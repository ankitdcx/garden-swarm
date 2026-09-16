"""Secret-free continuation for the independent-branch OpenRouter worker."""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
from tools import independent_branch_protocol as protocol
from tools import reviewer_quality_runtime
from tools import single_review_worker as legacy
WORKER="single-openrouter-review.yml"; DISPATCHER="continue-openrouter-review.yml"
def _digest_files(root,paths): return protocol.sha256_value([[rel,hashlib.sha256((root/rel).read_bytes()).hexdigest() if (root/rel).is_file() else "MISSING"] for rel in paths])
def host_check():
 if os.environ.get("GITHUB_REPOSITORY")!=legacy.REPO or os.environ.get("GITHUB_REF")!="refs/heads/main": raise ValueError("untrusted continuation host")
 ref=os.environ.get("GITHUB_WORKFLOW_REF"); event=os.environ.get("GITHUB_EVENT_NAME"); worker_ref=legacy.REPO+"/.github/workflows/"+WORKER+"@refs/heads/main"; dispatcher_ref=legacy.REPO+"/.github/workflows/"+DISPATCHER+"@refs/heads/main"
 if ref==worker_ref and event=="workflow_dispatch": return "completion"
 if ref==dispatcher_ref and event in ("push","schedule","workflow_dispatch"): return event
 raise ValueError("unregistered continuation host")
def _quality_hash(state): return protocol.sha256_value({"queue":state.get("reviewer_quality_queue",[]),"archive":state.get("reviewer_quality_archive",[]),"debt":state.get("reviewer_quality_debt")})
def _save_if_quality_changed(ledger,state,changed):
 if changed: ledger.save(state)
def dispatch(root=Path(".")):
 event=host_check(); token=os.environ["GH_REVIEW_TOKEN"]; ledger=legacy.GitLedger(token); state=ledger.value
 if state.get("paused") is not False or state.get("scope")!="PUBLIC_MATRIX_REVIEW_ONLY": print("PAUSED; no model call or dispatch"); return
 registry=reviewer_quality_runtime.load_registry(root); quality_policy=reviewer_quality_runtime.load_policy(root); before=_quality_hash(state); added=reviewer_quality_runtime.queue_pending_assessments(state,registry,limit=20,policy=quality_policy); changed=_quality_hash(state)!=before; debt=state.get("reviewer_quality_debt") or {}
 if debt.get("status")=="BLOCK_NEW_CONVERGENCE": state["continuation"]={"status":"QUALITY_DEBT_BLOCKED","reason":"REVIEWER_QUALITY_PENDING_HARD_LIMIT","quality_debt":debt,"updated":time.time()}; ledger.save(state); print("Reviewer quality debt hard limit reached; no continuation dispatch"); return
 executor_revision=_digest_files(root,["tools/context_capsule.py","tools/independent_branch_worker.py","tools/single_review_worker.py","tools/review_context.py","tools/review_budget.py","tools/reviewer_quality_runtime.py","agents/review-context-policy.json","SOURCE_MANIFEST.json","tools/independent_branch_protocol.py","tools/independent_branch_continuation.py","agents/garden-architecture-context-capsule-policy.json","agents/independent-branch-convergence-policy.json","agents/event-driven-context-policy.json","agents/openrouter-paid-review-policy.json","agents/reviewer-quality-policy.json","agents/reviewer-slot-registry.json","agents/provider-exclusion-policy.json","agents/design-review-matrix.json"]); current_commit=os.environ.get("GITHUB_SHA"); continuation=state.get("continuation") or {}
 outstanding=[r for r in state.get("attempts",[]) if r.get("status") in ("RESERVED","UNKNOWN")]
 if outstanding: state["continuation"]={"status":"BLOCKED_UNRESOLVED_CALL","reason":"GENERATION_OR_BILLING_EVIDENCE_REQUIRED","attempts":[{k:a.get(k) for k in ("run_id","model","status","response_id","started")} for a in outstanding],"updated":time.time()}; ledger.save(state); print("Outstanding call requires reconciliation; no continuation dispatch"); return
 if state.get("admitted_source_commit")!=current_commit or state.get("executor_revision_v3")!=executor_revision: state["admitted_source_commit"]=current_commit; state["executor_revision_v3"]=executor_revision; state["continuation"]={"status":"AWAITING_CHATGPT_BASELINE_OR_DIRECTIVE","reason":"NEW_SOURCE_OR_PROTOCOL_BINDING","updated":time.time()}; ledger.save(state); print("New material binding requires private ChatGPT baseline and source-bound Garden context capsule before OpenRouter inference"); return
 status=continuation.get("status")
 if status=="DEFERRED_DAILY" and time.time()<float(continuation.get("resume_after",0)): _save_if_quality_changed(ledger,state,changed); return
 if status=="DISPATCHED" and (event!="schedule" or time.time()-float(continuation.get("updated",0))<3600): _save_if_quality_changed(ledger,state,changed); return
 if status not in ("READY","DEFERRED_DAILY","DISPATCHED"): _save_if_quality_changed(ledger,state,changed); print("Queue state: "+str(status)+"; no automatic dispatch"); return
 attempts=int(continuation.get("dispatch_attempts",0))
 if attempts>=2: state["continuation"]={"status":"BLOCKED","reason":"DISPATCH_DELIVERY_UNCONFIRMED","updated":time.time()}; ledger.save(state); return
 state["continuation"]={**continuation,"status":"DISPATCHED","dispatch_attempts":attempts+1,"updated":time.time()}; ledger.save(state); legacy.http(legacy.API+"/actions/workflows/"+WORKER+"/dispatches",token,{"ref":"main"})
 if added: print("Queued "+str(added)+" reviewer response(s) for ChatGPT quality adjudication")
 print("Next isolated reviewer dispatched")
if __name__=="__main__":
 try: dispatch()
 except Exception as exc: print("INDEPENDENT_BRANCH_CONTINUATION_STOPPED: "+type(exc).__name__+"; no inference was made by dispatcher"); raise SystemExit(2)
