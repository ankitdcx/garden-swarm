#!/usr/bin/env python3
"""Bounded GCSC Epoch-1 discovery kernel.

This deliberately derives obligation signatures from GSL relations and cross-cutting
semantic facts, not from the Garden invariant catalogue.
"""
from dataclasses import dataclass
from itertools import product
from collections import Counter,defaultdict

OBJECTS=("TIME","SPACE","THING","EVENT","ACTION","AGENCY","RULE","VALUE","CONTEXT","CLAIM")
RELATIONS=("identifies","causes","governs","values","frames","acts","obeys","assesses","contextualizes","controls","partOf","dependsOn","owns","delegates","references","derivedFrom","equivalentTo","contradicts","supports","blocks","hasHypothesis","supersedes","conflictsWith","originatesFrom")
REL_OBL={
"delegates":("REQUIRE_AUTHORITY","REQUIRE_CONTEXT","REQUIRE_TIME_VALIDITY","REQUIRE_AUDIT_TRACE","PROHIBIT_AUTHORITY_AMPLIFICATION"),
"acts":("REQUIRE_AUTHORITY","REQUIRE_CONTEXT","REQUIRE_TIME_VALIDITY"),
"causes":("REQUIRE_CONTEXT","REQUIRE_TIME_VALIDITY","REQUIRE_EPISTEMIC_WARRANT"),
"supports":("REQUIRE_EPISTEMIC_WARRANT","REQUIRE_PROVENANCE","PROHIBIT_EPISTEMIC_PROMOTION"),
"derivedFrom":("REQUIRE_PROVENANCE","REQUIRE_DEPENDENCY_VALIDITY","PRESERVE_PROVENANCE"),
"dependsOn":("REQUIRE_DEPENDENCY_VALIDITY",),
"controls":("REQUIRE_AUTHORITY","REQUIRE_CONTEXT","REQUIRE_AUDIT_TRACE"),
"governs":("REQUIRE_AUTHORITY","REQUIRE_CONTEXT"),
"owns":("REQUIRE_CONTEXT",),
"supersedes":("REQUIRE_TIME_VALIDITY","REQUIRE_PROVENANCE","PRESERVE_PREDECESSOR"),
"conflictsWith":("CONFLICT_REQUIRES_RESOLUTION","PRESERVE_UNKNOWN"),
"contradicts":("CONFLICT_REQUIRES_RESOLUTION","REQUIRE_EPISTEMIC_WARRANT","PRESERVE_UNKNOWN"),
"equivalentTo":("REQUIRE_CONTEXT","REQUIRE_PROVENANCE"),
}
@dataclass(frozen=True)
class SemanticClass:
 source:str; relation:str; target:str; obligations:tuple[str,...]
def l0_classes():
 out=[]
 for s,r,t in product(OBJECTS,RELATIONS,OBJECTS):
  out.append(SemanticClass(s,r,t,tuple(sorted(REL_OBL.get(r,())))))
 return out
def obligation_signature_counts():
 c=Counter(x.obligations for x in l0_classes())
 return c
def candidate_invariant_families():
 # One family per distinct nonempty obligation signature at this primitive layer.
 return {sig for sig in obligation_signature_counts() if sig}
def l2_relation_motifs():
 # relation-pair topology A-r1-B-r2-C, type identities abstracted.
 return {(r1,r2) for r1 in RELATIONS for r2 in RELATIONS}
def report():
 sigs=obligation_signature_counts()
 return {
  "raw_l0":2400,
  "l0_material_signature_classes":len(sigs),
  "l0_nonempty_material_signature_classes":sum(1 for s in sigs if s),
  "l0_empty_or_not_yet_materialized_cells":sigs.get((),0),
  "l2_relation_pair_topologies":len(l2_relation_motifs()),
  "note":"These are discovery-kernel classes, not Garden coverage. Empty means no axiom in the independent seed, not no material obligation."
 }
if __name__=="__main__": print(report())
