#!/usr/bin/env python3
"""Evidence-bound reviewer quality evaluation for Garden OpenRouter slots."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any, Iterable
POLICY_PATH=Path("agents/reviewer-quality-policy.json"); REGISTRY_PATH=Path("agents/reviewer-slot-registry.json")
RECEIPT_SCHEMA="GardenReviewerQualityReceipt/v1"; SUMMARY_SCHEMA="GardenReviewerSlotQualitySummary/v1"; SHADOW_SCHEMA="GardenReviewerShadowBenchmark/v1"; TRANSITION_SCHEMA="GardenReviewerTransitionProposal/v1"
def load_policy(path:Path=POLICY_PATH):
 data=json.loads(path.read_text());
 if data.get("schema")!="GardenReviewerQualityPolicy/v1": raise ValueError("unsupported reviewer quality policy")
 weights=data.get("quality_dimensions") or {}
 if not weights or abs(sum(float(v) for v in weights.values())-1.0)>1e-9: raise ValueError("quality dimension weights must sum to one")
 return data
def load_registry(path:Path=REGISTRY_PATH):
 data=json.loads(path.read_text());
 if data.get("schema")!="GardenReviewerSlotRegistry/v1": raise ValueError("unsupported reviewer slot registry")
 return data
def _score(value,name):
 if isinstance(value,bool): raise ValueError(f"{name} must be numeric")
 value=float(value)
 if not 0<=value<=1: raise ValueError(f"{name} must be in [0,1]")
 return value
def validate_receipt(receipt,policy=None):
 policy=policy or load_policy()
 if receipt.get("schema")!=RECEIPT_SCHEMA: raise ValueError(f"schema must be {RECEIPT_SCHEMA}")
 for field in ("receipt_id","task_id","slot_id","family","model","source_packet_sha256","response_sha256","phase","context_sufficiency","adjudicator"):
  if not isinstance(receipt.get(field),str) or not receipt[field].strip(): raise ValueError(f"{field} must be non-empty")
 for field in ("source_packet_sha256","response_sha256"):
  value=receipt[field].lower()
  if len(value)!=64 or any(c not in "0123456789abcdef" for c in value): raise ValueError(f"{field} must be sha256")
 if receipt["context_sufficiency"] not in {"SUFFICIENT","EXPAND_REQUIRED","FULL_CONTEXT_REQUIRED"}: raise ValueError("invalid context_sufficiency")
 scores=receipt.get("scores"); expected=set(policy["quality_dimensions"])
 if not isinstance(scores,dict) or set(scores)!=expected: raise ValueError("scores must exactly match policy quality dimensions")
 normalized={name:_score(scores[name],name) for name in expected}; evidence=receipt.get("evidence_refs")
 if not isinstance(evidence,list) or not evidence or any(not isinstance(x,str) or not x.strip() for x in evidence): raise ValueError("quality scores require evidence_refs")
 hard=receipt.get("hard_failures",[])
 if not isinstance(hard,list) or any(x not in policy["hard_failures"] for x in hard): raise ValueError("unknown hard failure")
 if receipt["context_sufficiency"]!="SUFFICIENT" and normalized["context_handling"]>.8: raise ValueError("insufficient-context receipt cannot claim near-perfect context handling")
 if receipt.get("agreement_with_peers") is not None or receipt.get("agreement_with_chatgpt") is not None: raise ValueError("agreement is not an admissible quality score")
 result=dict(receipt); result["scores"]=normalized; return result
def weighted_score(receipt,policy=None):
 policy=policy or load_policy(); receipt=validate_receipt(receipt,policy)
 if receipt.get("hard_failures"): return 0.0
 return round(sum(receipt["scores"][k]*float(w) for k,w in policy["quality_dimensions"].items()),6)
def summarize(receipts:Iterable[dict[str,Any]],*,slot_id,family,model,policy=None):
 policy=policy or load_policy(); selected=[]
 for raw in receipts:
  r=validate_receipt(raw,policy)
  if (r["slot_id"],r["family"],r["model"])==(slot_id,family,model): selected.append(r)
 if not selected: return {"schema":SUMMARY_SCHEMA,"slot_id":slot_id,"family":family,"model":model,"receipt_count":0,"weighted_quality":None,"hard_failure_count":0,"unique_material_contribution":None,"recommended_state":"ACTIVE","boundary":"No quality evidence yet; ACTIVE preserves the governed baseline, not a quality proof."}
 scores=[weighted_score(r,policy) for r in selected]; hard_count=sum(len(r.get("hard_failures",[])) for r in selected); weighted=round(sum(scores)/len(scores),6); unique=round(sum(r["scores"]["unique_material_contribution"] for r in selected)/len(selected),6); life=policy["lifecycle"]
 if hard_count: state="QUARANTINED"
 elif len(selected)>=int(life["ordinary_window_minimum_receipts"]) and weighted<float(life["quarantine_when_weighted_quality_below"]): state="QUARANTINED"
 elif len(selected)>=int(life["ordinary_window_minimum_receipts"]) and weighted<float(life["degrade_when_weighted_quality_below"]): state="DEGRADED"
 else: state="ACTIVE"
 return {"schema":SUMMARY_SCHEMA,"slot_id":slot_id,"family":family,"model":model,"receipt_count":len(selected),"weighted_quality":weighted,"hard_failure_count":hard_count,"unique_material_contribution":unique,"recommended_state":state,"boundary":"Quality summary is operational evidence only and does not self-modify the reviewer registry."}
def shadow_benchmark(incumbent,candidate,*,packet_count,policy=None):
 policy=policy or load_policy(); rule=policy["shadow_replacement"]; reasons=[]
 if packet_count<int(rule["minimum_shadow_packets"]): reasons.append("INSUFFICIENT_SHADOW_PACKETS")
 if int(candidate.get("hard_failure_count",0))!=0: reasons.append("CANDIDATE_HARD_FAILURE")
 iq,cq=incumbent.get("weighted_quality"),candidate.get("weighted_quality")
 if iq is None or cq is None: reasons.append("MISSING_QUALITY_SUMMARY")
 elif float(cq)-float(iq)<float(rule["minimum_weighted_quality_improvement"]): reasons.append("QUALITY_IMPROVEMENT_TOO_SMALL")
 iu,cu=incumbent.get("unique_material_contribution"),candidate.get("unique_material_contribution")
 if iu is None or cu is None: reasons.append("MISSING_UNIQUE_CONTRIBUTION_SUMMARY")
 elif float(cu)-float(iu)<float(rule["candidate_unique_contribution_floor_relative_to_incumbent"]): reasons.append("UNIQUE_CONTRIBUTION_REGRESSION")
 return {"schema":SHADOW_SCHEMA,"packet_count":packet_count,"incumbent":incumbent,"candidate":candidate,"qualified":not reasons,"blocking_reasons":reasons,"registry_change_required":True,"boundary":"Shadow qualification is evidence for a registry PR, not permission for a silent model swap."}
def validate_transition(*,current_state,target_state,shadow=None,registry_pr_declared=False,policy=None):
 policy=policy or load_policy(); states=set(policy["lifecycle"]["states"])
 if current_state not in states or target_state not in states: raise ValueError("unknown reviewer lifecycle state")
 reasons=[]
 if current_state==target_state: return {"allowed":True,"reasons":[],"registry_pr_required":False}
 if target_state=="ACTIVE" and current_state in {"DEGRADED","QUARANTINED"}: reasons.append("DIRECT_RETURN_TO_ACTIVE_FORBIDDEN_USE_SHADOW_CHALLENGED")
 if target_state=="SHADOW_CHALLENGED" and current_state not in {"DEGRADED","QUARANTINED"}: reasons.append("SHADOW_CHALLENGE_REQUIRES_DEGRADED_OR_QUARANTINED_SOURCE")
 if current_state=="SHADOW_CHALLENGED" and target_state=="ACTIVE":
  if not shadow or shadow.get("schema")!=SHADOW_SCHEMA or shadow.get("qualified") is not True: reasons.append("QUALIFIED_SHADOW_BENCHMARK_REQUIRED")
  if not registry_pr_declared: reasons.append("GOVERNED_REGISTRY_PR_REQUIRED")
 return {"allowed":not reasons,"reasons":reasons,"registry_pr_required":current_state=="SHADOW_CHALLENGED" and target_state=="ACTIVE"}
def transition_proposal(summary,*,current_state,shadow=None,registry_pr_declared=False,policy=None):
 policy=policy or load_policy(); recommended=summary["recommended_state"]
 if recommended=="ACTIVE" and current_state in {"DEGRADED","QUARANTINED"}: recommended="SHADOW_CHALLENGED"
 check=validate_transition(current_state=current_state,target_state=recommended,shadow=shadow,registry_pr_declared=registry_pr_declared,policy=policy)
 return {"schema":TRANSITION_SCHEMA,"slot_id":summary["slot_id"],"model":summary["model"],"current_state":current_state,"recommended_state":recommended,"change_required":current_state!=recommended,"allowed":check["allowed"],"blocking_reasons":check["reasons"],"registry_pr_required":check["registry_pr_required"] or current_state!=recommended,"semantic_delta_admitted":False}
def main():
 p=argparse.ArgumentParser(); p.add_argument("receipts"); p.add_argument("--slot",required=True); p.add_argument("--family",required=True); p.add_argument("--model",required=True); a=p.parse_args(); raw=json.loads(Path(a.receipts).read_text()); receipts=raw if isinstance(raw,list) else [raw]; print(json.dumps(summarize(receipts,slot_id=a.slot,family=a.family,model=a.model),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
