#!/usr/bin/env python3
"""One-off governed all-family protocol-review sweep for Model Capability Lab."""
import hashlib,json,os,time
from pathlib import Path
from urllib import request,error
MODELS=json.loads(Path("agents/model-capability-lab.json").read_text())["models"]
SOURCE=Path("docs/MODEL_CAPABILITY_LAB.md").read_text()
OR="https://openrouter.ai/api/v1"
CAP=0.05
PROMPT="""Independently adversarially review the supplied Model Capability Comparison Process. Do NOT generate benchmark questions and do NOT rank models. Return compact JSON only with keys: verdict (KEEP|PATCH), defects (array of at most 6 objects with severity, defect, failure_scenario, smallest_patch), and residual_unknowns (array). Focus on concrete gaming, statistical, blindness, contamination, cross-model fairness, verification, scaling, and operational defects.\n\nPROTOCOL:\n"""+SOURCE

def get(url,key):
 req=request.Request(url,headers={"Authorization":"Bearer "+key,"User-Agent":"garden-all-model-protocol-sweep"})
 with request.urlopen(req,timeout=60) as r:return json.loads(r.read().decode())
def post(body,key):
 req=request.Request(OR+"/chat/completions",data=json.dumps(body).encode(),method="POST",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json","HTTP-Referer":"https://github.com/ankitdcx/garden-swarm","X-Title":"Garden all-model protocol sweep"})
 with request.urlopen(req,timeout=240) as r:return json.loads(r.read().decode())
def money(x):
 try:return float(x)
 except:return 1e9
def main():
 key=os.environ["OPENROUTER_API_KEY"]; info=get(OR+"/key",key)["data"]; before=money(info.get("usage_daily"))
 if before+0.65>2.0: raise SystemExit("daily budget cannot reserve 13 x $0.05")
 out=[]
 for row in MODELS:
  model=row["model"]; fam=row["family"]; rec={"family":fam,"model":model,"status":"UNATTEMPTED"}
  try:
   ident=get(OR+"/models/"+model+"/endpoints",key)["data"]["endpoints"]
   eligible=[]
   for ep in ident:
    if ep.get("data_collection") not in (None,"deny","no"): continue
    pp=money(ep.get("pricing",{}).get("prompt"))*1_000_000
    cp=money(ep.get("pricing",{}).get("completion"))*1_000_000
    est=(len(PROMPT)/4*pp/1e6)+(1400*cp/1e6)
    if est<=CAP: eligible.append((est,ep))
   if not eligible:
    rec.update(status="PRICE_OR_ENDPOINT_BLOCKED",endpoint_count=len(ident)); out.append(rec); continue
   est,ep=min(eligible,key=lambda x:x[0]); provider=(ep.get("provider_name") or ep.get("name") or "")
   body={"model":model,"messages":[{"role":"user","content":PROMPT}],"temperature":0,"max_tokens":1400,"provider":{"sort":"price","allow_fallbacks":False,"data_collection":"deny","only":[provider] if provider else []}}
   t=time.time(); data=post(body,key); msg=(data.get("choices") or [{}])[0].get("message") or {}; content=msg.get("content") or ""
   usage=data.get("usage") or {}; cost=usage.get("cost")
   rec.update(status="USABLE" if content.strip() else "NULL_TEXT",provider=provider,response_id=data.get("id"),cost_usd=cost,latency_seconds=round(time.time()-t,2),content=content,content_sha256=hashlib.sha256(content.encode()).hexdigest())
  except error.HTTPError as e:
   rec.update(status="HTTP_"+str(e.code),error=e.read().decode(errors="replace")[:500])
  except Exception as e: rec.update(status="ERROR",error=type(e).__name__+":"+str(e))
  out.append(rec)
 after=money(get(OR+"/key",key)["data"].get("usage_daily"))
 result={"schema":"GardenAllModelProtocolSweep/v1","source_sha256":hashlib.sha256(SOURCE.encode()).hexdigest(),"prompt_sha256":hashlib.sha256(PROMPT.encode()).hexdigest(),"started_usage_daily_usd":before,"ended_usage_daily_usd":after,"results":out,"semantic_delta_admitted":False,"authority_effect":"NONE_EVIDENCE_ONLY"}
 Path("all-model-protocol-sweep.json").write_text(json.dumps(result,indent=2)+"\n"); print(json.dumps({**result,"results":[{k:v for k,v in x.items() if k!="content"} for x in out]},indent=2))
if __name__=="__main__":main()
