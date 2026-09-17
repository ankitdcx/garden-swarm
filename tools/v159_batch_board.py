#!/usr/bin/env python3
"""Review a directory of bounded Garden v15.9 packets with 4 OpenRouter families + direct Gemini.
Proposal evidence only. No admission, merge or canonical effect.
"""
from __future__ import annotations
import concurrent.futures as cf, hashlib, json, os, subprocess, sys, time
from pathlib import Path
from tools import v159_fast_board as base

GEMINI_MODEL=os.getenv('GEMINI_MODEL','gemini-3.8-flash')
GEMINI_BASE='https://generativelanguage.googleapis.com/v1beta/models'
PACKET_WORKERS=2
OUT_ROOT=Path('review-results/v159-batch-002-011')


def sha(t): return hashlib.sha256(t.encode()).hexdigest()


def gemini_call(packet, packet_hash, key):
    started=time.time(); fam='gemini'; p=base.prompt(packet,packet_hash,fam)
    out={'family':fam,'prompt_sha256':sha(p),'started':started,'attempts':[],'selected_model':GEMINI_MODEL}
    if not key:
        out.update(status='UNAVAILABLE',reason='GEMINI_API_KEY_NOT_CONFIGURED',elapsed_seconds=0); return out
    body={'contents':[{'role':'user','parts':[{'text':p}]}],
          'generationConfig':{'maxOutputTokens':3400,'temperature':0.1,'responseMimeType':'application/json'}}
    url=f'{GEMINI_BASE}/{GEMINI_MODEL}:generateContent'
    cmd=['curl','-sS','--connect-timeout','10','--max-time','210','-X','POST',url,
         '-H','Content-Type: application/json','-H','x-goog-api-key: '+key,
         '--data-binary','@-','-w','\n%{http_code}']
    try:
        q=subprocess.run(cmd,input=json.dumps(body,ensure_ascii=False),text=True,capture_output=True,timeout=220)
        raw=q.stdout
        if '\n' not in raw:
            out['attempts'].append({'model':GEMINI_MODEL,'result':'NO_HTTP_STATUS'}); out['status']='FAILED'; return out
        payload,st=raw.rsplit('\n',1); status=int(st.strip() or 0)
        att={'model':GEMINI_MODEL,'http_status':status,'elapsed_seconds':round(time.time()-started,3)}
        out['attempts'].append(att)
        if q.returncode!=0 or not 200<=status<300:
            att['result']='HTTP_OR_CURL_FAILURE'; out['status']='FAILED'; return out
        data=json.loads(payload); parts=data.get('candidates',[{}])[0].get('content',{}).get('parts',[])
        text=''.join(x.get('text','') for x in parts).strip(); structured=base.parse_structured(text)
        if structured is not None: out.update(status='COMPLETE_STRUCTURED',review=structured)
        elif len(text)>=200: out.update(status='COMPLETE_RAW',raw_review=text)
        else: out.update(status='FAILED',reason='EMPTY_OR_TOO_SHORT')
        out.update(actual_model=data.get('modelVersion') or GEMINI_MODEL,usage=data.get('usageMetadata') or {})
    except Exception as exc:
        out.update(status='FAILED',reason=type(exc).__name__)
    out['elapsed_seconds']=round(time.time()-started,3); return out


def render(result):
    lines=['GARDEN v15.9 FIVE-LANE BLIND REVIEW',f"packet: {result['packet_id']}",
           f"packet_sha256: {result['packet_sha256']}",f"usable_reviews: {result['completed']}/5",
           f"quorum: {result['quorum']}",'proposal evidence only; no canonical admission','']
    for r in result['reviews']:
        lines += ['='*88,f"{r['family']} | {r['status']}"]
        if r.get('selected_model'): lines.append('selected_model: '+str(r['selected_model']))
        if r.get('review'):
            rv=r['review']; lines += ['verdict: '+str(rv.get('verdict','')),'summary: '+str(rv.get('summary',''))]
            for f in rv.get('findings',[])[:8]:
                lines += ['',f"{f.get('id')} [{f.get('severity')}] {f.get('area')}",
                          'claim: '+str(f.get('claim','')),'repair: '+str(f.get('minimal_repair','')),
                          'test: '+str(f.get('test',''))]
        elif r.get('raw_review'): lines += ['RAW REVIEW:',r['raw_review']]
        elif r.get('reason'): lines += ['reason: '+str(r['reason'])]
    return '\n'.join(lines)+'\n'


def review_packet(path, or_key, gem_key, resolution, ignores):
    packet=path.read_text(); ph=sha(packet); pid=path.stem
    with cf.ThreadPoolExecutor(max_workers=5) as pool:
        futs=[pool.submit(base.call_family,f,resolution['candidates'].get(f,[]),ignores,packet,ph,or_key) for f in base.FAMILIES]
        futs.append(pool.submit(gemini_call,packet,ph,gem_key))
        reviews=[f.result() for f in futs]
    completed=sum(r.get('status') in ('COMPLETE_STRUCTURED','COMPLETE_RAW') for r in reviews)
    result={'schema':'GardenFiveLaneBlindBoard/v1','packet_id':pid,'packet_path':str(path),'packet_sha256':ph,
            'completed':completed,'quorum':completed>=3,'reviews':reviews,'semantic_delta_admitted':False,'canonical_effect':False}
    out=OUT_ROOT/pid; out.mkdir(parents=True,exist_ok=True)
    (out/'board.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    (out/'board.txt').write_text(render(result))
    print(f'{pid}: {completed}/5 usable; quorum={completed>=3}')
    return result


def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else 'review-inputs/v159-batch-002-011')
    packets=sorted(root.glob('P*.txt'))
    if len(packets)!=10: raise SystemExit(f'expected 10 packets, found {len(packets)}')
    or_key=os.environ.get('OPENROUTER_API_KEY'); gem_key=os.environ.get('GEMINI_API_KEY')
    if not or_key: raise SystemExit('OPENROUTER_API_KEY missing')
    preferred,markers,ignores=base.load_constraints(); resolution=base.resolve_models(or_key,preferred,markers)
    with cf.ThreadPoolExecutor(max_workers=PACKET_WORKERS) as pool:
        results=[f.result() for f in [pool.submit(review_packet,p,or_key,gem_key,resolution,ignores) for p in packets]]
    summary={'schema':'GardenV159BatchReviewSummary/v1','packets':len(results),
             'quorum_passed':sum(r['quorum'] for r in results),'gemini_model':GEMINI_MODEL,
             'results':[{'packet_id':r['packet_id'],'completed':r['completed'],'quorum':r['quorum']} for r in results]}
    OUT_ROOT.mkdir(parents=True,exist_ok=True); (OUT_ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
    if not all(r['quorum'] for r in results): raise SystemExit(2)

if __name__=='__main__': main()
