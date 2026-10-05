#!/usr/bin/env python3
"""Garden Model Capability Tournament v1.0, Epoch 1."""
import hashlib,json,math,os,random,re,time
from fractions import Fraction
from pathlib import Path
from urllib import request,error
OR="https://openrouter.ai/api/v1"; CAP=.05
CFG=json.loads(Path("agents/model-capability-lab.json").read_text()); MODELS=CFG["models"]
def rng(seed): return random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16],16))
def common(seed,n=200):
 r=rng(seed); items=[]
 for i in range(n):
  typ=i%10
  if typ==0:
   a,b=r.randint(2,30),r.randint(2,30); x=a+b;y=2*x-b;x=x-y;q=f"x={a}, y={b}. Set x=x+y; then y=2*x-y using new x; then x=x-y. Give x+y.";a0=str(x+y)
  elif typ==1:
   p=r.choice([7,11,13,17]);v=r.randint(1,p-1);k=r.randint(5,18);s=v
   for _ in range(k):v=(3*v+2)%p
   q=f"Start n={s}. Repeat n=(3n+2) mod {p}, {k} times. Final n?";a0=str(v)
  elif typ==2:
   xs=list("ABCDE");r.shuffle(xs);q="Five items A-E are in a line. "+"; ".join(f"{xs[j]} immediately before {xs[j+1]}" for j in range(4))+". Give order letters only.";a0="".join(xs)
  elif typ==3:
   w=[r.randint(1,12) for _ in range(5)];q=f"Edges S-A={w[0]},S-B={w[1]},A-T={w[2]},B-C={w[3]},C-T={w[4]}. Shortest S-T cost?";a0=str(min(w[0]+w[2],w[1]+w[3]+w[4]))
  elif typ==4:
   sens=r.choice([Fraction(3,4),Fraction(4,5),Fraction(5,6)]);fp=r.choice([Fraction(1,10),Fraction(1,8),Fraction(1,6)]);prev=r.choice([Fraction(1,10),Fraction(1,5),Fraction(1,4)]);post=sens*prev/(sens*prev+fp*(1-prev));q=f"Prevalence={prev}; sensitivity={sens}; false-positive rate={fp}. P(disease|positive)? Reduced fraction.";a0=f"{post.numerator}/{post.denominator}"
  elif typ==5:
   total=r.randint(40,80);oa,ob,both=[r.randint(5,15) for _ in range(3)]; total=max(total,oa+ob+both);q=f"{total} people: {oa} only A, {ob} only B, {both} both. Neither?";a0=str(total-oa-ob-both)
  elif typ==6:
   base=r.randint(20,70);d=r.randint(2,12);e=r.randint(1,9);q=f"Output baseline {base}. P adds {d} and triggers Q subtracting {e}. With P observed output {base+d-e}. Under do(P=0), Q absent. Output?";a0=str(base)
  elif typ==7:
   d=[r.randint(1,8) for _ in range(4)];q=f"Durations A={d[0]},B={d[1]},C={d[2]},D={d[3]}. A,B start 0; C after A; D after B and C; unlimited workers. Earliest finish?";a0=str(max(d[1],d[0]+d[2])+d[3])
  elif typ==8:
   num=r.randint(20,200);z=num;s=""
   while z:s=str(z%3)+s;z//=3
   q=f"Decimal {num} in base 3, digits only.";a0=s
  else:
   aa,bb=r.randint(1,20),r.randint(1,20);q=f"Exactly one statement is true: S1: {aa}>{bb}; S2: {aa}<={bb}. Which statement is true? Answer S1 or S2.";a0="S1" if aa>bb else "S2"
  items.append({"id":f"C{i+1:03}","category":typ,"q":q,"a":a0})
 return items
def call(model,prompt,max_tokens=5000):
 key=os.environ["OPENROUTER_API_KEY"]; eps=json.loads(request.urlopen(request.Request(OR+"/models/"+model+"/endpoints",headers={"Authorization":"Bearer "+key}),timeout=60).read())["data"]["endpoints"]
 elig=[]
 for ep in eps:
  try: pp=float(ep["pricing"]["prompt"])*1e6;cp=float(ep["pricing"]["completion"])*1e6
  except: continue
  est=(len(prompt)/4*pp/1e6)+(max_tokens*cp/1e6)
  if est*1.35<=CAP:elig.append((est,ep))
 if not elig:return {"status":"UNAVAILABLE_CAP"}
 est,ep=min(elig,key=lambda x:x[0]);prov=ep.get("provider_name") or ep.get("name")
 body={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":max_tokens,"provider":{"allow_fallbacks":False,"data_collection":"deny","only":[prov] if prov else []}}
 req=request.Request(OR+"/chat/completions",method="POST",data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
 t=time.time()
 try:
  data=json.loads(request.urlopen(req,timeout=240).read());msg=(data.get("choices")or[{}])[0].get("message")or{};txt=msg.get("content")or"";cost=(data.get("usage")or{}).get("cost")
  return {"status":"OK" if txt.strip() else "NULL","text":txt,"cost":cost,"latency":round(time.time()-t,2),"provider":prov}
 except Exception as e:return {"status":"ERROR","error":type(e).__name__+":"+str(e),"provider":prov}
def parse_answers(txt):
 m=re.search(r"\{.*\}",txt,re.S)
 if not m:return {}
 try:d=json.loads(m.group())
 except:return {}
 return {str(x.get("id")):str(x.get("answer","")).strip() for x in d.get("answers",[]) if isinstance(x,dict)}
def main():
 seed="epoch1-20261005-"+hashlib.sha256(str(time.time_ns()).encode()).hexdigest()[:16];items=common(seed); results=[]; authors=[]
 # Common set in 4 chunks to avoid context/output truncation.
 for m in MODELS:
  ans={};cost=0;lat=0;statuses=[]
  for k in range(0,200,50):
   chunk=items[k:k+50];prompt="No tools/web/code. Solve independently. JSON only {answers:[{id,answer}]}. Final answers only.\n"+json.dumps([{"id":x["id"],"q":x["q"]} for x in chunk])
   z=call(m["model"],prompt,3500);statuses.append(z["status"]);cost+=float(z.get("cost") or 0);lat+=float(z.get("latency") or 0)
   if z["status"]=="OK":ans.update(parse_answers(z["text"]))
   if float(z.get("cost") or 0)>CAP:break
  correct=sum(re.sub(r"\s+","",ans.get(x["id"],"")).upper()==re.sub(r"\s+","",x["a"]).upper() for x in items)
  results.append({"family":m["family"],"model":m["model"],"common_correct":correct,"common_total":200,"common_accuracy":correct/200,"chunks":statuses,"cost_usd":cost,"latency_seconds":lat,"transport_reliability":sum(s=="OK" for s in statuses)/4})
 # Author 10 questions each, isolated.
 for m in MODELS:
  p="""Author exactly 10 novel self-contained text-only reasoning questions for other frontier models. No trivia/current facts/tools/tokenizer/string tricks. Each must have objectively verifiable answer. Return JSON {questions:[{id,category,question,answer,assumptions,difficulty,scoring_rule,ambiguity_note}]}. Do not solve any other model's questions."""
  z=call(m["model"],p,5000);authors.append({"family":m["family"],"model":m["model"],"status":z["status"],"text":z.get("text",""),"cost_usd":z.get("cost"),"latency_seconds":z.get("latency")})
 out={"schema":"GardenModelCapabilityEpoch/v1","protocol":"MODEL_CAPABILITY_LAB_v1.0","seed_sha256":hashlib.sha256(seed.encode()).hexdigest(),"common_item_hash":hashlib.sha256(json.dumps(items,sort_keys=True).encode()).hexdigest(),"common_results":results,"author_raw":authors,"common_items":items,"authority_effect":"NONE_EVIDENCE_ONLY"}
 Path("capability-epoch1-stage1.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"results":results,"authors":[{k:v for k,v in a.items() if k!="text"} for a in authors]},indent=2))
if __name__=="__main__":main()
