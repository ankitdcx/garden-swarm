#!/usr/bin/env python3
"""GCSC bounded L2 discovery: relation-pair motifs and emergent obligation deltas."""
from itertools import product
from tools.gcsc_epoch1_discovery import RELATIONS,REL_OBL
INTERACTION={
 ("delegates","acts"):("REQUIRE_DELEGATION_SCOPE_COMPATIBILITY","REQUIRE_AUTHORITY_AT_EFFECT","PROHIBIT_AUTHORITY_AMPLIFICATION"),
 ("supports","supports"):("REQUIRE_CHAIN_WARRANT","PROHIBIT_EPISTEMIC_PROMOTION"),
 ("causes","causes"):("REQUIRE_CAUSAL_MODEL","REQUIRE_ASSUMPTION_COMPATIBILITY","REQUIRE_CONTEXT_COMPATIBILITY"),
 ("owns","controls"):("REQUIRE_OWNERSHIP_CONTROL_DISTINCTION","REQUIRE_AUTHORITY"),
 ("hasHypothesis","assesses"):("REQUIRE_EPISTEMIC_WARRANT","PRESERVE_HYPOTHESIS_STATUS"),
 ("dependsOn","supersedes"):("REQUIRE_DEPENDENCY_REVALIDATION","PRESERVE_PREDECESSOR"),
 ("conflictsWith","governs"):("CONFLICT_REQUIRES_RESOLUTION","REQUIRE_CONTEXT"),
 ("contradicts","supports"):("CONFLICT_REQUIRES_RESOLUTION","PRESERVE_UNKNOWN","REQUIRE_EPISTEMIC_WARRANT"),
 ("partOf","delegates"):("PROHIBIT_AUTHORITY_BY_AGGREGATION","REQUIRE_AUTHORITY"),
 ("delegates","delegates"):("REQUIRE_DELEGATION_SCOPE_INTERSECTION","PROHIBIT_AUTHORITY_AMPLIFICATION"),
}
def baseline(r1,r2): return frozenset(REL_OBL.get(r1,()))|frozenset(REL_OBL.get(r2,()))
def actual(r1,r2): return baseline(r1,r2)|frozenset(INTERACTION.get((r1,r2),()))
def emergent(r1,r2): return actual(r1,r2)-baseline(r1,r2)
def report():
 pairs=list(product(RELATIONS,repeat=2))
 e=[p for p in pairs if emergent(*p)]
 return {"raw_relation_pairs":len(pairs),"interaction_seed_pairs":len(e),
         "distinct_emergent_atoms":len(set().union(*(emergent(*p) for p in e))) if e else 0,
         "pairs":[{"r1":a,"r2":b,"delta":sorted(emergent(a,b))} for a,b in e]}
if __name__=="__main__": print(report())
