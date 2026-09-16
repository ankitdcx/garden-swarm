"""Secret-free preflight for the active independent-branch OpenRouter worker."""
from __future__ import annotations
import json,os,time
from pathlib import Path
from tools import independent_branch_protocol as protocol
from tools import reviewer_quality_runtime
from tools import select_paid_matrix_reviewers as reviewer_selector
from tools import single_review_worker as legacy
from tools.provider_exclusion import load_policy as load_exclusion_policy

def _inactive_slots(registry): return [{k:r.get(k) for k in ("slot_id","family","model","state")} for r in registry.get("slots",[]) if r.get("state")!="ACTIVE"]
def preflight():
 legacy.host_check(); token=os.environ.get("GH_REVIEW_TOKEN")
 if not token: raise ValueError("state access token missing")
 ledger=legacy.GitLedger(token); state=ledger.value
 if state.get("paused") is not False or state.get("scope")!="PUBLIC_MATRIX_REVIEW_ONLY": raise ValueError("review state paused or outside public scope")
 policy=json.loads(Path("agents/independent-branch-convergence-policy.json").read_text()); protocol.load_policy(policy); model_policy=json.loads(Path("agents/openrouter-paid-review-policy.json").read_text()); quality_policy=reviewer_quality_runtime.load_policy(); registry=json.loads(Path("agents/reviewer-slot-registry.json").read_text()); exclusion_policy=load_exclusion_policy(Path("agents/provider-exclusion-policy.json"))
 inactive=_inactive_slots(registry)
 if inactive:
  state["continuation"]={"status":"REVIEWER_SLOT_INVALIDATED","reason":"REQUIRED_REVIEWER_SLOT_NOT_ACTIVE","inactive_slots":inactive,"silent_model_swap_allowed":False,"replacement_requires_new_convergence_cycle":True,"updated":time.time()}; ledger.save(state); raise ValueError("required reviewer slot is non-ACTIVE; current/new convergence paused")
 debt=reviewer_quality_runtime.maintain_quality_queue(state,quality_policy)
 if debt["status"]=="BLOCK_NEW_CONVERGENCE":
  state["continuation"]={"status":"QUALITY_DEBT_BLOCKED","reason":"REVIEWER_QUALITY_PENDING_HARD_LIMIT","quality_debt":debt,"updated":time.time()}; ledger.save(state); raise ValueError("reviewer quality debt hard limit blocks new convergence admission")
 selected=reviewer_selector.active_reviewers(model_policy,registry,exclusion_policy); families=[r["family"] for r in selected]
 if len(families)!=4 or len(set(families))!=4: raise ValueError("active board must contain exactly four distinct families")
 if int(model_policy["execution_limits"]["max_model_calls_per_dispatch"])!=1: raise ValueError("one OpenRouter call per dispatch is required")
 if int(model_policy["execution_limits"]["max_concurrent_model_calls"])!=1: raise ValueError("OpenRouter calls must remain sequential")
 if debt["status"]=="SOFT_LIMIT_EXCEEDED": print("Reviewer quality debt soft limit exceeded; current call allowed but adjudication is due")
 print("Independent-branch preflight passed; active reviewer slots, bounded quality debt, ChatGPT directive and live budget checks remain required")
if __name__=="__main__":
 try: preflight()
 except Exception as exc:
  print("INDEPENDENT_BRANCH_PREFLIGHT_BLOCKED: "+type(exc).__name__); raise SystemExit(2)
