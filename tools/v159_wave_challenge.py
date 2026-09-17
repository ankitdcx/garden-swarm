#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf, hashlib, json, os, subprocess, sys, time
from pathlib import Path

OR='https://openrouter.ai/api/v1'
OUT=Path('review-results/v159-wave1-challenge')
MODELS={
 'deepseek':['deepseek/deepseek-v4-flash-0731','deepseek/deepseek-v4.1-flash'],
 'glm':['z-ai/glm-5.3-flash','z-ai/glm-5.3'],
 'xiaomi':['xiaomi/mimo-v2.5','xiaomi/mimo-v2.5-pro'],
 'gemini':['google/gemini-3.8-flash'],
}
TIMEOUT=220

def canon(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def sha(t): return hashlib.sha256(t.encode()).hexdigest()
def post(body,key):
    cmd=['curl','-sS','--connect-timeout','10','--max-time',str(TIMEOUT),OR+'/chat/completions','-X','POST','-H','Authorization: Bearer '+key,'-H','Content-Type: application/json','--data-binary','@-','-w','\n%{http_code}']
    p=subprocess.run(cmd,input=canon(body),text=True,capture_output=True,timeout=TIMEOUT+10); raw=p.stdout
    if '\n' not in raw: return 0,None,'NO_STATUS'
    payload,st=raw.rsplit('\n',1)
    try: status=int(st.strip())
    except: status=0
    if p.returncode!=0: return status,None,'CURL_'+str(p.returncode)
    if not 200<=status<300: return status,None,'HTTP_'+str(status)
    try: return status,json.loads(payload),None
    except: return status,None,'JSON_DECODE'

def parse(text):
    s=(text or '').strip()
    if s.startswith('```'):
        s=s.split('\n',1)[1] if '\n' in s else s
        if s.endswith('```'): s=s[:-3]
        s=s.strip()
        if s.lower().startswith('json\n'): s=s[5:]
    for c in (s, s[s.find('{'):s.rfind('}')+1] if '{' in s and '}' in s else ''):
        if not c: continue
        try:
            o=json.loads(c)
            if isinstance(o,dict): return o
        except: pass
    return None

def prompt(source,candidate,family,ph):
    return f'''SECOND-PASS ADVERSARIAL GARDEN v15.9 REVIEW.
You are {family}. You now see the original bounded source packet AND ChatGPT's synthesized candidate after independent reviewers were considered. Do not vote by popularity. Attack the candidate.
Preserve: authority/evidence/capability do not manufacture authority; UNKNOWN != PASS; specification != proof != implementation != certification; rights/privacy/safety/law remain hard constraints; prefer existing owners/minimal repair.
Candidate SHA256: {ph}

TASK
1. Identify only material blockers, regressions, semantic contradictions, missing cases, or over-engineering introduced/remained in the candidate.
2. Compare candidate against original source and DO_NOTHING.
3. Distinguish BLOCKER/HIGH issues from optional refinements.
4. If candidate is sound enough at design level, say ACCEPT and do not invent problems.
5. Give at most 5 findings with minimal repair and falsifiable test. Do not claim tests/searches ran.

Return concise JSON if possible:
{{"verdict":"ACCEPT|CHANGE|BLOCK|EXPAND_REQUIRED","summary":"...","findings":[{{"id":"C1","severity":"CRITICAL|HIGH|MEDIUM|LOW","claim":"...","minimal_repair":"...","test":"...","confidence":"HIGH|MEDIUM|LOW","needs_more_context":false}}],"retain":[],"context_requests":[]}}

--- ORIGINAL SOURCE PACKET ---
{source}
--- SYNTHESIZED CANDIDATE ---
{candidate}
--- END ---'''

def call(family,candidates,source,candidate,key):
    p=prompt(source,candidate,family,sha(candidate)); out={'family':family,'prompt_sha256':sha(p),'attempts':[]}; start=time.time()
    for mid in candidates:
        body={'model':mid,'messages':[{'role':'user','content':p}],'temperature':0.05,'max_tokens':2600,'stream':False,'provider':{'allow_fallbacks':True,'sort':'throughput','data_collection':'deny','zdr':True}}
        if family=='glm': body['reasoning']={'effort':'low','exclude':True}
        a=time.time(); status,data,err=post(body,key); out['attempts'].append({'model':mid,'http_status':status,'transport':err,'elapsed_seconds':round(time.time()-a,2)})
        if err:
            if err.startswith('CURL_'): break
            continue
        choices=(data or {}).get('choices') or []; text=((choices[0].get('message') or {}).get('content') or '').strip() if choices else ''; o=parse(text)
        if o is not None: out.update(status='COMPLETE_STRUCTURED',review=o)
        elif len(text)>=150: out.update(status='COMPLETE_RAW',raw_review=text)
        else: continue
        out.update(selected_model=mid,actual_model=(data or {}).get('model'),provider=(data or {}).get('provider'),usage=(data or {}).get('usage')); break
    if 'status' not in out: out['status']='FAILED'
    out['elapsed_seconds']=round(time.time()-start,2); return out

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: v159_wave_challenge.py SOURCE CANDIDATE')
    key=os.environ.get('OPENROUTER_API_KEY');
    if not key: raise SystemExit('OPENROUTER_API_KEY missing')
    sp,cp=Path(sys.argv[1]),Path(sys.argv[2]); source=sp.read_text(); candidate=cp.read_text(); pid=sp.stem
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        reviews=[f.result() for f in [pool.submit(call,f,c,source,candidate,key) for f,c in MODELS.items()]]
    completed=sum(r.get('status','').startswith('COMPLETE') for r in reviews)
    result={'schema':'GardenWaveChallenge/v1','packet_id':pid,'source_sha256':sha(source),'candidate_sha256':sha(candidate),'completed':completed,'quorum':completed>=3,'reviews':reviews,'canonical_effect':False}
    out=OUT/pid; out.mkdir(parents=True,exist_ok=True); (out/'challenge.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'packet':pid,'completed':completed,'quorum':completed>=3}))
    if completed<3: raise SystemExit(2)
if __name__=='__main__': main()
