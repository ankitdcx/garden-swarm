#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from tools.free_model_rotation import catalog, choose, event_slot


def _adaptive_choose(models:list[dict],slot:int,requested:int,minimum:int)->list[dict]:
    last_error=None
    for count in range(requested,minimum-1,-1):
        try: return choose(models,slot,count=count)
        except SystemExit as exc: last_error=exc
    raise SystemExit(f"Could not resolve the minimum {minimum} distinct :free reviewer families from the live catalog; last_error={last_error}")


def main()->int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output",default="agents/runtime/free-selection.json"); parser.add_argument("--event-key"); parser.add_argument("--slot",type=int); parser.add_argument("--count",type=int,default=3); parser.add_argument("--minimum-count",type=int,default=1); args=parser.parse_args()
    if args.count<1: raise SystemExit("reviewer selection count must be at least one")
    if args.minimum_count<1 or args.minimum_count>args.count: raise SystemExit("minimum-count must be between one and count")
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key: raise SystemExit("OPENROUTER_API_KEY is required")
    event_key_value=args.event_key or os.environ.get("GARDEN_EVENT_KEY") or os.environ.get("GITHUB_SHA")
    if args.slot is not None:
        slot=args.slot; event_key_hash=None; selection_mode="EXPLICIT_EVENT_SLOT"
    else:
        if not event_key_value: raise SystemExit("event key is required unless --slot is supplied; no clock fallback is allowed")
        slot=event_slot(event_key_value); event_key_hash=hashlib.sha256(event_key_value.encode("utf-8")).hexdigest(); selection_mode="DETERMINISTIC_EVENT_HASH_ROTATION"
    models=catalog(key); selected=_adaptive_choose(models,slot,requested=args.count,minimum=args.minimum_count); families=[row["family"] for row in selected]
    if len(set(families))!=len(families): raise SystemExit("reviewer selection is not family-independent")
    if not all(str(row["model"]).endswith(":free") for row in selected): raise SystemExit("non-free reviewer route refused")
    payload={"schema":"GardenFreeModelSelection/v2","purpose":"MULTI_TRACK_REVIEW_MATRIX","event_slot":slot,"event_key_sha256":event_key_hash,"selection_mode":selection_mode,"free_catalog_count":len(models),"requested_family_count":args.count,"required_family_count":args.minimum_count,"selected_family_count":len(selected),"selection_scope":"EXECUTION_BUDGET_ONLY_NOT_ADMISSION_QUORUM","selected":selected,"cost_policy":"OpenRouter :free routes only; reviewer calls must independently report usage.cost == 0 before review completion is eligible."}
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8"); print(json.dumps(payload)); return 0

if __name__=="__main__": raise SystemExit(main())
