#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, time
from pathlib import Path
from urllib import request

OR='https://openrouter.ai/api/v1/chat/completions'
KEY='https://openrouter.ai/api/v1/key'
SRC=Path('review-inputs/v159-zero-review/ZERO_BASE_SYNTHESIS_R2.txt')
OUT=Path('review-results/v159-zero-review/final-confirmation')
DAILY=10.0
PER=0.10
MODELS={
 'deepseek':'deepseek/deepseek-v4.1-flash',
 'glm':'z-ai/glm-5.3-flash',
 'xiaomi':'xiaomi/mimo-v2.5',
 'gemini':'google/gemini-3.8-flash',
}
def sha(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def budget(key):
 req=request.Request(KEY,headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
 with request.urlopen(req,timeout=30) as r:d=json.loads(r.read().decode('utf-8'))
 p=d.get('data') if isinstance(d,dict) and isinstance(d.get('data'),dict) else d
 u=float(p.get('usage_daily'))
 if not math.isfinite(u) or u<0: raise RuntimeError('usage_daily unverifiable')
 if u+PER>DAILY: raise RuntimeError('daily budget reservation exhausted')
 return {'usage_daily':u,'limit':p.get('limit'),'limit_remaining':p.get('limit_remaining')}
def call(model,prompt,key):
 max_tokens=12000 if model.startswith('z-ai/glm-') else 8000
 body={'model':model,'messages':[{'role':'user','content':prompt}],'temperature':0.0,'max_tokens':max_tokens,'stream':False,
       'provider':{'allow_fallbacks':True,'data_collection':'deny','sort':'price','ignore':['anthropic','mistral','nvidia'],'max_price':{'prompt':1.0,'completion':4.0}}}
 if model.startswith('deepseek/') or model.startswith('xiaomi/'): body['reasoning']={'effort':'none'}
 elif model.startswith('z-ai/glm-'): body['reasoning']={'effort':'low'}
 cmd=['curl','-sS','--connect-timeout','10','--max-time','360',OR,'-X','POST',
      '-H','Authorization: Bearer '+key,'-H','Content-Type: application/json',
      '-H','HTTP-Referer: https://github.com/ankitdcx/garden-swarm',
      '-H','X-Title: Garden v15.9 Zero-Base Final Confirmation',
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
 if not 200<=status<300:return status,data,f'HTTP_{status}: '+json.dumps(data,ensure_ascii=False)[:1000]
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
 cand=[s]
 if '{' in s and '}' in s:cand.append(s[s.find('{'):s.rfind('}')+1])
 for c in cand:
  try:
   o=json.loads(c)
   if isinstance(o,dict):return o,text
  except:pass
 return None,text
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--family',required=True,choices=MODELS);args=ap.parse_args()
 key=os.environ.get('OPENROUTER_API_KEY')
 if not key: raise SystemExit('OPENROUTER_API_KEY missing')
 model=MODELS[args.family];receipt=budget(key);src=SRC.read_text()
 prompt=f'''FINAL CONFIRMATION — GARDEN v15.9 ZERO-BASE R2.
Reviewer family: {args.family}
Candidate SHA-256: {sha(src)}

You are reviewing only this current-v15.9-derived synthesis. Do not use prior Garden history.
This is the single bounded confirmation round after final-challenge patches. Verify the R2 patches close the material findings, then try to falsify the exact R2 synthesis. Focus on material contradictions, weakened safety/rights/privacy/authority,
duplicate ontology, precedence ambiguity, unjustified release claims, or missing hard tests.
If no material issue remains, verdict ACCEPT.
Return one JSON object only:
{{
 "verdict":"ACCEPT|ACCEPT_WITH_PATCH|BLOCK",
 "material_findings":[{{"id":"C1","severity":"CRITICAL|HIGH|MEDIUM|LOW","candidate_refs":["ZR-001"],"claim":"...","minimal_patch":"...","test":"..."}}],
 "must_retain":[],
 "must_remove_or_defer":[],
 "uncertainty":"..."
}}
At most 4 findings. Do not invent stylistic defects. If no material issue remains, verdict ACCEPT.

--- BEGIN R1 ---
{src}
--- END R1 ---
'''
 start=time.time();status,data,err=call(model,prompt,key);structured,raw=parse(data)
 usage=(data or {}).get('usage') if isinstance(data,dict) else None
 cost=(usage or {}).get('cost') if isinstance(usage,dict) else None
 usable=isinstance(structured,dict) and structured.get('verdict') in {'ACCEPT','ACCEPT_WITH_PATCH','BLOCK'}
 if isinstance(cost,(int,float)) and float(cost)>PER: usable=False;err='MODEL_COST_CEILING_EXCEEDED'
 res={'schema':'GardenV159ZeroBaseFinalConfirmation/v1','family':args.family,'model':model,'candidate_sha256':sha(src),
      'http_status':status,'error':err,'usable':usable,'review':structured,'raw_review':None if structured is not None else raw,
      'actual_model':(data or {}).get('model') if isinstance(data,dict) else None,'provider':(data or {}).get('provider') if isinstance(data,dict) else None,
      'usage':usage,'budget_receipt':receipt,'elapsed_seconds':round(time.time()-start,2),
      'canonical_effect':False,'semantic_delta_admitted':False}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/f'{args.family}.json').write_text(json.dumps(res,indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'family':args.family,'usable':usable,'error':err,'cost':cost}))
 if not usable: raise SystemExit(2)
if __name__=='__main__':main()
