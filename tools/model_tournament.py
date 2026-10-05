#!/usr/bin/env python3
"""Garden Model Tournament v1 — resumable OpenRouter reciprocal reasoning tournament."""
from __future__ import annotations
import argparse,hashlib,json,os,random,re,time
from pathlib import Path
from urllib import request,error
from fractions import Fraction

OR="https://openrouter.ai/api/v1"; CFG=Path("agents/model-capability-lab.json")
STATE=Path("model-tournament-state.json"); CALL_CAP=0.05; DAILY=2.0
def H(x):return hashlib.sha256(x.encode()).hexdigest()
def http(url,key,body=None,timeout=240):
 h={"Authorization":"Bearer "+key,"User-Agent":"garden-model-tournament","Content-Type":"application/json","HTTP-Referer":"https://github.com/ankitdcx/garden-swarm","X-Title":"Garden Model Tournament"}
 req=request.Request(url,headers=h,data=None if body is None else json.dumps(body).encode(),method="GET" if body is None else "POST")
 with request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode())
def parse_json(s):
 m=re.search(r"\{.*\}",s or "",re.S)
 if not m:return None
 try:return json.loads(m.group(0))
 except:return None
def common(seed):
 r=random.Random(int(H(seed)[:16],16)); q=[]
 for i in range(10):
  a,b,c=[r.randint(2,15) for _ in range(3)]
  typ=i%5
  if typ==0:q.append({"id":f"C{i+1}","category":"arithmetic_state","q":f"Start x={a}, y={b}. Set x=x+y; then y=2*x-y using new x; then x=x-y. Return x+y.","a":str((a+b-(2*(a+b)-b))+(2*(a+b)-b))})
  elif typ==1:
   p=r.choice([7,11,13]);n=a%p
   for _ in range(c):n=(3*n+2)%p
   q.append({"id":f"C{i+1}","category":"recurrence","q":f"Start n={a%p}. Repeat n=(3n+2) mod {p} exactly {c} times. Final n?","a":str(n)})
  elif typ==2:
   ds=[r.randint(2,6) for _ in range(4)];ans=max(ds[1],ds[0]+ds[2])+ds[3]
   q.append({"id":f"C{i+1}","category":"planning","q":f"Durations A={ds[0]},B={ds[1]},C={ds[2]},D={ds[3]}. A,B start at 0; C after A; D after B and C; unlimited workers. Earliest finish?","a":str(ans)})
  elif typ==3:
   prev=Fraction(1,r.choice([4,5,10]));sens=Fraction(r.choice([3,4,5]),r.choice([4,5,6])); sens=min(sens,Fraction(5,6)); fp=Fraction(1,r.choice([6,8,10]));post=(sens*prev)/(sens*prev+fp*(1-prev))
   q.append({"id":f"C{i+1}","category":"bayes","q":f"Prevalence={prev}, sensitivity={sens}, false-positive rate={fp}. Given positive, posterior? Reduced fraction.","a":f"{post.numerator}/{post.denominator}"})
  else:
   n=r.randint(30,100); z=n;out=""
   while z:out=str(z%3)+out;z//=3
   q.append({"id":f"C{i+1}","category":"representation","q":f"Write decimal {n} in base 3, digits only.","a":out or "0"})
 return q
def prompt_author():
 return """Create exactly 10 novel self-contained reasoning questions for other frontier AI models. No web/trivia/tokenizer tricks. Prefer objectively verifiable math, logic, causal, planning, probabilistic, algorithmic or scientific reasoning. Freeze the answer before seeing peers. JSON only: {"questions":[{"id":"Q1","category":"...","question":"...","answer":"...","scoring":"exact semantic answer rule","assumptions":"...","ambiguity":"none or explanation","difficulty":"..."},...]}. Each must have one defensible answer."""
def prompt_solve(items):
 return "Solve independently without tools/web. JSON only {\"answers\":[{\"id\":\"...\",\"answer\":\"...\",\"confidence\":0.0}]}\n"+json.dumps([{"id":x["id"],"question":x["question"] if "question" in x else x["q"]} for x in items])
def prompt_judge(item,answers):
 return "Judge anonymized answers against frozen key. A valid counterexample beats consensus. JSON only {\"judgments\":[{\"label\":\"A\",\"correct\":true/false,\"reason\":\"short\"}],\"key_valid\":true/false,\"disputed\":true/false}.\nITEM="+json.dumps(item)+"\nANSWERS="+json.dumps(answers)
def call(model,prompt,key,max_tokens=2200):
 eps=http(OR+"/models/"+model+"/endpoints",key)["data"]["endpoints"]; elig=[]
 for ep in eps:
  pp=float(ep.get("pricing",{}).get("prompt") or 99);cp=float(ep.get("pricing",{}).get("completion") or 99)
  est=(len(prompt)/4*pp)+(max_tokens*cp)
  if est<=CALL_CAP:elig.append((est,ep))
 if not elig:return {"status":"BLOCKED","content":"","cost":0}
 _,ep=min(elig,key=lambda x:x[0]); provider=ep.get("provider_name") or ep.get("name") or ""
 body={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":max_tokens,"provider":{"allow_fallbacks":False,"data_collection":"deny","only":[provider] if provider else []}}
 t=time.time()
 try:
  d=http(OR+"/chat/completions",key,body); content=((d.get("choices") or [{}])[0].get("message") or {}).get("content") or "";u=d.get("usage") or {}
  return {"status":"OK" if content.strip() else "NULL","content":content,"cost":u.get("cost"),"provider":provider,"response_id":d.get("id"),"latency":round(time.time()-t,2)}
 except error.HTTPError as e:return {"status":"HTTP_"+str(e.code),"content":"","cost":0,"provider":provider}
 except Exception as e:return {"status":"ERROR","content":"","cost":0,"error":str(e)}
def load():
 return json.loads(STATE.read_text()) if STATE.exists() else {"schema":"GardenModelTournamentState/v1","seed":"2026-10-05-tournament-v1","authors":{},"solves":{},"judges":{},"attempts":[]}
def save(s):STATE.write_text(json.dumps(s,indent=2)+"\n")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--phase",choices=["author","solve-common","solve-reciprocal","judge","report"],required=True);ap.add_argument("--max-calls",type=int,default=12);args=ap.parse_args()
 key=os.environ["OPENROUTER_API_KEY"];cfg=json.loads(CFG.read_text());models=cfg["models"];s=load();calls=0
 def do(fam,model,p,tag,tok=2200):
  nonlocal calls
  if calls>=args.max_calls:return None
  usage=float(http(OR+"/key",key)["data"].get("usage_daily") or 0)
  if usage+CALL_CAP>DAILY:return None
  r=call(model,p,key,tok);r.update(family=fam,model=model,tag=tag);s["attempts"].append({k:v for k,v in r.items() if k!="content"});calls+=1;save(s);return r
 if args.phase=="author":
  for m in models:
   if m["family"] in s["authors"]:continue
   r=do(m["family"],m["model"],prompt_author(),"author")
   if r:s["authors"][m["family"]]={"model":m["model"],"raw":r["content"],"parsed":parse_json(r["content"]),"status":r["status"]};save(s)
 elif args.phase=="solve-common":
  items=common(s["seed"])
  for m in models:
   k=m["family"]+":common"
   if k in s["solves"]:continue
   r=do(m["family"],m["model"],prompt_solve(items),"solve-common",1800)
   if r:s["solves"][k]={"raw":r["content"],"parsed":parse_json(r["content"]),"status":r["status"]};save(s)
 elif args.phase=="solve-reciprocal":
  for author,a in s["authors"].items():
   qs=((a.get("parsed") or {}).get("questions") or [])
   if len(qs)!=10:continue
   for m in models:
    if m["family"]==author:continue
    k=m["family"]+":peer:"+author
    if k in s["solves"]:continue
    r=do(m["family"],m["model"],prompt_solve(qs),k,2200)
    if r:s["solves"][k]={"raw":r["content"],"parsed":parse_json(r["content"]),"status":r["status"]};save(s)
 elif args.phase=="report":
  report={"models":[],"common":common(s["seed"]),"state_sha256":H(json.dumps(s,sort_keys=True))}
  keys={x["id"]:x["a"] for x in report["common"]}
  for m in models:
   fam=m["family"]; row={"family":fam,"model":m["model"],"authored_valid":len((((s["authors"].get(fam) or {}).get("parsed") or {}).get("questions") or []))}
   ans=(((s["solves"].get(fam+":common") or {}).get("parsed") or {}).get("answers") or []); amap={x.get("id"):str(x.get("answer","")).strip().upper().replace(" ","") for x in ans}
   row["common_correct"]=sum(amap.get(k)==str(v).upper().replace(" ","") for k,v in keys.items());row["common_total"]=10
   peer_ok=peer_n=0
   for author,a in s["authors"].items():
    if author==fam:continue
    qs=((a.get("parsed") or {}).get("questions") or []); frozen={x.get("id"):str(x.get("answer","")).strip().upper().replace(" ","") for x in qs}
    aa=(((s["solves"].get(fam+":peer:"+author) or {}).get("parsed") or {}).get("answers") or []); got={x.get("id"):str(x.get("answer","")).strip().upper().replace(" ","") for x in aa}
    for k,v in frozen.items():peer_n+=1;peer_ok+=got.get(k)==v
   row["reciprocal_exact_correct"]=peer_ok;row["reciprocal_exact_total"]=peer_n;report["models"].append(row)
  Path("model-tournament-report.json").write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report,indent=2))
 save(s)
if __name__=="__main__":main()
