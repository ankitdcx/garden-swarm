#!/usr/bin/env python3
"""Bounded cross-domain GCSC motif generator. Independent of Garden invariant catalogue."""
from itertools import combinations, product
DOMAINS={
"authority_consent_rights":("REQUIRE_AUTHORITY","REQUIRE_CONSENT","REQUIRE_RIGHTS_CHECK","PROHIBIT_AUTHORITY_AMPLIFICATION","REQUIRE_REVOCATION_EFFECT"),
"epistemics_evidence_provenance":("REQUIRE_EPISTEMIC_WARRANT","REQUIRE_PROVENANCE","PRESERVE_UNKNOWN","PROHIBIT_EPISTEMIC_PROMOTION","REQUIRE_RETRACTION_PROPAGATION"),
"dependency_version_lifecycle":("REQUIRE_DEPENDENCY_VALIDITY","REQUIRE_REVALIDATION","PRESERVE_PREDECESSOR","REQUIRE_VERSION_SCOPE","REQUIRE_INVALIDATION_PROPAGATION"),
"composition_concurrency":("REQUIRE_ASSUMPTION_COMPATIBILITY","REQUIRE_CONTEXT_COMPATIBILITY","REQUIRE_ORDER_ANALYSIS","REQUIRE_CONFLICT_RESOLUTION","REQUIRE_ATOMICITY_OR_COMPENSATION"),
"human_effects_privacy":("REQUIRE_HUMAN_EFFECT_INVESTIGATION","REQUIRE_PRIVACY_CHECK","REQUIRE_PURPOSE_SCOPE","REQUIRE_MINIMIZATION","REQUIRE_RETENTION_VALIDITY"),
"safety_physical_recovery":("REQUIRE_SAFETY_CHECK","REQUIRE_HAZARD_BOUND","REQUIRE_SAFE_FALLBACK","REQUIRE_RECOVERY","REQUIRE_PHYSICAL_EFFECT_RECONCILIATION"),
"resources_termination":("REQUIRE_RESOURCE_BOUND","REQUIRE_TERMINATION_OR_LIVENESS","REQUIRE_TIMEOUT_STATUS","REQUIRE_PROTECTED_RESOURCE_FLOOR"),
"security_adversarial":("REQUIRE_AUTHENTICITY","REQUIRE_INTEGRITY","REQUIRE_CHANNEL_SEPARATION","REQUIRE_LEAKAGE_BOUND","REQUIRE_ATTACK_MODEL"),
"law_jurisdiction":("REQUIRE_JURISDICTION","REQUIRE_SOURCE_AUTHENTICATION","REQUIRE_EXCEPTION_SCOPE","PRESERVE_LEGAL_UNCERTAINTY","PROHIBIT_JURISDICTION_UNIVERSALIZATION"),
"evolution_self_modification":("REQUIRE_INDEPENDENT_REVIEW","PROHIBIT_SELF_CERTIFICATION","REQUIRE_ROLLBACK_OR_COMPENSATION","REQUIRE_SEMANTIC_DELTA","REQUIRE_DESIGNEPOCH_GATE"),
"collective_multiagent":("PROHIBIT_AUTHORITY_BY_AGGREGATION","REQUIRE_MEMBER_SCOPE_INTERSECTION","REQUIRE_COLLECTIVE_EFFECT_MONITORING","REQUIRE_MESSAGE_PROVENANCE"),
"world_context_temporal":("REQUIRE_CONTEXT","REQUIRE_TIME_VALIDITY","REQUIRE_WORLD_SCOPE","REQUIRE_SNAPSHOT_OR_REVALIDATION_POLICY","REQUIRE_STALENESS_HANDLING"),
"representation_compile_runtime":("PROHIBIT_REPRESENTATION_IDENTITY_COLLAPSE","REQUIRE_CORRESPONDENCE_VALIDITY","REQUIRE_MACHINE_TRACE_REFINEMENT","REQUIRE_GENERATION_DETERMINISM","REQUIRE_RUNTIME_GATE"),
"domain_theory_applicability":("REQUIRE_APPLICABILITY","REQUIRE_ASSUMPTIONS","REQUIRE_VALIDITY_DOMAIN","REQUIRE_FALSIFIER","PROHIBIT_THEORY_AS_AUTHORITY")}
CROSS={
frozenset(("authority_consent_rights","world_context_temporal")):("REQUIRE_POINT_OF_USE_AUTHORITY",),
frozenset(("authority_consent_rights","collective_multiagent")):("REQUIRE_AUTHORITY_INTERSECTION",),
frozenset(("authority_consent_rights","human_effects_privacy")):("REQUIRE_AFFECTED_HUMAN_AUTHORITY_BOUNDARY",),
frozenset(("epistemics_evidence_provenance","domain_theory_applicability")):("REQUIRE_EVIDENCE_APPLICABILITY_MATCH",),
frozenset(("epistemics_evidence_provenance","law_jurisdiction")):("PROHIBIT_EVIDENCE_AS_LEGAL_AUTHORITY",),
frozenset(("dependency_version_lifecycle","evolution_self_modification")):("REQUIRE_DEPENDENT_CLOSURE_REVALIDATION",),
frozenset(("composition_concurrency","safety_physical_recovery")):("REQUIRE_INTERMEDIATE_STATE_SAFETY",),
frozenset(("composition_concurrency","resources_termination")):("REQUIRE_DEADLOCK_LIVELOCK_HANDLING",),
frozenset(("human_effects_privacy","security_adversarial")):("REQUIRE_PRIVATE_CHANNEL_NONINTERFERENCE",),
frozenset(("safety_physical_recovery","world_context_temporal")):("REQUIRE_EFFECT_TIME_REVALIDATION",),
frozenset(("representation_compile_runtime","security_adversarial")):("REQUIRE_SEMANTIC_MACHINE_SECURITY_REFINEMENT",),
frozenset(("representation_compile_runtime","evolution_self_modification")):("REQUIRE_GENERATED_ARTIFACT_INVALIDATION",),
frozenset(("law_jurisdiction","world_context_temporal")):("REQUIRE_JURISDICTION_TIME_SCOPE",),
frozenset(("collective_multiagent","security_adversarial")):("REQUIRE_COLLECTIVE_CHANNEL_INTEGRITY",)}
def l2():
 out=[]
 for a,b in combinations(DOMAINS,2):
  delta=CROSS.get(frozenset((a,b)),())
  out.append((a,b,delta))
 return out
def l3():
 # bounded constitutional triples; report only triples with >=2 cross-domain activations
 out=[]
 for tri in combinations(DOMAINS,3):
  ds=set()
  for a,b in combinations(tri,2): ds.update(CROSS.get(frozenset((a,b)),()))
  if len(ds)>=2: out.append((tri,tuple(sorted(ds))))
 return out
def report():
 return {"domains":len(DOMAINS),"base_obligation_atoms":len(set().union(*map(set,DOMAINS.values()))),
 "domain_pairs":len(l2()),"pairs_with_emergent_seed":sum(bool(x[2]) for x in l2()),
 "cross_domain_emergent_atoms":len(set().union(*(set(x[2]) for x in l2()))),
 "bounded_l3_candidate_triples":len(l3())}
if __name__=="__main__":print(report())
