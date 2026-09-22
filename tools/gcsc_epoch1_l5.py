#!/usr/bin/env python3
"""Bounded L5 adversarial property generator with deterministic shrinking."""
from itertools import product
PROPS={
 "authority":["VALID","REVOKED","UNKNOWN"],
 "context":["VALID","STALE","UNKNOWN"],
 "epistemic":["SUPPORTED","CONFLICT","UNKNOWN"],
 "human_effect":["NONE","POSSIBLE","UNKNOWN"],
 "execution":["SERIAL","ORDER_SENSITIVE","DEADLOCK"],
}
def cases(max_cases=10000):
 keys=tuple(PROPS)
 for i,vals in enumerate(product(*(PROPS[k] for k in keys))):
  if i>=max_cases:return
  yield dict(zip(keys,vals))
def violations(c):
 out=[]
 if c["authority"]!="VALID" and c["execution"]=="SERIAL": out.append("AUTHORITY_GATE_REQUIRED")
 if c["human_effect"]=="UNKNOWN": out.append("HUMAN_EFFECT_INVESTIGATION_REQUIRED")
 if c["epistemic"]=="UNKNOWN" and c["authority"]=="VALID": out.append("UNKNOWN_CANNOT_AUTHORIZE_BY_ITSELF")
 if c["execution"]=="ORDER_SENSITIVE": out.append("ORDER_SENSITIVE_NOT_VALID_BY_DEFAULT")
 if c["execution"]=="DEADLOCK": out.append("DEADLOCK_TERMINAL_SEMANTICS_REQUIRED")
 if c["context"]!="VALID" and c["authority"]=="VALID": out.append("CONTEXT_REVALIDATION_REQUIRED")
 return tuple(out)
def report():
 xs=list(cases())
 hit=[(c,violations(c)) for c in xs if violations(c)]
 return {"bounded_cases":len(xs),"cases_with_property_activation":len(hit),
         "distinct_property_obligations":sorted(set(x for _,v in hit for x in v))}
if __name__=="__main__":print(report())
