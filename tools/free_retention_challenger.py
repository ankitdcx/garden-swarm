"""Blind free-model retention challenger sweep for GROUP_REVIEW packets."""
from __future__ import annotations
import json, os, time
from tools import free_model_rotation as free
from tools import group_review_bus as bus
from tools import group_review_openrouter_worker as group
from tools import single_review_worker as legacy

MAX_REVIEWERS=8  # bounded diverse zero-cost challenger families

def main():
    key=os.environ["OPENROUTER_API_KEY"]; gh=os.environ["GH_REVIEW_TOKEN"]
    issue_number=int(os.environ["GARDEN_TRIGGER_ISSUE"])
    _,packet=group.fetch_run_issue(gh,issue_number)
    result_title="[FREE_RETENTION_RESULT] "+packet["problem_id"]
    existing=legacy.http(legacy.API+"/issues?state=all&per_page=100",gh)
    if any(row.get("title")==result_title for row in existing):
        print("FREE_RETENTION_SWEEP_ALREADY_RECORDED"); return
    source=group.materialize_frozen_sources(packet,gh,max_characters=160000)
    models=free.catalog(key)
    selected=[]
    for count in range(min(MAX_REVIEWERS,len(free.FAMILIES)),0,-1):
        try:
            selected=free.choose(models,free.event_slot(packet["packet_sha256"]),count=count); break
        except SystemExit: pass
    if not selected: raise SystemExit("no allowed free reviewer families available")
    records=[]
    for row in selected:
        prompt=bus.openrouter_prompt(packet,family=row["family"],role=row["role"],model=row["model"])+            "\nExact frozen public source bundle follows. Review independently; peer answers are hidden.\n"+source
        body={"model":row["model"],"messages":[{"role":"user","content":prompt}],"max_tokens":1800,
              "temperature":0.1,"stream":False,
              "provider":{"allow_fallbacks":True,"data_collection":"deny"}}
        rec={"family":row["family"],"model":row["model"],"role":row["role"],"peer_content_seen":False}
        try:
            response=legacy.http(legacy.OR+"/chat/completions",key,body,timeout=180)
            usage=response.get("usage") or {}; cost=legacy.money(usage.get("cost"))
            content=((response.get("choices") or [{}])[0].get("message") or {}).get("content")
            rec.update({"actual_model":response.get("model"),"provider":response.get("provider"),
                        "response_id":response.get("id"),"cost_usd":str(cost),
                        "finish_reason":((response.get("choices") or [{}])[0]).get("finish_reason")})
            if cost != 0: raise ValueError("free challenger reported nonzero cost")
            if not isinstance(content,str) or not content.strip(): raise ValueError("no textual challenger content")
            rec["status"]="REVIEW_RECORDED"; rec["review"]=content[:12000]; rec["review_sha256"]=bus.sha256_text(content)
        except Exception as exc:
            rec.update({"status":"FAILED","error_type":type(exc).__name__,"error":str(exc)[:300]})
        records.append(rec)
    payload={"schema":"GardenFreeRetentionChallengerSweep/v1","problem_id":packet["problem_id"],
             "run_issue_number":issue_number,"packet_sha256":packet["packet_sha256"],
             "selected_family_count":len(selected),"recorded_review_count":sum(r["status"]=="REVIEW_RECORDED" for r in records),
             "records":records,"semantic_delta_admitted":False,"authority_effect":"NONE_CHALLENGER_EVIDENCE_ONLY"}
    payload["bundle_sha256"]=bus.sha256_value(payload)
    body="<!-- GARDEN_FREE_RETENTION_CHALLENGER -->\n\n```json\n"+json.dumps(payload,indent=2,ensure_ascii=False)+"\n```"
    legacy.http(legacy.API+"/issues",gh,{"title":result_title,"body":body})
    print(json.dumps({"selected":len(selected),"recorded":payload["recorded_review_count"],"bundle_sha256":payload["bundle_sha256"]}))
if __name__=="__main__": main()
