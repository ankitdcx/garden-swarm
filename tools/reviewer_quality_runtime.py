#!/usr/bin/env python3
"""Durably queue recorded OpenRouter reviews for external ChatGPT quality adjudication."""
from __future__ import annotations
import json,time
from pathlib import Path
from typing import Any
from tools import independent_branch_protocol as protocol
ASSESSMENT_SCHEMA="GardenReviewerQualityAssessmentRequest/v1"; QUALITY_STATUS="AWAITING_CHATGPT_ADJUDICATION"; OVERDUE_STATUS="OVERDUE_CHATGPT_ADJUDICATION"; WORKER_PROTOCOL=protocol.PROTOCOL_ID; POLICY_PATH=Path("agents/reviewer-quality-policy.json")
def load_policy(root:Path=Path(".")):
 data=json.loads((root/POLICY_PATH).read_text())
 if data.get("schema")!="GardenReviewerQualityPolicy/v1": raise ValueError("unsupported reviewer quality policy")
 return data
def _slot_for(registry,family,model):
 if registry.get("schema")!="GardenReviewerSlotRegistry/v1": raise ValueError("unsupported reviewer slot registry")
 matches=[r for r in registry.get("slots",[]) if r.get("family")==family and r.get("model")==model]
 if len(matches)!=1: raise ValueError("recorded reviewer does not resolve exactly one governed slot")
 return matches[0]
def _record_for_attempt(state,attempt):
 cycle=(state.get("convergence_cycles") or {}).get(attempt.get("cycle"))
 if not isinstance(cycle,dict): raise ValueError("recorded reviewer attempt has no convergence cycle")
 h=attempt.get("finding_sha256"); records=[]; records.extend((cycle.get("blind") or {}).values())
 for rows in (cycle.get("reconcile") or {}).values(): records.extend(rows or [])
 records.extend((cycle.get("final") or {}).values()); records.extend((cycle.get("confirm") or {}).values()); matches=[r for r in records if r.get("finding_sha256")==h]
 if len(matches)!=1: raise ValueError("recorded reviewer finding does not resolve exactly one branch record")
 return matches[0]
def _request_for(state,attempt,registry,now):
 response=attempt.get("response_text")
 if not isinstance(response,str) or not response: raise ValueError("recorded review is missing response text")
 family=str(attempt.get("family") or ""); model=str(attempt.get("model") or ""); slot=_slot_for(registry,family,model); record=_record_for_attempt(state,attempt); finding=record.get("finding") or {}; response_hash=protocol.sha256_text(response)
 core={"task_key":attempt.get("task_key"),"cycle":attempt.get("cycle"),"review_slot":attempt.get("slot"),"slot_id":slot["slot_id"],"family":family,"model":model,"phase":attempt.get("phase"),"source_packet_sha256":attempt.get("source_packet_sha256"),"response_sha256":response_hash,"finding_sha256":attempt.get("finding_sha256"),"context_sufficiency":finding.get("context_sufficiency"),"peer_content_seen":bool(record.get("peer_content_seen")),"response_id":attempt.get("response_id"),"run_id":attempt.get("run_id")}
 return {"schema":ASSESSMENT_SCHEMA,"request_id":protocol.sha256_value(core),**core,"status":QUALITY_STATUS,"assessment_owner":"EXTERNAL_CHATGPT_FRONTIER","quality_receipt_schema":"GardenReviewerQualityReceipt/v1","cost_usd":attempt.get("cost"),"created":now,"semantic_delta_admitted":False,"quality_assessment_is_not_proof_or_authority":True}
def maintain_quality_queue(state,policy,*,now=None):
 now=time.time() if now is None else float(now); rule=policy["runtime_assessment_queue"]; queue=state.setdefault("reviewer_quality_queue",[]); archive=state.setdefault("reviewer_quality_archive",[]); closed=set(rule["closed_statuses"]); kept=[]; moved=overdue=0
 for row in queue:
  if not isinstance(row,dict): continue
  status=row.get("status")
  if status in closed:
   archive.append({"request_id":row.get("request_id"),"response_sha256":row.get("response_sha256"),"status":status,"closed_at":row.get("closed_at"),"archived_at":now}); moved+=1; continue
  age=max(0,(now-float(row.get("created",now)))/3600)
  if status==QUALITY_STATUS and age>=float(rule["overdue_after_hours"]): row["status"]=OVERDUE_STATUS; row["overdue_at"]=now; status=OVERDUE_STATUS
  if status in {QUALITY_STATUS,OVERDUE_STATUS}: overdue+=int(status==OVERDUE_STATUS)
  kept.append(row)
 max_archive=int(rule["closed_archive_hash_limit"])
 if len(archive)>max_archive: archive[:]=archive[-max_archive:]
 queue[:]=kept; pending=sum(1 for r in queue if r.get("status") in {QUALITY_STATUS,OVERDUE_STATUS})
 debt={"schema":"GardenReviewerQualityDebtReceipt/v1","pending":pending,"overdue":overdue,"soft_limit":int(rule["pending_soft_limit"]),"hard_limit":int(rule["pending_hard_limit"]),"status":"BLOCK_NEW_CONVERGENCE" if pending>=int(rule["pending_hard_limit"]) else ("SOFT_LIMIT_EXCEEDED" if pending>=int(rule["pending_soft_limit"]) else "WITHIN_LIMIT"),"archived_count":len(archive),"moved_to_archive":moved,"updated":now,"authority_effect":"NONE"}; state["reviewer_quality_debt"]=debt; return debt
def quality_debt_blocks_new_convergence(state,policy,*,now=None): return maintain_quality_queue(state,policy,now=now)["status"]=="BLOCK_NEW_CONVERGENCE"
def queue_pending_assessments(state,registry,*,now=None,limit=20,policy=None):
 if limit<1 or limit>100: raise ValueError("quality queue scan limit must be in [1,100]")
 now=time.time() if now is None else float(now); policy=policy or load_policy(); maintain_quality_queue(state,policy,now=now); queue=state.setdefault("reviewer_quality_queue",[]); hashes={r.get("response_sha256") for r in queue if isinstance(r,dict)}; added=0
 for attempt in state.get("attempts",[]):
  if added>=limit: break
  if attempt.get("status")!="REVIEW_RECORDED" or attempt.get("protocol")!=WORKER_PROTOCOL: continue
  response=attempt.get("response_text")
  if not isinstance(response,str) or not response: raise ValueError("current-protocol recorded review is missing response text")
  h=protocol.sha256_text(response)
  if h in hashes:
   attempt["reviewer_quality_status"]=next((r.get("status") for r in queue if r.get("response_sha256")==h),QUALITY_STATUS); attempt["response_sha256"]=h; continue
  req=_request_for(state,attempt,registry,now)
  if req["peer_content_seen"] is not False: raise ValueError("quality request detected peer-content exposure")
  queue.append(req); hashes.add(h); attempt["reviewer_quality_status"]=QUALITY_STATUS; attempt["reviewer_quality_request_id"]=req["request_id"]; attempt["response_sha256"]=h; rec=_record_for_attempt(state,attempt); rec["reviewer_quality_status"]=QUALITY_STATUS; rec["reviewer_quality_request_id"]=req["request_id"]; rec["response_sha256"]=h; added+=1
 maintain_quality_queue(state,policy,now=now); return added
def load_registry(root:Path=Path(".")): return json.loads((root/"agents/reviewer-slot-registry.json").read_text())
