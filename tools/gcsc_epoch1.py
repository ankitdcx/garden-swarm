#!/usr/bin/env python3
from dataclasses import dataclass
from itertools import product
from typing import Iterable
OBJECTS=("TIME","SPACE","THING","EVENT","ACTION","AGENCY","RULE","VALUE","CONTEXT","CLAIM")
RELATIONS=("identifies","causes","governs","values","frames","acts","obeys","assesses","contextualizes","controls","partOf","dependsOn","owns","delegates","references","derivedFrom","equivalentTo","contradicts","supports","blocks","hasHypothesis","supersedes","conflictsWith","originatesFrom")
RAW_L0=2400
@dataclass(frozen=True,order=True)
class L0: source:str; relation:str; target:str
def enumerate_l0():
    xs=[L0(*x) for x in product(OBJECTS,RELATIONS,OBJECTS)]
    assert len(xs)==RAW_L0==len(set(xs)); return xs
@dataclass(frozen=True)
class Rediscovery:
    rediscovered:frozenset[str]; new_candidates:frozenset[str]; not_rediscovered:frozenset[str]
def compare_families(existing:Iterable[str],discovered:Iterable[str]):
    a,b=frozenset(existing),frozenset(discovered)
    return Rediscovery(a&b,b-a,a-b)
def coverage_allowed(epoch_frozen,search_complete,measurement_complete):
    return bool(epoch_frozen and search_complete and measurement_complete)
