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

const deps = process.env.GARDEN_WASM_DEPENDENCIES;
const modelDir = process.env.GARDEN_WASM_MODEL_DIR;
if (!deps || !modelDir || !path.isAbsolute(deps) || !path.isAbsolute(modelDir)) throw Error('operator must configure absolute dependency/model paths');
if (!process.permission || process.permission.has('fs.read') || process.permission.has('fs.write') || process.permission.has('child') || process.permission.has('addon') || process.permission.has('wasi') || process.permission.has('worker')) throw Error('required restricted Node launch missing');

// No online model loading, remote URL, arbitrary code or tool dispatch exists.
globalThis.fetch = () => { throw Error('network acquisition disabled in inference worker'); };
const { Tokenizer } = await import(pathToFileURL(path.join(deps, '@huggingface/tokenizers/dist/tokenizers.mjs')).href);
const ort = await import(pathToFileURL(path.join(deps, 'onnxruntime-web/dist/ort.node.min.mjs')).href);

const hashes = {
  'config.json': '8eb740e8bbe4cff95ea7b4588d17a2432deb16e8075bc5828ff7ba9be94d982a',
  'model_quantized.onnx': 'ecc1a19eece6494e2963cf74f78ace35916e8d0b803168ddd41db00979f18e39',
  'tokenizer.json': '9ca9acddb6525a194ec8ac7a87f24fbba7232a9a15ffa1af0c1224fcd888e47c',
  'tokenizer_config.json': '4ec77d44f62efeb38d7e044a1db318f6a939438425312dfa333b8382dbad98df',
};
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
const allowedFields = new Set(['task', 'tool', 'args', 'actor_id', 'delegation_id', 'policy_version']);
const schemas = {calculator:['op','a','b'],sandbox_read:['path'],sandbox_write:['path','content'],mock_email:['to','subject','body'],mock_ledger:['from','to','amount_cents']};
if (!request || typeof request !== 'object' || Array.isArray(request) || Object.keys(request).some(x=>!allowedFields.has(x)) || typeof request.task !== 'string' || !request.task.trim() || Buffer.byteLength(request.task)>8192 || !schemas[request.tool] || !request.args || typeof request.args !== 'object' || Array.isArray(request.args) || Object.keys(request.args).sort().join(',') !== schemas[request.tool].sort().join(',')) throw Error('invalid proposal-only request');
if (request.tool==='calculator' && (!['add','subtract','multiply','divide'].includes(request.args.op) || !Number.isFinite(request.args.a) || !Number.isFinite(request.args.b))) throw Error('invalid calculator arguments');
for(const field of ['actor_id','delegation_id','policy_version']) if(request[field] !== undefined && (typeof request[field] !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/.test(request[field]))) throw Error('invalid registered identity');
const context = JSON.stringify({task:request.task,tool:request.tool,args:request.args});
const contextHash = crypto.createHash('sha256').update(context).digest('hex');
const session = await ort.InferenceSession.create(new Uint8Array(modelBytes), {executionProviders:['wasm'],graphOptimizationLevel:'all'});
const deadline = performance.now()+40000;

async function generate(question, maxNewTokens=48) {
  const prompt='<|im_start|>system\nYou are a helpful assistant. Answer concisely.<|im_end|>\n<|im_start|>user\n'+question+'<|im_end|>\n<|im_start|>assistant\n';
  const encoded=tokenizer.encode(prompt);
  if(encoded.ids.length>512)throw Error('tokenized input budget exceeded');
  let all=[...encoded.ids], ids=all, past={}, generated=[];
  for(let step=0;step<maxNewTokens;step++) {
    if(performance.now()>deadline)throw Error('inference deadline exceeded');
    const feed={input_ids:new ort.Tensor('int64',BigInt64Array.from(ids,BigInt),[1,ids.length]),attention_mask:new ort.Tensor('int64',BigInt64Array.from(all,()=>1n),[1,all.length]),position_ids:new ort.Tensor('int64',BigInt64Array.from(ids,(_,j)=>BigInt(all.length-ids.length+j)),[1,ids.length])};
    for(let layer=0;layer<config.num_hidden_layers;layer++)for(const kind of ['key','value']) feed[`past_key_values.${layer}.${kind}`]=past[`present.${layer}.${kind}`]||new ort.Tensor('float32',new Float32Array(0),[1,config.num_key_value_heads,0,config.hidden_size/config.num_attention_heads]);
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
const reports=[];
for(const [role,question] of roleQuestions) {
  const started=performance.now(), output=await generate(question+context);
  reports.push({role,actor_id:role+'-advisory',cognition:'OPEN_WEIGHT_LLM',cognition_status:'EXPERIMENTAL',model:'HuggingFaceTB/SmolLM2-135M-Instruct',family:'SmolLM2',lineage:'onnx-sha256:'+hashes['model_quantized.onnx'],controller:'garden-wasm-worker',prompt_sha256:output.prompt_sha256,evidence_sha256:contextHash,tool_overlap:[request.tool],analysis:output.text,status:'UNKNOWN',authoritative:false,generated_tokens:output.generated_tokens,elapsed_seconds:Math.round((performance.now()-started)/10)/100});
}
await session.release();
const job=crypto.randomUUID().replaceAll('-','');
const proposal={id:'job-'+job,nonce:'nonce-'+job,actor_id:request.actor_id||'planner-demo',delegation_id:request.delegation_id||'demo-delegation',policy_version:request.policy_version||'garden-implementation-0.1',tool:request.tool,args:request.args,claims:[],unknowns:[],human_effect:!['calculator','sandbox_read'].includes(request.tool),assessment_ids:{verification:null,qse:null,truthfulness:null,human_effect:null},successor_of:null};
const overlaps=[];
for(let i=0;i<reports.length;i++)for(let j=i+1;j<reports.length;j++)overlaps.push({roles:[reports[i].role,reports[j].role],same_family:true,same_lineage:true,same_controller:true,same_evidence:true,tool_overlap:[request.tool],independent:false});
console.log(JSON.stringify({schema:'garden.agent_bundle.v1',status:'IMPLEMENTATION',cognition:'OPEN_WEIGHT_LLM',cognition_status:'EXPERIMENTAL',model_execution_provider:'wasm',model_execution_boundary:'Fixed ONNX model-as-data tensor runner; no generated JS/plugins/tools; trusted host JS/runtime remain TCB.',execution_authority:false,proposal,advisory_reports:reports,lineage_overlap:overlaps,roles:reports.map(r=>({role:r.role.replaceAll('_',' '),summary:r.analysis,cognition:r.cognition})),limitations:['Experimental tiny model; weak reasoning and incomplete/repetitive output possible.','Shared model/controller roles are not independent verifiers.','Node permissions are not malicious-host-code containment. Host/runtime compromise and VM-engine flaws remain residual risks.','No model-generated code, remote assets, tool dispatch, trusted assessment registration or authority updates are supported.']}));
