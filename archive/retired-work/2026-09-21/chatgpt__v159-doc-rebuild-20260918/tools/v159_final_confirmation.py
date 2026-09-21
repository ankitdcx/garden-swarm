#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, time
from pathlib import Path
from urllib import request

OPENROUTER='https://openrouter.ai/api/v1/chat/completions'
KEY_INFO='https://openrouter.ai/api/v1/key'
CANDIDATE=Path('review-inputs/v159-postfreeze/SYNTHESIZED_POSTFREEZE_CANDIDATE_R3.txt')
EVIDENCE=Path('review-inputs/v159-postfreeze/FINAL_BOARD_EVIDENCE_INDEX.json')
OUT=Path('review-results/v159-postfreeze-final-confirmation')
DAILY_CEILING=10.0
PER_CALL_CEILING=0.10
MODELS={
 'deepseek':'deepseek/deepseek-v4.1-flash',
 'glm':'z-ai/glm-5.3-flash',
 'gemini':'google/gemini-3.8-flash',
}

def sha(s): return hashlib.sha256(s.encode()).hexdigest()

def budget(key):
 req=request.Request(KEY_INFO,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
 with request.urlopen(req,timeout=30) as r:data=json.loads(r.read().decode())
 p=data.get('data') if isinstance(data,dict) and isinstance(data.get('data'),dict) else data
 u=float(p.get('usage_daily'))
 if not math.isfinite(u) or u<0:raise RuntimeError('daily usage unverifiable')
 if u+PER_CALL_CEILING>DAILY_CEILING:raise RuntimeError('daily budget reservation exhausted')
 return {'usage_daily':u,'limit':p.get('limit'),'limit_remaining':p.get('limit_remaining')}

def call(model,prompt,key):
 max_tokens=9000 if model.startswith('z-ai/glm-') else 4500
 body={'model':model,'messages':[{'role':'user','content':prompt}],'temperature':0.0,'max_tokens':max_tokens,'stream':False,
       'provider':{'allow_fallbacks':True,'data_collection':'deny','sort':'price','ignore':['anthropic','mistral','nvidia'],'max_price':{'prompt':1.0,'completion':4.0}}}
 if model.startswith('deepseek/'): body['reasoning']={'effort':'none'}
 elif model.startswith('z-ai/glm-'): body['reasoning']={'effort':'low'}
 cmd=['curl','-sS','--connect-timeout','10','--max-time','360',OPENROUTER,'-X','POST',
      '-H','Authorization: Bearer '+key,'-H','Content-Type: application/json',
      '-H','HTTP-Referer: https://github.com/ankitdcx/garden-swarm',
      '-H','X-Title: Garden v15.9 Final Confirmation',
      '--data-binary','@-','-w','\\n%{http_code}']
 p=subprocess.run(cmd,input=json.dumps(body,separators=(',',':')),text=True,capture_output=True,timeout=375)
 raw=p.stdout
 if '\n' not in raw:return 0,{},f'NO_STATUS rc={p.returncode} {p.stderr[-500:]}'
 payload,status=raw.rsplit('\n',1)
 try:status=int(status.strip())
 except:status=0
 try:data=json.loads(payload)
 except:data={'raw_payload':payload}
 if p.returncode!=0:return status,data,f'CURL_{p.returncode}'
 if not 200<=status<300:return status,data,f'HTTP_{status}: '+json.dumps(data,ensure_ascii=False)[:1200]
 return status,data,None

def parse(data):
 choices=(data or {}).get('choices') or []
 if not choices:return None,''
 text=((choices[0].get('message') or {}).get('content') or '').strip()
 s=text
 if s.startswith('```'):
  s=s.split('\n',1)[1] if '\n' in s else s
  if s.endswith('```'):s=s[:-3]
  s=s.strip()
  if s.lower().startswith('json\n'):s=s[5:]
 for c in [s, s[s.find('{'):s.rfind('}')+1] if '{' in s and '}' in s else '']:
  if not c:continue
  try:
   o=json.loads(c)
   if isinstance(o,dict):return o,text
  except:pass
 return None,text

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--family',required=True,choices=MODELS);args=ap.parse_args()
 key=os.environ.get('OPENROUTER_API_KEY')
 if not key:raise SystemExit('OPENROUTER_API_KEY missing')
 model=MODELS[args.family];receipt=budget(key);cand=CANDIDATE.read_text();evidence=EVIDENCE.read_text()
 prompt=f'''FINAL CONFIRMATION — GARDEN v15.9 R3.
Reviewer family: {args.family}
Candidate SHA-256: {sha(cand)}

This is the single allowed confirmation round after one challenge correction. You have not seen other confirmation answers.
Review evidence index is metadata only; do not vote by majority.

Task:
- Verify the R3 UCAS lineage/profile clarification closes the challenge ambiguity, then try to falsify the exact R3 candidate.
- Focus only on material contradictions, duplicate owners, authority escalation, rights/privacy/child-safety/legal/federation regressions, unjustified admission, or missing hard tests.
- Existing owner beats duplicate subsystem.
- No model/review consensus creates truth, canon, authority, execution permission, or certification.
- Universal surveillance remains rejected.
- Declared-scope coverage is not omniscience.
- If no material issue remains, verdict ACCEPT.
- At most 4 material findings. Do not invent minor stylistic defects. If the correction closes the issue and no new material issue exists, verdict ACCEPT.

Return JSON only:
{{"verdict":"ACCEPT|ACCEPT_WITH_PATCH|BLOCK","summary":"...","material_findings":[{{"id":"C1","severity":"CRITICAL|HIGH|MEDIUM|LOW","item_refs":["E1"],"claim":"...","minimal_patch":"...","test":"..."}}],"must_retain":[],"must_remove_or_defer":[],"uncertainty":"..."}}

--- EVIDENCE INDEX ---
{evidence}
--- BEGIN R2 ---
{cand}
--- END R2 ---
'''
 start=time.time();status,data,err=call(model,prompt,key);structured,raw=parse(data)
 usage=(data or {}).get('usage') if isinstance(data,dict) else None
 cost=(usage or {}).get('cost') if isinstance(usage,dict) else None
 usable=structured is not None
 if isinstance(cost,(int,float)) and float(cost)>PER_CALL_CEILING:usable=False;err='MODEL_COST_CEILING_EXCEEDED'
 result={'schema':'GardenV159FinalConfirmationReview/v1','family':args.family,'model':model,'candidate_sha256':sha(cand),'prompt_sha256':sha(prompt),
         'http_status':status,'error':err,'elapsed_seconds':round(time.time()-start,2),'usable':usable,'review':structured,
         'raw_review':None if structured is not None else raw,'actual_model':(data or {}).get('model') if isinstance(data,dict) else None,
         'provider':(data or {}).get('provider') if isinstance(data,dict) else None,'usage':usage,'budget_receipt':receipt,
         'canonical_effect':False,'semantic_delta_admitted':False}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/f'{args.family}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'family':args.family,'usable':usable,'error':err,'cost':cost}))
 if not usable:raise SystemExit(2)
if __name__=='__main__':main()
