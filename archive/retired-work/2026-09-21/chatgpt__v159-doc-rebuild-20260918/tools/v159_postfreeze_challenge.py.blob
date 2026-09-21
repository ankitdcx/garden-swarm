#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from v159_postfreeze_single import load_model, call, parse_content, sha

ROOT = Path('review-inputs/v159-postfreeze')
OUT = Path('review-results/v159-postfreeze-challenge')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', required=True)
    args = ap.parse_args()
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key:
        raise SystemExit('OPENROUTER_API_KEY missing')
    model = load_model(args.family)
    candidate = (ROOT / 'SYNTHESIZED_POSTFREEZE_CANDIDATE.txt').read_text()
    packet_index = (ROOT / 'SYNTHESIS_EVIDENCE_INDEX.json').read_text()
    prompt = f'''FINAL ADVERSARIAL CHALLENGE — GARDEN v15.9 POST-FREEZE CANDIDATE.\nReviewer family: {args.family}\nCandidate SHA-256: {sha(candidate)}\n\nYou are seeing ChatGPT's synthesized result after blind independent review. Do not vote by popularity. Attack the synthesis.\n\nRules:\n- Identify only material regressions, contradictions, missing cases, unjustified NEW semantics, rights/privacy/authority weakening, or over-engineering.\n- Compare against DO_NOTHING and the stated existing-v15.9 owner mappings.\n- Reject any universal surveillance/observation authority created from technical capability.\n- Reject impossible exhaustive open-world proof requirements; bounded UNKNOWN/non-PASS is valid.\n- Existing owners and aliases are preferred.\n- Review evidence is not authority, proof, implementation, certification or canon.\n- Give at most 8 findings. If design-level synthesis is sound, say ACCEPT and do not invent defects.\n\nReturn concise JSON: {{"verdict":"ACCEPT|CHANGE|BLOCK|EXPAND_REQUIRED","summary":"...","findings":[{{"id":"C1","severity":"CRITICAL|HIGH|MEDIUM|LOW","claim":"...","minimal_repair":"...","test":"...","confidence":"HIGH|MEDIUM|LOW","needs_more_context":false}}],"retain":[],"context_requests":[]}}\n\n--- BLIND EVIDENCE INDEX ---\n{packet_index}\n--- SYNTHESIZED CANDIDATE ---\n{candidate}\n--- END ---'''
    start=time.time(); status,data,error=call(model,prompt,key); structured,raw=parse_content(data)
    result={
      'schema':'GardenV159PostFreezeChallenge/v1','family':args.family,'governed_model':model,
      'candidate_sha256':sha(candidate),'prompt_sha256':sha(prompt),'http_status':status,'error':error,
      'elapsed_seconds':round(time.time()-start,2),'usable':bool(structured is not None or len(raw)>=150),
      'review':structured,'raw_review':None if structured is not None else raw,
      'actual_model':(data or {}).get('model') if isinstance(data,dict) else None,
      'provider':(data or {}).get('provider') if isinstance(data,dict) else None,
      'usage':(data or {}).get('usage') if isinstance(data,dict) else None,
      'canonical_effect':False,'semantic_delta_admitted':False}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/f'{args.family}.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'family':args.family,'usable':result['usable'],'error':error}))
    if not result['usable']:
        raise SystemExit(2)
if __name__=='__main__': main()
