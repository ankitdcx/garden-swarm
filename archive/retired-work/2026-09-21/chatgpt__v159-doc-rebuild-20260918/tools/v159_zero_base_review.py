#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, os, subprocess, time
from pathlib import Path
from urllib import request

OPENROUTER="https://openrouter.ai/api/v1/chat/completions"
KEY_INFO="https://openrouter.ai/api/v1/key"
PACKET=Path("review-inputs/v159-zero-review/ZERO_BASE_CANDIDATE_PACKET.txt")
OUT=Path("review-results/v159-zero-review/initial")
DAILY=10.0
PER_CALL=0.10
MODELS={
 "deepseek":"deepseek/deepseek-v4.1-flash",
 "glm":"z-ai/glm-5.3-flash",
 "xiaomi":"xiaomi/mimo-v2.5",
 "gemini":"google/gemini-3.8-flash",
}
def sha(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
def budget(key):
 req=request.Request(KEY_INFO,headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
 with request.urlopen(req,timeout=30) as r: data=json.loads(r.read().decode("utf-8"))
 p=data.get("data") if isinstance(data,dict) and isinstance(data.get("data"),dict) else data
 u=float(p.get("usage_daily"))
 if not math.isfinite(u) or u<0: raise RuntimeError("daily usage unverifiable")
 if u+PER_CALL>DAILY: raise RuntimeError("daily budget reservation exhausted")
 return {"usage_daily":u,"limit":p.get("limit"),"limit_remaining":p.get("limit_remaining")}
def call(model,prompt,key):
 max_tokens=12000 if model.startswith("z-ai/glm-") else 9000
 body={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0.05,"max_tokens":max_tokens,"stream":False,
       "provider":{"allow_fallbacks":True,"data_collection":"deny","sort":"price","ignore":["anthropic","mistral","nvidia"],"max_price":{"prompt":1.0,"completion":4.0}}}
 if model.startswith("deepseek/") or model.startswith("xiaomi/"): body["reasoning"]={"effort":"none"}
 elif model.startswith("z-ai/glm-"): body["reasoning"]={"effort":"low"}
 cmd=["curl","-sS","--connect-timeout","10","--max-time","360",OPENROUTER,"-X","POST",
      "-H","Authorization: Bearer "+key,"-H","Content-Type: application/json",
      "-H","HTTP-Referer: https://github.com/ankitdcx/garden-swarm",
      "-H","X-Title: Garden v15.9 Zero-Base Fresh Review",
      "--data-binary","@-","-w","\\n%{http_code}"]
 p=subprocess.run(cmd,input=json.dumps(body,separators=(",",":")),text=True,capture_output=True,timeout=375)
 raw=p.stdout
 if "\n" not in raw: return 0,{},f"NO_STATUS rc={p.returncode} {p.stderr[-500:]}"
 payload,status=raw.rsplit("\n",1)
 try: status=int(status.strip())
 except: status=0
 try:data=json.loads(payload)
 except:data={"raw_payload":payload}
 if p.returncode!=0:return status,data,f"CURL_{p.returncode}"
 if not 200<=status<300:return status,data,f"HTTP_{status}: "+json.dumps(data,ensure_ascii=False)[:1200]
 return status,data,None
def parse(data):
 choices=(data or {}).get("choices") or []
 if not choices:return None,""
 text=((choices[0].get("message") or {}).get("content") or "").strip()
 s=text
 if s.startswith("~~~"): pass
 if s.startswith("```"):
  s=s.split("\n",1)[1] if "\n" in s else s
  if s.endswith("```"):s=s[:-3]
  s=s.strip()
  if s.lower().startswith("json\n"):s=s[5:]
 cand=[s]
 if "{" in s and "}" in s:cand.append(s[s.find("{"):s.rfind("}")+1])
 for c in cand:
  try:
   o=json.loads(c)
   if isinstance(o,dict):return o,text
  except:pass
 return None,text
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--family",required=True,choices=MODELS);args=ap.parse_args()
 key=os.environ.get("OPENROUTER_API_KEY")
 if not key:raise SystemExit("OPENROUTER_API_KEY missing")
 model=MODELS[args.family];receipt=budget(key);packet=PACKET.read_text()
 prompt=f"""BLIND INDEPENDENT ZERO-BASE DESIGN CHALLENGE — GARDEN v15.9.
Reviewer family: {args.family}
Packet SHA-256: {sha(packet)}

You are reviewing ONLY the current-v15.9-derived packet below. You have not seen other reviewers.
Do not use prior Garden history or infer prior intent.
Challenge every candidate against DO_NOTHING and existing-owner precedence.
Return one JSON object only:
{{
 "verdict":"ACCEPT_SET|ACCEPT_WITH_PATCHES|REJECT_SET|EXPAND_REQUIRED",
 "candidate_dispositions":{{
   "ZR-001":{{"decision":"KEEP_AS_PROPOSED|PATCH|ALIAS_EXISTING|REJECT|NEEDS_CONTEXT","reason":"...","minimal_patch":"...","owner":"...","test":"..."}}
 }},
 "material_findings":[{{"id":"F1","severity":"CRITICAL|HIGH|MEDIUM|LOW","candidate_refs":["ZR-001"],"claim":"...","minimal_patch":"...","test":"...","confidence":"HIGH|MEDIUM|LOW"}}],
 "missing_current_source_context":[],
 "must_retain":[],
 "must_remove_or_merge":[],
 "overall_uncertainty":"..."
}}
Disposition map MUST cover ZR-001 through ZR-012.
At most 12 material findings. Do not invent defects.

--- BEGIN CURRENT-SOURCE-DERIVED PACKET ---
{packet}
--- END PACKET ---
"""
 start=time.time();status,data,err=call(model,prompt,key);structured,raw=parse(data)
 usage=(data or {}).get("usage") if isinstance(data,dict) else None
 cost=(usage or {}).get("cost") if isinstance(usage,dict) else None
 usable=isinstance(structured,dict) and isinstance(structured.get("candidate_dispositions"),dict) and all(f"ZR-{i:03d}" in structured["candidate_dispositions"] for i in range(1,13))
 if isinstance(cost,(int,float)) and float(cost)>PER_CALL:usable=False;err="MODEL_COST_CEILING_EXCEEDED"
 result={"schema":"GardenV159ZeroBaseBlindReview/v1","family":args.family,"model":model,"packet_sha256":sha(packet),
         "http_status":status,"error":err,"elapsed_seconds":round(time.time()-start,2),"usable":usable,
         "review":structured,"raw_review":None if structured is not None else raw,
         "actual_model":(data or {}).get("model") if isinstance(data,dict) else None,
         "provider":(data or {}).get("provider") if isinstance(data,dict) else None,"usage":usage,"budget_receipt":receipt,
         "canonical_effect":False,"semantic_delta_admitted":False}
 OUT.mkdir(parents=True,exist_ok=True);(OUT/f"{args.family}.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
 print(json.dumps({"family":args.family,"usable":usable,"error":err,"cost":cost}))
 if not usable:raise SystemExit(2)
if __name__=="__main__":main()
