#!/usr/bin/env node
/** Fixed model-as-data runner. No model-generated JS, plugins, tools or URLs.
 * ONNX tensor execution uses WASM only. Host JS/runtime are part of the TCB.
 * Node permissions supplement this boundary; they do not contain malicious JS.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { performance } from 'node:perf_hooks';
import { parseCalculatorIntent } from './calculator_intent.mjs';

const deps = process.env.GARDEN_WASM_DEPENDENCIES;
const modelDir = process.env.GARDEN_WASM_MODEL_DIR;
if (!deps || !modelDir || !path.isAbsolute(deps) || !path.isAbsolute(modelDir)) throw Error('operator must configure absolute dependency/model paths');
if (!process.permission || process.permission.has('fs.read') || process.permission.has('fs.write') || process.permission.has('child') || process.permission.has('addon') || process.permission.has('wasi') || process.permission.has('worker')) throw Error('required restricted Node launch missing');

// No online model loading, remote URL, arbitrary code or tool dispatch exists.
globalThis.fetch = () => { throw Error('network acquisition disabled in inference worker'); };
const { Tokenizer } = await import(pathToFileURL(path.join(deps, '@huggingface/tokenizers/dist/tokenizers.mjs')).href);
const ort = await import(pathToFileURL(path.join(deps, 'onnxruntime-web/dist/ort.node.min.mjs')).href);

const smolHashes = {
  'config.json': '8eb740e8bbe4cff95ea7b4588d17a2432deb16e8075bc5828ff7ba9be94d982a',
  'model_quantized.onnx': 'ecc1a19eece6494e2963cf74f78ace35916e8d0b803168ddd41db00979f18e39',
  'tokenizer.json': '9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c',
  'tokenizer_config.json': '4ec77d44f62efeb38d7e044a1db318f6a939438425312dfa333b8382dbad98df',
};
const qwenHashes = {
  'config.json': '8a04114ba59cc42b47d804d35d1d5c61d746ae4634f41f796768c6e302d39b9e',
  'model_quantized.onnx': 'ccf8734e59fdf7475b2dc0c117005e267a3a08342c1d951e0a79f0bce57bf62a',
  'tokenizer.json': 'e7a95fce95bf5b0946d0ddb3f9d7caa030b7e850bbe92b0edb26bcf563e9f3d5',
  'tokenizer_config.json': 'b0a8115cf05a7002cbe2575058c0139c1dee3f06f221c05717c3444947d78b9f',
};
const configDigest=crypto.createHash('sha256').update(fs.readFileSync(path.join(modelDir,'config.json'))).digest('hex');
const isQwen=configDigest===qwenHashes['config.json'];
const hashes=isQwen?qwenHashes:smolHashes;
const modelId=isQwen?'Qwen/Qwen3-0.6B':'HuggingFaceTB/SmolLM2-135M-Instruct';
const family=isQwen?'Qwen3':'SmolLM2';
function readPinned(filename) {
  const bytes = fs.readFileSync(path.join(modelDir, filename));
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== hashes[filename]) throw Error('pinned model asset mismatch');
  return bytes;
}
const config = JSON.parse(readPinned('config.json'));
const tokenizer = new Tokenizer(JSON.parse(readPinned('tokenizer.json')), JSON.parse(readPinned('tokenizer_config.json')));
const modelBytes = readPinned('model_quantized.onnx');
const dist = path.join(deps, 'onnxruntime-web/dist');
ort.env.wasm.numThreads = 1;
ort.env.wasm.proxy = false;
ort.env.wasm.wasmPaths = dist + '/';
ort.env.wasm.wasmBinary = new Uint8Array(fs.readFileSync(path.join(dist, 'ort-wasm-simd-threaded.wasm')));

let input = '';
for await (const chunk of process.stdin) {
  input += chunk;
  if (Buffer.byteLength(input) > 32768) throw Error('input budget exceeded');
}
const request = JSON.parse(input);
const planCalculator=process.argv.slice(2).includes('--plan-calculator');
if(process.argv.slice(2).some(x=>x!=='--plan-calculator'))throw Error('unknown operator mode');
const allowedFields = new Set(['task', 'tool', 'args', 'actor_id', 'delegation_id', 'policy_version']);
const schemas = {calculator:['op','a','b'],sandbox_read:['path'],sandbox_write:['path','content'],mock_email:['to','subject','body'],mock_ledger:['from','to','amount_cents']};
if(planCalculator) {
  if(request.tool!==undefined||request.args!==undefined)throw Error('model planning mode accepts task and registered identity only');
  request.tool='calculator';request.args={op:'add',a:0,b:0};
}
if (!request || typeof request !== 'object' || Array.isArray(request) || Object.keys(request).some(x=>!allowedFields.has(x)) || typeof request.task !== 'string' || !request.task.trim() || Buffer.byteLength(request.task)>8192 || !schemas[request.tool] || !request.args || typeof request.args !== 'object' || Array.isArray(request.args) || Object.keys(request.args).sort().join(',') !== schemas[request.tool].sort().join(',')) throw Error('invalid proposal-only request');
if (request.tool==='calculator' && (!['add','subtract','multiply','divide'].includes(request.args.op) || !Number.isFinite(request.args.a) || !Number.isFinite(request.args.b))) throw Error('invalid calculator arguments');
for(const field of ['actor_id','delegation_id','policy_version']) if(request[field] !== undefined && (typeof request[field] !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(request[field]))) throw Error('invalid registered identity');
let context = JSON.stringify({task:request.task,tool:request.tool,args:request.args});
let contextHash = crypto.createHash('sha256').update(context).digest('hex');
const session = await ort.InferenceSession.create(new Uint8Array(modelBytes), {executionProviders:['wasm'],graphOptimizationLevel:'all'});
const deadline = performance.now()+40000;

async function generate(question, maxNewTokens=isQwen?32:48) {
  const prompt='<|im_start|>system\nYou are a helpful assistant. Answer concisely.<|im_end|>\n<|im_start|>user\n'+question+'<|im_end|>\n<|im_start|>assistant\n'+(isQwen?'<think>\n\n</think>\n\n':'');
  const encoded=tokenizer.encode(prompt);
  if(encoded.ids.length>512)throw Error('tokenized input budget exceeded');
  let all=[...encoded.ids], ids=all, past={}, generated=[];
  for(let step=0;step<maxNewTokens;step++) {
    if(performance.now()>deadline)throw Error('inference deadline exceeded');
    const feed={input_ids:new ort.Tensor('int64',BigInt64Array.from(ids,BigInt),[1,ids.length]),attention_mask:new ort.Tensor('int64',BigInt64Array.from(all,()=>1n),[1,all.length]),position_ids:new ort.Tensor('int64',BigInt64Array.from(ids,(_,j)=>BigInt(all.length-ids.length+j)),[1,ids.length])};
    for(let layer=0;layer<config.num_hidden_layers;layer++)for(const kind of ['key','value']) feed[`past_key_values.${layer}.${kind}`]=past[`present.${layer}.${kind}`]||new ort.Tensor('float32',new Float32Array(0),[1,config.num_key_value_heads,0,config.head_dim||config.hidden_size/config.num_attention_heads]);
    const result=await session.run(feed), logits=result.logits;
    let offset=(ids.length-1)*config.vocab_size, largest=-Infinity, next=0;
    for(let token=0;token<config.vocab_size;token++)if(logits.data[offset+token]>largest){largest=logits.data[offset+token];next=token;}
    if(next===config.eos_token_id)break;
    generated.push(next);all.push(next);ids=[next];past=result;
  }
  return {text:tokenizer.decode(generated),prompt_sha256:crypto.createHash('sha256').update(prompt).digest('hex'),generated_tokens:generated.length};
}

const roleQuestions = [
  ['planner','Summarize the requested bounded tool action in one sentence. Request: '],
  ['qse_explorer','Name one question that should be checked before this action. Request: '],
  ['representation_escape','Name one alternative to doing this action immediately. Request: '],
  ['verifier','Check this task for a possible arithmetic or input mistake. Request: '],
];
let plannedOutput=null,planElapsed=0;
if(planCalculator) {
  const started=performance.now();
  plannedOutput=await generate('Convert the arithmetic request to a JSON object only, with exactly keys op,a,b. op must be add,subtract,multiply,divide. a and b must be numbers. Example request: Add 2 and 3. JSON: {"op":"add","a":2,"b":3}.\nRequest: '+request.task+'\nJSON:',64);
  planElapsed=(performance.now()-started)/1000;
  try {
    request.args=parseCalculatorIntent(plannedOutput.text);
  } catch(error) {
    console.log(JSON.stringify({schema:'garden.model_plan_failure.v1',status:'UNKNOWN',cognition:'OPEN_WEIGHT_LLM',cognition_status:'EXPERIMENTAL',model:modelId,family,model_execution_provider:'wasm',proposal:null,execution_authority:false,model_generated_proposal:false,model_plan_attempt:plannedOutput,reason:error.message}));
    await session.release();
    process.exit(2);
  }
  context=JSON.stringify({task:request.task,tool:request.tool,args:request.args});
  contextHash=crypto.createHash('sha256').update(context).digest('hex');
}
const reports=[];
const deterministicCritics={
  qse_explorer:'Check missing inputs, no-action, read-only preview, policy/delegation expiry, omitted effects, failure recovery and representation overlap. These findings are advisory; verification remains UNKNOWN.',
  representation_escape:'Consider no action or a read-only preview. Represent the task as a scoped capability request; the external gate decides exact authority.',
  verifier:'The model is not its sole authoritative verifier. The external deterministic calculator/gate checks the exact bounded input contract; consequential effects require independent registered assessments.',
};
for(const [role,question] of roleQuestions) {
  const started=performance.now(), ruleBased=isQwen&&role!=='planner';
  // The larger CPU model uses one planner within budget; critics degrade honestly.
  const output=(role==='planner'&&plannedOutput)?plannedOutput:ruleBased?{text:deterministicCritics[role],prompt_sha256:crypto.createHash('sha256').update('RULE_BASED:'+question+context).digest('hex'),generated_tokens:0}:await generate(question+context);
  reports.push({role,actor_id:role+'-advisory',cognition:ruleBased?'RULE_BASED':'OPEN_WEIGHT_LLM',cognition_status:ruleBased?'IMPLEMENTATION':'EXPERIMENTAL',model:ruleBased?'garden-advisory-rules-v1':modelId,family:ruleBased?'deterministic-rules':family,lineage:ruleBased?'garden-advisory-rules-v1':'onnx-sha256:'+hashes['model_quantized.onnx'],controller:'garden-wasm-worker',prompt_sha256:output.prompt_sha256,evidence_sha256:contextHash,tool_overlap:[request.tool],analysis:output.text,status:'UNKNOWN',authoritative:false,generated_tokens:output.generated_tokens,elapsed_seconds:(role==='planner'&&plannedOutput)?Math.round(planElapsed*100)/100:Math.round((performance.now()-started)/10)/100});
}
await session.release();
const job=crypto.randomUUID().replaceAll('-','');
const proposal={id:'job-'+job,nonce:'nonce-'+job,actor_id:request.actor_id||'planner-demo',delegation_id:request.delegation_id||'demo-delegation',policy_version:request.policy_version||'garden-implementation-0.1',tool:request.tool,args:request.args,claims:[],unknowns:[],human_effect:!['calculator','sandbox_read'].includes(request.tool),assessment_ids:{verification:null,qse:null,truthfulness:null,human_effect:null},successor_of:null};
const overlaps=[];
for(let i=0;i<reports.length;i++)for(let j=i+1;j<reports.length;j++)overlaps.push({roles:[reports[i].role,reports[j].role],same_family:reports[i].family===reports[j].family,same_lineage:reports[i].lineage===reports[j].lineage,same_controller:true,same_evidence:true,tool_overlap:[request.tool],independent:false});
console.log(JSON.stringify({schema:'garden.agent_bundle.v1',status:'IMPLEMENTATION',cognition:'OPEN_WEIGHT_LLM',cognition_status:'EXPERIMENTAL',model_execution_provider:'wasm',model_execution_boundary:'Fixed ONNX model-as-data tensor runner; no generated JS/plugins/tools; trusted host JS/runtime remain TCB.',model_generated_proposal:planCalculator,execution_authority:false,proposal,advisory_reports:reports,lineage_overlap:overlaps,roles:reports.map(r=>({role:r.role.replaceAll('_',' '),summary:r.analysis,cognition:r.cognition})),limitations:['Experimental tiny model; weak reasoning and incomplete/repetitive output possible.','Shared model/controller roles are not independent verifiers.','Node permissions are not malicious-host-code containment. Host/runtime compromise and VM-engine flaws remain residual risks.','No model-generated code, remote assets, tool dispatch, trusted assessment registration or authority updates are supported.']}));
