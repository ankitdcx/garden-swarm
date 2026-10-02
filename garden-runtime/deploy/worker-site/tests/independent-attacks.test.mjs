// Independent attack fixtures. Stored data is deliberately corrupted only in
// the explicit hostile-storage case; this is not an ordinary model API ability.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import worker, {decide, strictJSON} from '../worker/index.js';

function database(){
  const sqlite=new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../drizzle/0000_thankful_human_cannonball.sql',import.meta.url),'utf8'));
  return {sqlite,prepare(sql){return {values:[],bind(...v){this.values=v;return this},async first(){return sqlite.prepare(sql).get(...this.values)||null},async all(){return {results:sqlite.prepare(sql).all(...this.values)}},async run(){return {meta:{changes:sqlite.prepare(sql).run(...this.values).changes}}}}}};
}
function request(path,value,token){return new Request('https://demo.test'+path,{method:value===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:value===undefined?undefined:JSON.stringify(value)});}
async function setup(){
  const DB=database(),env={DB,GARDEN_RECEIPT_KEY:'independent-test-only-receipt-key-not-production'};
  const session=await (await worker.fetch(request('/api/session',{}),env)).json();
  const s=await DB.prepare('SELECT * FROM sessions WHERE id=?').bind(session.id).first();
  return {DB,env,session,s,proposal(changes={}){return {id:crypto.randomUUID(),nonce:crypto.randomUUID(),actor_id:'demo-planner',delegation_id:s.id,policy_version:'garden-worker-experimental-0.1',tool:'calculator',args:{expression:'9 * 9'},claims:[],unknowns:[],...changes}}};
}

test('independent: human credential is not accepted as raw agent authority',async()=>{
  const f=await setup();
  assert.equal((await worker.fetch(request('/api/proposal',f.proposal(),f.session.token),f.env)).status,401);
});
test('independent: agent cannot forge human flag or consent at raw boundary',async()=>{
  const f=await setup();
  const p=f.proposal({tool:'fs_write',args:{path:'notes/attack.txt',content:'attack'},human_effect:true});
  let r=await worker.fetch(request('/api/proposal',{...p,human:true},f.session.agent_token),f.env);
  assert.equal(r.status,400);
  r=await worker.fetch(request('/api/proposal',p,f.session.agent_token),f.env);
  assert.equal((await r.json()).decision,'DENY');
});
test('independent: agent cannot revoke session or access human receipts',async()=>{
  const f=await setup();
  for(const [path,value]of [['/api/revoke',{}],['/api/receipts',undefined],['/api/status',undefined]]){
    assert.equal((await worker.fetch(request(path,value,f.session.agent_token),f.env)).status,401);
  }
});
test('independent: another session cannot consume victim delegation',async()=>{
  const f=await setup();
  const other=await (await worker.fetch(request('/api/session',{}),f.env)).json();
  const r=await worker.fetch(request('/api/proposal',f.proposal(),other.agent_token),f.env);
  const out=await r.json();
  assert.equal(out.decision,'DENY');
  assert.equal(out.receipt.session_id,other.id);
});
test('independent: concurrent proposals cannot fork authoritative receipt sequence',async()=>{
  const f=await setup();
  const outcomes=await Promise.allSettled([decide(f.env,f.s,f.proposal()),decide(f.env,f.s,f.proposal())]);
  assert.equal(outcomes.filter(r=>r.status==='fulfilled').length,1);
  assert.equal(outcomes.filter(r=>r.status==='rejected').length,1);
  assert.equal((await f.DB.prepare('SELECT COUNT(*) AS n FROM decisions').first()).n,1);
});
test('independent: altered log cannot be laundered into freshly signed read effect',async()=>{
  const f=await setup();
  const p=f.proposal({tool:'fs_write',args:{path:'notes/victim.txt',content:'genuine'},human_effect:true});
  const r=await decide(f.env,f.s,p,{human:true});
  const corrupted=structuredClone(r.receipt);
  corrupted.execution_result.stored_note.content='attacker-forged-content';
  f.DB.sqlite.prepare('UPDATE decisions SET receipt=? WHERE id=?').run(JSON.stringify(corrupted),r.receipt.receipt_id);
  const q=f.proposal({tool:'fs_read',args:{path:'notes/victim.txt'}});
  await assert.rejects(()=>decide(f.env,f.s,q),/integrity|signature|authenticate|corrupt/i);
});
test('independent: strict JSON rejects non-JSON Unicode whitespace',()=>{
  for(const text of ['\u00a0{"tool":"calculator"}','{"tool":"calculator"}\ufeff'])assert.throws(()=>strictJSON(text));
});
