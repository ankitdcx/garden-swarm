#!/usr/bin/env python3
"""Cognitive Arena v1: multi-model challenge, solve, critique, judge and shared discovery."""
import hashlib,json,os,re,time
from pathlib import Path
from urllib import request,error
OR="https://openrouter.ai/api/v1"; CAP=.05; DAILY=3.65
MODELS=[{"family":"deepseek","model":"deepseek/deepseek-v4-pro-0813"},{"family":"nvidia","model":"nvidia/nemotron-3-ultra-550b-a55b"},{"family":"pareto","model":"unbiased/pareto"},{"family":"mistral","model":"mistralai/mistral-medium-3-5"},{"family":"grok","model":"x-ai/grok-4.6"}]
OUT=Path("cognitive-arena-result.json")
def http(url,key,body=None,timeout=180):
 h={"Authorization":"Bearer "+key,"Content-Type":"application/json","User-Agent":"garden-cognitive-arena"}
 req=request.Request(url,headers=h,data=None if body is None else json.dumps(body).encode(),method="GET" if body is None else "POST")
 with request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
def parse(s):
 m=re.search(r"\{.*\}",s or "",re.S)
 if not m:return None
 try:return json.loads(m.group())
 except:return None
def call(m,p,key,tok=1600):
 try:eps=http(OR+"/models/"+m+"/endpoints",key)["data"]["endpoints"]
 except Exception as e:return {"status":"ENDPOINT_ERROR","text":"","cost":0}
 elig=[]
 for ep in eps:
  try: pp=float(ep["pricing"]["prompt"]);cp=float(ep["pricing"]["completion"])
  except:continue
  est=(len(p)/4*pp+tok*cp)*1.4
  if est<=CAP:elig.append((est,ep))
 if not elig:return {"status":"BLOCKED","text":"","cost":0}
 _,ep=min(elig,key=lambda x:x[0]);prov=ep.get("provider_name") or ep.get("name") or ""
 body={"model":m,"messages":[{"role":"user","content":p}],"temperature":0,"max_tokens":tok,"provider":{"allow_fallbacks":False,"data_collection":"deny","only":[prov] if prov else []}}
 t=time.time()
 try:
  d=http(OR+"/chat/completions",key,body);txt=((d.get("choices")or[{}])[0].get("message")or{}).get("content")or"";u=d.get("usage")or{}
  return {"status":"OK" if txt.strip() else "NULL","text":txt,"cost":u.get("cost") or 0,"provider":prov,"latency":round(time.time()-t,2)}
 except error.HTTPError as e:return {"status":"HTTP_"+str(e.code),"text":"","cost":0,"provider":prov}
 except Exception as e:return {"status":"ERROR","text":"","cost":0,"provider":prov}
def main():
 key=os.environ["OPENROUTER_API_KEY"]; start=float(http(OR+"/key",key)["data"].get("usage_daily") or 0); usable=[]; rec=[]
 # Phase 1: one 3-question challenge per model (keeps full matrix affordable)
 for m in MODELS:
  
  p='Create exactly 3 hard novel self-contained reasoning problems that distinguish frontier AI reasoning. No trivia/web/tokenizer tricks. Freeze objective keys. JSON only {"questions":[{"id":"Q1","question":"...","answer":"...","category":"...","why_hard":"..."}]}.'
  z=call(m["model"],p,key);d=parse(z["text"]); qs=(d or {}).get("questions",[])
  row={"family":m["family"],"model":m["model"],"author_status":z["status"],"questions":qs if len(qs)==3 else [],"cost":z["cost"],"provider":z.get("provider")}
  rec.append(row)
  if len(row["questions"])==3:usable.append(row)
 # Phase 2: each usable model solves a balanced 12-question panel: 1 deterministic shared + up to 11 peer-authored
 shared={"id":"S","question":"A machine maps integer pair (x,y) by one unknown rule chosen from: R1=(x+y,y), R2=(x-y,y), R3=(x,x+y), R4=(x,y-x), R5=(y,x), R6=(-x,y). It maps (2,1)->(3,1) and (-1,4)->(3,4). Which rule?","answer":"R1","category":"rule_induction"}
 panel=[shared]
 for a in usable:
  if a["questions"]:panel.append({**a["questions"][0],"id":"P_"+a["family"]})
 panel=panel[:12]
 solves={}
 for m in usable:
  if float(http(OR+"/key",key)["data"].get("usage_daily") or 0)+CAP>DAILY:break
  p='Solve independently. Do not trust question author keys. JSON only {"answers":[{"id":"...","answer":"...","confidence":0.0,"key_challenge":null}]}.\n'+json.dumps([{"id":x["id"],"question":x["question"]} for x in panel])
  z=call(m["model"],p,key,2200);solves[m["family"]]={"status":z["status"],"parsed":parse(z["text"]),"cost":z["cost"],"provider":z.get("provider")}
 # Phase 3: shared discovery problem, independent proposals
 research={}
 problem="Invent and analyze a deterministic rule for aggregating conflicting claims from five imperfect reasoners when their errors may be correlated. The rule must not reduce truth to majority vote. Give one concrete failure case of your own rule and a minimal repair. This is a novel design problem; originality, falsifiability and self-critique matter."
 for m in usable:
  if float(http(OR+"/key",key)["data"].get("usage_daily") or 0)+CAP>DAILY:break
  z=call(m["model"],'Shared research problem: '+problem+' Return compact JSON {"proposal":"...","new_insight":"...","failure":"...","repair":"..."}.',key,1800);research[m["family"]]={"status":z["status"],"parsed":parse(z["text"]),"cost":z["cost"]}
 # Phase 4: each usable judge ranks anonymized research contributions + solver answers, attacks ranking
 packet={"panel":panel,"solves":solves,"research":research}
 judges={}
 for m in usable:
  if float(http(OR+"/key",key)["data"].get("usage_daily") or 0)+CAP>DAILY:break
  p='Act as blind meta-reviewer. Evaluate correctness, novelty, error detection, calibration and research contribution. Challenge bad frozen keys. Return JSON only {"ranking":[{"family":"...","score":0,"reason":"..."}],"key_defects":[],"ranking_attack":"strongest reason this ranking could be wrong","repair":"..."}. DATA='+json.dumps(packet)
  z=call(m["model"],p,key,2400);judges[m["family"]]={"status":z["status"],"parsed":parse(z["text"]),"cost":z["cost"]}
 end=float(http(OR+"/key",key)["data"].get("usage_daily") or 0)
 out={"schema":"CognitiveArena/v1","authors":rec,"panel":panel,"solves":solves,"research":research,"judges":judges,"usage_start":start,"usage_end":end,"authority_effect":"NONE"}
 OUT.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"usable":[x["family"] for x in usable],"usage_start":start,"usage_end":end,"solve_count":len(solves),"research_count":len(research),"judge_count":len(judges)},indent=2))
if __name__=="__main__":main()
