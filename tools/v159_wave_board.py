#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures as cf, hashlib, json, os, subprocess, sys, time
from pathlib import Path

OR='https://openrouter.ai/api/v1'
OUT=Path('review-results/v159-wave1')
MODELS={
 'deepseek':['deepseek/deepseek-v4-flash-0731','deepseek/deepseek-v4.1-flash'],
 'glm':['z-ai/glm-5.3-flash','z-ai/glm-5.3'],
 'xiaomi':['xiaomi/mimo-v2.5','xiaomi/mimo-v2.5-pro'],
 'gemini':['google/gemini-3.8-flash'],
}
TIMEOUT=220

def sha(t): return hashlib.sha256(t.encode()).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,separators=(',',':'))

def post(body,key):
    cmd=['curl','-sS','--connect-timeout','10','--max-time',str(TIMEOUT),OR+'/chat/completions',
         '-X','POST','-H','Authorization: Bearer '+key,'-H','Content-Type: application/json',
         '-H','Accept: application/json','--data-binary','@-','-w','\n%{http_code}']
    p=subprocess.run(cmd,input=canon(body),text=True,capture_output=True,timeout=TIMEOUT+10)
    raw=p.stdout
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
            if isinstance(o,dict) and isinstance(o.get('findings',[]),list): return o
        except: pass
    return None

def prompt(packet,ph,family):
    return f'''BLIND INDEPENDENT GARDEN v15.8 -> v15.9 DESIGN REVIEW.
You have not seen ChatGPT baseline or peer answers. Do not infer consensus.
Reviewer family: {family}. Packet SHA256: {ph}.
Preserve Garden boundaries: authority does not arise from capability/evidence/model agreement; UNKNOWN is not PASS; specification != proof != implementation != validation != certification; privacy/rights/consent/safety/law remain binding; prefer existing owners and simpler repairs over ontology growth.

TASK
- Find at most 6 material defects, ambiguities, missing semantics, unsafe compositions, implementation blockers or simplifications.
- Compare each proposed change against DO_NOTHING.
- Give a minimal repair and falsifiable invariant/test.
- If a conclusion materially requires source not present, set needs_more_context=true and request the exact missing anchor instead of guessing.
- Do not claim external searches or tests were run.

Return concise JSON if possible:
{{"verdict":"KEEP|CHANGE|MIXED|EXPAND_REQUIRED","summary":"...","findings":[{{"id":"F1","severity":"CRITICAL|HIGH|MEDIUM|LOW","area":"...","claim":"...","source_quote":"...","why_it_matters":"...","minimal_repair":"...","test":"...","confidence":"HIGH|MEDIUM|LOW","needs_more_context":false}}],"retain":[],"merge_or_remove":[],"context_requests":[]}}

--- SOURCE PACKET ---
{packet}
--- END PACKET ---'''

def call(family,candidates,packet,ph,key):
    p=prompt(packet,ph,family); out={'family':family,'prompt_sha256':sha(p),'attempts':[]}; start=time.time()
    for mid in candidates:
        body={'model':mid,'messages':[{'role':'user','content':p}],'temperature':0.1,'max_tokens':3200,'stream':False,
              'provider':{'allow_fallbacks':True,'sort':'throughput','data_collection':'deny','zdr':True}}
        if family=='glm': body['reasoning']={'effort':'low','exclude':True}
        a=time.time(); status,data,err=post(body,key); att={'model':mid,'http_status':status,'transport':err,'elapsed_seconds':round(time.time()-a,2)}; out['attempts'].append(att)
        if err:
            if err.startswith('CURL_'): break
            continue
        choices=(data or {}).get('choices') or []; msg=(choices[0].get('message') or {}) if choices else {}; text=(msg.get('content') or '').strip(); structured=parse(text)
        if structured is not None: out.update(status='COMPLETE_STRUCTURED',review=structured)
        elif len(text)>=200: out.update(status='COMPLETE_RAW',raw_review=text)
        else: att['result']='EMPTY_OR_TOO_SHORT'; continue
        out.update(selected_model=mid,actual_model=(data or {}).get('model'),provider=(data or {}).get('provider'),usage=(data or {}).get('usage'),response_id=(data or {}).get('id')); break
    if 'status' not in out: out['status']='FAILED'
    out['elapsed_seconds']=round(time.time()-start,2); return out

def render(r):
    lines=['GARDEN v15.9 WAVE REVIEW',f"packet: {r['packet_id']}",f"packet_sha256: {r['packet_sha256']}",f"usable: {r['completed']}/4",f"quorum: {r['quorum']}",'proposal evidence only','']
    for x in r['reviews']:
        lines += ['='*80,f"{x['family']} | {x['status']}"]
        if x.get('selected_model'): lines.append('model: '+x['selected_model'])
        if x.get('review'):
            rv=x['review']; lines += ['verdict: '+str(rv.get('verdict','')),'summary: '+str(rv.get('summary',''))]
            for f in rv.get('findings',[])[:6]: lines += ['',f"{f.get('id')} [{f.get('severity')}] {f.get('area')}",'claim: '+str(f.get('claim','')),'repair: '+str(f.get('minimal_repair','')),'test: '+str(f.get('test',''))]
        elif x.get('raw_review'): lines += ['RAW REVIEW:',x['raw_review']]
    return '\n'.join(lines)+'\n'

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: v159_wave_board.py PACKET')
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key: raise SystemExit('OPENROUTER_API_KEY missing')
    path=Path(sys.argv[1]); packet=path.read_text(); ph=sha(packet); pid=path.stem
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        reviews=[f.result() for f in [pool.submit(call,fam,cands,packet,ph,key) for fam,cands in MODELS.items()]]
    completed=sum(x.get('status','').startswith('COMPLETE') for x in reviews)
    result={'schema':'GardenWaveBlindReview/v1','packet_id':pid,'packet_path':str(path),'packet_sha256':ph,'completed':completed,'quorum':completed>=3,'reviews':reviews,'canonical_effect':False,'semantic_delta_admitted':False}
    out=OUT/pid; out.mkdir(parents=True,exist_ok=True); (out/'board.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n'); (out/'board.txt').write_text(render(result))
    print(json.dumps({'packet':pid,'completed':completed,'quorum':completed>=3}))
    if completed<3: raise SystemExit(2)
if __name__=='__main__': main()
