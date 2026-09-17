#!/usr/bin/env python3
"""Gemini-through-OpenRouter retrospective review of Garden v15.9 packets 001-011.
Proposal-only. Looks for new ideas/defects missed by the existing three-family quorum.
"""
from __future__ import annotations
import concurrent.futures as cf, hashlib, json, os, sys, time
from pathlib import Path
from tools import v159_fast_board as base

MODEL='google/gemini-3.8-flash'
OUT=Path('review-results/v159-gemini-retro-001-011')
WORKERS=3


def sha(t): return hashlib.sha256(t.encode()).hexdigest()

def prompt(packet, ph, pid):
    return f'''You are an independent RETROSPECTIVE challenger reviewing Garden v15.8 -> v15.9 packet {pid}.
Three other model families already reviewed this packet, but you have NOT seen their answers. Your job is not to agree: find NEW defects, missing alternatives, simplifications, cross-layer consequences, or reasons to keep the design unchanged that another reviewer could plausibly miss.
Preserve Garden boundaries: capability/evidence do not create authority; UNKNOWN is not PASS; specified != proven/implemented/certified; privacy/rights/consent/authority stay binding; do not add ontology when an existing owner suffices.
Packet SHA256: {ph}

Return concise JSON if possible with keys: verdict, summary, findings, retain, merge_or_remove, context_requests.
Each finding: id, severity, area, claim, source_quote, why_it_matters, minimal_repair, test, confidence, needs_more_context.
Limit to 6 material findings. Prefer genuinely novel information over restating obvious packet concerns. Compare DO_NOTHING and simpler alternatives. Do not claim external tests/searches ran.

--- PACKET ---
{packet}
--- END PACKET ---'''

def review(path,key):
    packet=path.read_text(); ph=sha(packet); pid=path.stem; p=prompt(packet,ph,pid)
    body={
      'model':MODEL,
      'messages':[{'role':'user','content':p}],
      'temperature':0.15,
      'max_tokens':3200,
      'stream':False,
      'reasoning':{'effort':'medium','exclude':True},
      'provider':{'allow_fallbacks':True,'sort':'throughput','data_collection':'deny','zdr':True}
    }
    started=time.time(); status,data,err=base.curl_json(base.OR+'/chat/completions',key,body,220)
    out={'packet_id':pid,'packet_sha256':ph,'model':MODEL,'http_status':status,'transport':err,
         'elapsed_seconds':round(time.time()-started,3),'canonical_effect':False}
    if err:
        out['status']='FAILED'; return out
    choices=(data or {}).get('choices') or []; msg=(choices[0].get('message') or {}) if choices else {}
    text=(msg.get('content') or '').strip(); structured=base.parse_structured(text)
    if structured is not None: out.update(status='COMPLETE_STRUCTURED',review=structured)
    elif len(text)>=200: out.update(status='COMPLETE_RAW',raw_review=text)
    else: out.update(status='FAILED',reason='EMPTY_OR_TOO_SHORT')
    out.update(response_id=(data or {}).get('id'),actual_model=(data or {}).get('model'),provider=(data or {}).get('provider'),usage=(data or {}).get('usage'))
    return out

def main():
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key: raise SystemExit('OPENROUTER_API_KEY missing')
    paths=[]
    p1=Path('review-inputs/v159-batch-001-011/P001_GSL_CORE.txt')
    if p1.exists(): paths.append(p1)
    paths.extend(sorted(Path('review-inputs/v159-batch-002-011').glob('P*.txt')))
    if len(paths)!=11: raise SystemExit(f'expected 11 packets, found {len(paths)}')
    OUT.mkdir(parents=True,exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results=[f.result() for f in [pool.submit(review,p,key) for p in paths]]
    for r in results:
        (OUT/(r['packet_id']+'.json')).write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
    summary={'schema':'GardenGeminiOpenRouterRetrospective/v1','model':MODEL,'packets':11,
             'completed':sum(r.get('status','').startswith('COMPLETE') for r in results),
             'results':[{'packet_id':r['packet_id'],'status':r.get('status'),'http_status':r.get('http_status'),'elapsed_seconds':r.get('elapsed_seconds')} for r in results],
             'canonical_effect':False}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
    if summary['completed'] < 8: raise SystemExit(2)

if __name__=='__main__': main()
