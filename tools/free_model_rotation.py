#!/usr/bin/env python3
"""Select diverse OpenRouter :free model families from a durable event key."""
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from urllib import request

CATALOG = "https://openrouter.ai/api/v1/models"
FAMILIES = [
    ("nvidia", ("nvidia/",), "adversarial_security"),
    ("poolside", ("poolside/",), "implementation_correctness"),
    ("cohere", ("cohere/",), "evidence_grounding"),
    ("gemma", ("google/gemma",), "test_design_and_edge_cases"),
    ("openai_oss", ("openai/gpt-oss",), "formal_reasoning_baseline"),
    ("dots", ("dots-studio/",), "invariants_and_proof_obligations"),
    ("inkling", ("thinking-machines/",), "uncertainty_and_counterevidence"),
    ("deepseek", ("deepseek/",), "adversarial_reasoning"),
    ("qwen", ("qwen/",), "architecture_and_code"),
    ("llama", ("meta-llama/", "meta/"), "systems_integration"),
    ("mistral", ("mistralai/",), "privacy_compliance_and_failure_modes"),
    ("glm", ("z-ai/", "zhipu/", "zhipuai/", "thudm/"), "semantic_formalization"),
]


def event_slot(event_key: str) -> int:
    key = str(event_key).strip()
    if not key:
        raise ValueError("event_key must be non-empty")
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)


def catalog(key: str) -> list[dict]:
    req=request.Request(CATALOG,headers={"Authorization":f"Bearer {key}"})
    with request.urlopen(req,timeout=60) as r: data=json.loads(r.read().decode())
    return [x for x in data.get("data",[]) if str(x.get("id","")).endswith(":free")]


def choose(models:list[dict],slot:int,count:int=2)->list[dict]:
    out=[]
    for off in range(len(FAMILIES)):
        family,prefixes,role=FAMILIES[(slot+off)%len(FAMILIES)]
        hits=[m for m in models if any(str(m.get("id","")).startswith(p) for p in prefixes)]
        if not hits: continue
        hits.sort(key=lambda m:int(m.get("context_length") or 0),reverse=True)
        model=hits[0]
        out.append({"family":family,"role":role,"model":model["id"],"context_length":model.get("context_length")})
        if len(out)==count: return out
    raise SystemExit(f"Could not resolve {count} diverse :free model families from the live catalog")


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output",default="agents/runtime/free-selection.json"); p.add_argument("--event-key"); p.add_argument("--slot",type=int); p.add_argument("--count",type=int,default=2); args=p.parse_args()
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key: raise SystemExit("OPENROUTER_API_KEY is required")
    event_key_value=args.event_key or os.environ.get("GARDEN_EVENT_KEY") or os.environ.get("GITHUB_SHA")
    if args.slot is not None:
        slot=args.slot; event_key_hash=None; selection_mode="EXPLICIT_EVENT_SLOT"
    else:
        if not event_key_value: raise SystemExit("event key is required unless --slot is supplied; no clock fallback is allowed")
        slot=event_slot(event_key_value); event_key_hash=hashlib.sha256(event_key_value.encode("utf-8")).hexdigest(); selection_mode="DETERMINISTIC_EVENT_HASH_ROTATION"
    models=catalog(key); picked=choose(models,slot,count=args.count)
    payload={"schema":"GardenFreeModelSelection/v2","event_slot":slot,"event_key_sha256":event_key_hash,"selection_mode":selection_mode,"free_catalog_count":len(models),"selected":picked}
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); print(json.dumps(payload)); return 0

if __name__=="__main__": raise SystemExit(main())
