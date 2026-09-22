#!/usr/bin/env python3
"""Epoch-1 L0 classifier. Conservative: source-unsupported pairs remain UNKNOWN, never silently excluded."""
from dataclasses import dataclass
from itertools import product
OBJECTS=("TIME","SPACE","THING","EVENT","ACTION","AGENCY","RULE","VALUE","CONTEXT","CLAIM")
RELATIONS=("identifies","causes","governs","values","frames","acts","obeys","assesses","contextualizes","controls","partOf","dependsOn","owns","delegates","references","derivedFrom","equivalentTo","contradicts","supports","blocks","hasHypothesis","supersedes","conflictsWith","originatesFrom")
EXACT={"acts":({"AGENCY"},{"ACTION"}),"delegates":({"AGENCY"},{"AGENCY"})}
def classify(source,relation,target):
    if relation in EXACT:
        s,t=EXACT[relation]
        return "TYPED_ADMISSIBLE_SOURCE_SUPPORTED" if source in s and target in t else "UNKNOWN_PAIR_PREDICATE"
    return "UNKNOWN_PAIR_PREDICATE"
def counts():
    out={"TYPED_ADMISSIBLE_SOURCE_SUPPORTED":0,"UNKNOWN_PAIR_PREDICATE":0}
    for s,r,t in product(OBJECTS,RELATIONS,OBJECTS): out[classify(s,r,t)]+=1
    assert sum(out.values())==2400
    return out
if __name__=="__main__": print(counts())
