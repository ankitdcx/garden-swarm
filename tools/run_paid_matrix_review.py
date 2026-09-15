#!/usr/bin/env python3
"""Run bounded multi-family paid OpenRouter reviews under hard Garden budget controls."""
from __future__ import annotations
import json, math, os, time
from pathlib import Path
from typing import Any
from urllib import error, request
from tools import matrix_design_review as review
CHAT="https://openrouter.ai/api/v1/chat/completions"; KEY_INFO="https://openrouter.ai/api/v1/key"; SELECTION=Path("agents/runtime/paid-selection.json"); OUT_DIR=Path("agents/outbox/hourly/paid-review"); BUNDLE=Path("agents/outbox/hourly/paid-review-bundle.json")

def _key_usage_daily(key:str)->tuple[float|None,dict[str,Any]]:
    req=request.Request(KEY_INFO,method="GET",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        with request.urlopen(req,timeout=60) as response: data=json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail=exc.read().decode("utf-8",errors="replace"); return None,{"status":f"HTTP_{exc.code}","detail":detail[:1000]}
    except Exception as exc: return None,{"status":"PROVIDER_ERROR","detail":f"{type(exc).__name__}: {exc}"}
    payload=data.get("data") if isinstance(data,dict) and isinstance(data.get("data"),dict) else data
    if not isinstance(payload,dict): return None,{"status":"INVALID_KEY_USAGE_RESPONSE"}
    value=payload.get("usage_daily")
    try: usage_daily=float(value)
    except (TypeError,ValueError): return None,{"status":"DAILY_USAGE_UNVERIFIED","raw_usage_daily":value}
    if isinstance(value, bool) or not math.isfinite(usage_daily) or usage_daily < 0:
        return None,{"status":"DAILY_USAGE_UNVERIFIED","reason":"usage must be finite and nonnegative"}
    return usage_daily,{"status":"VERIFIED","usage_daily":usage_daily,"limit_remaining":payload.get("limit_remaining"),"limit":payload.get("limit"),"limit_reset":payload.get("limit_reset")}

def _call(*,model:dict[str,Any],prompt:str,selection:dict[str,Any],reasoning:dict[str,Any]|None=None)->tuple[dict[str,Any]|None,dict[str,Any]]:
    model_id=str(model["model"]); family=str(model["family"])
    approved_source=selection.get("approved_families") or [row.get("family") for row in selection.get("selected") or []]; approved={str(x) for x in approved_source if x}
    if family not in approved: raise RuntimeError(f"unapproved paid reviewer family: {family}")
    if model_id.endswith(":free"): raise RuntimeError(f"free route is not a paid routine reviewer: {model_id}")
    if len(prompt)>int(selection["max_prompt_characters"]): return None,{"status":"PROMPT_TOO_LARGE","family":family,"model":model_id,"cost":0.0,"prompt_characters":len(prompt)}
    key=os.environ.get("OPENROUTER_API_KEY")
    if not key: return None,{"status":"KEY_UNAVAILABLE","family":family,"model":model_id,"cost":None}
    daily_ceiling=float(selection.get("daily_openrouter_cost_ceiling_usd",0)); per_call_ceiling=float(selection["routine_model_call_cost_ceiling_usd"])
    if daily_ceiling>0:
        usage_daily,usage_receipt=_key_usage_daily(key)
        if usage_daily is None: return None,{"status":"DAILY_USAGE_UNVERIFIED","family":family,"model":model_id,"cost":None,"daily_budget_receipt":usage_receipt}
        if usage_daily+per_call_ceiling>daily_ceiling: return None,{"status":"DAILY_BUDGET_RESERVED_EXHAUSTED","family":family,"model":model_id,"cost":0.0,"usage_daily_before_call":usage_daily,"daily_openrouter_cost_ceiling_usd":daily_ceiling,"reserved_max_call_cost_usd":per_call_ceiling,"daily_budget_receipt":usage_receipt}
    else: usage_daily=None; usage_receipt={"status":"NO_DAILY_CEILING_CONFIGURED"}
    provider_policy=selection["provider_policy"]; max_price=provider_policy["max_price_usd_per_million_tokens"]
    body={"model":model_id,"messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":int(selection["max_output_tokens"]),"provider":{"sort":provider_policy.get("sort","price"),"allow_fallbacks":bool(provider_policy.get("allow_fallbacks",True)),"data_collection":provider_policy.get("data_collection","deny"),"max_price":{"prompt":float(max_price["prompt"]),"completion":float(max_price["completion"])}}}
    if reasoning is not None: body["reasoning"]=reasoning
    req=request.Request(CHAT,method="POST",data=json.dumps(body).encode("utf-8"),headers={"Authorization":f"Bearer {key}","Content-Type":"application/json","HTTP-Referer":"https://github.com/ankitdcx/garden-swarm","X-Title":"Garden Routine Paid Design Review"})
    try:
        with request.urlopen(req,timeout=300) as response: data=json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail=exc.read().decode("utf-8",errors="replace"); return None,{"status":f"HTTP_{exc.code}","family":family,"model":model_id,"cost":None,"detail":detail[:1000],"usage_daily_before_call":usage_daily,"daily_budget_receipt":usage_receipt}
    except Exception as exc: return None,{"status":"PROVIDER_ERROR","family":family,"model":model_id,"cost":None,"detail":f"{type(exc).__name__}: {exc}","usage_daily_before_call":usage_daily,"daily_budget_receipt":usage_receipt}
    usage=data.get("usage") or {}; cost=usage.get("cost")
    if cost is None: return None,{"status":"COST_UNVERIFIED","family":family,"model":model_id,"cost":None,"usage":usage,"usage_daily_before_call":usage_daily,"daily_budget_receipt":usage_receipt}
    try:
        if isinstance(cost, bool): raise ValueError("boolean cost")
        cost=float(cost)
        if not math.isfinite(cost) or cost < 0: raise ValueError("invalid cost")
    except (TypeError, ValueError):
        return None,{"status":"COST_UNVERIFIED","family":family,"model":model_id,"cost":None,"reason":"cost must be finite and nonnegative","usage_daily_before_call":usage_daily,"daily_budget_receipt":usage_receipt}
    if cost>per_call_ceiling: return None,{"status":"MODEL_COST_CEILING_EXCEEDED","family":family,"model":model_id,"cost":cost,"usage":usage,"usage_daily_before_call":usage_daily,"daily_budget_receipt":usage_receipt}
    try: content=data["choices"][0]["message"].get("content","")
    except Exception: content=""
    raw=review._clean_json(content)
    return raw,{"status":"CALLED","family":family,"model":model_id,"cost":cost,"usage":usage,"usage_daily_before_call":usage_daily,"daily_budget_receipt":usage_receipt}

def main()->int:
    root=Path(".").resolve(); matrix,target=review.load_matrix(root)
    if target.get("public_only") is not True: raise SystemExit("paid public reviewer refused non-public target")
    source,trace=review.extract_target(root,target); selection=json.loads(SELECTION.read_text(encoding="utf-8"))
    if selection.get("schema")!="GardenPaidModelSelection/v2": raise SystemExit("unsupported paid reviewer selection schema")
    if selection.get("design_epoch")!=matrix.get("design_epoch"): raise SystemExit("paid reviewer selection DesignEpoch mismatch")
    selected=list(selection.get("selected") or []); families=[str(row.get("family")) for row in selected]; approved=[str(x) for x in selection.get("approved_families") or []]
    if families!=approved or len(set(families))!=len(families) or len(families)<2: raise SystemExit("paid routine execution requires the approved distinct family set")
    attempts=[]; findings=[]; OUT_DIR.mkdir(parents=True,exist_ok=True); hourly_ceiling=float(selection["routine_hourly_cost_ceiling_usd"]); per_call_ceiling=float(selection["routine_model_call_cost_ceiling_usd"]); charged_total=0.0
    for model in selected:
        family=str(model["family"])
        if charged_total+per_call_ceiling>hourly_ceiling:
            attempts.append({"phase":"INDEPENDENT","status":"HOURLY_BUDGET_RESERVED_EXHAUSTED","family":family,"model":model["model"],"cost":0.0,"charged_total_before_call":charged_total,"hourly_cost_ceiling_usd":hourly_ceiling,"reserved_max_call_cost_usd":per_call_ceiling}); continue
        prompt=review.independent_prompt(target=target,source=source,trace=trace,model=model); raw,attempt=_call(model=model,prompt=prompt,selection=selection); attempt["phase"]="INDEPENDENT"; attempts.append(attempt)
        if isinstance(attempt.get("cost"),(int,float)) and float(attempt["cost"])>=0: charged_total+=float(attempt["cost"])
        if raw is None: continue
        try: finding=review.validate_independent(raw,target_id=target["target_id"],family=family,model_id=str(model["model"]))
        except Exception as exc:
            attempts.append({"phase":"INDEPENDENT_PARSE","status":"INVALID_OUTPUT","family":family,"model":model["model"],"cost":0.0,"detail":str(exc)}); continue
        findings.append(finding); (OUT_DIR/f"{family}-independent.json").write_text(json.dumps(finding,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    charged=[float(row["cost"]) for row in attempts if isinstance(row.get("cost"),(int,float)) and float(row["cost"])>=0]; total_cost=sum(charged)
    status="HOURLY_COST_CEILING_EXCEEDED" if total_cost>hourly_ceiling else ("PAID_BLIND_REVIEW_COMPLETE_PROPOSALS_ONLY" if len({row["reviewer_family"] for row in findings})==len(families) else "PARTIAL_PAID_REVIEW_PROPOSALS_ONLY")
    bundle={"schema":"GardenPaidDesignReviewBundle/v1","created_at_unix":int(time.time()),"design_epoch":matrix["design_epoch"],"canonical_source_root_sha256":matrix["canonical_source_root_sha256"],"target_id":target["target_id"],"source_trace":trace,"selected_families":families,"completed_families":sorted({row["reviewer_family"] for row in findings}),"provider_attempts":attempts,"independent_findings":findings,"daily_openrouter_cost_ceiling_usd":float(selection["daily_openrouter_cost_ceiling_usd"]),"routine_hourly_cost_ceiling_usd":hourly_ceiling,"actual_cost_usd":round(total_cost,8),"status":status,"requires_separate_gemini_lane":True,"requires_separate_chatgpt_lane":True,"requires_cross_examination":True,"semantic_delta_admitted":False}
    BUNDLE.parent.mkdir(parents=True,exist_ok=True); BUNDLE.write_text(json.dumps(bundle,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"); print(json.dumps({"target_id":target["target_id"],"status":status,"selected_families":families,"completed_families":bundle["completed_families"],"actual_cost_usd":bundle["actual_cost_usd"],"hourly_cost_ceiling_usd":hourly_ceiling,"daily_openrouter_cost_ceiling_usd":bundle["daily_openrouter_cost_ceiling_usd"],"semantic_delta_admitted":False},sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
