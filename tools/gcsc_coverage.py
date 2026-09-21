#!/usr/bin/env python3
"""GSL Combinatorial Semantic Coverage engine.

Enumerates L0 and streams the 21,168,000 L1 raw cells. It deliberately separates
structural admissibility from schema/invariant coverage. Missing relation-domain
typing is UNKNOWN rather than guessed from English relation names.
"""
from __future__ import annotations
import argparse, itertools, json
from collections import Counter

PILLARS=("Existence","Change","Agency","Law","Value","Frame")
OBJECTS=("TIME","SPACE","THING","EVENT","ACTION","AGENCY","RULE","VALUE","CONTEXT","CLAIM")
RELATIONS=("identifies","causes","governs","values","frames","acts","obeys","assesses","contextualizes","controls","partOf","dependsOn","owns","delegates","references","derivedFrom","equivalentTo","contradicts","supports","blocks","hasHypothesis","supersedes","conflictsWith","originatesFrom")
FORMS=("CONSTRUCT","CONTRACT","STATE","RELATION","PROCESS","RULE","PROJECTION")
FACETS=("IdentityLifecycle","ScopeContext","EpistemicsProvenance","AuthorityHumanBoundary","EffectsSafety","DependencyValidity","ResourceTermination","PrivacyRetention","AuditExplanation","RecoveryEvolution")
FORM_BINDINGS={
"CONSTRUCT":({"THING"},{"identifies","partOf","references"}),
"CONTRACT":({"RULE","ACTION","CONTEXT","VALUE"},{"governs","obeys","dependsOn"}),
"STATE":({"THING","VALUE","TIME","CONTEXT"},{"contextualizes","dependsOn"}),
"RELATION":({"THING","CONTEXT"},set(RELATIONS)),
"PROCESS":({"ACTION","EVENT","TIME","CONTEXT"},{"acts","causes","dependsOn"}),
"RULE":({"RULE","CONTEXT"},{"governs","obeys","blocks"}),
"PROJECTION":({"THING","VALUE","CONTEXT"},{"derivedFrom","references","equivalentTo"})}
MACROS={
"ArchitectureObject":set(FORMS),"Function":{"CONTRACT","PROCESS"},"Lifecycle":{"STATE","PROCESS","RULE"},
"Schema":{"RULE","PROJECTION"},"Receipt":{"CONSTRUCT","STATE","RELATION","PROJECTION"},
"Registry":{"CONSTRUCT","STATE","RELATION","RULE","PROJECTION"},"Test":{"PROCESS","RULE","PROJECTION"},
"ProofObligation":{"CONTRACT","PROCESS","RULE"},"Theory":set(FORMS),
"Algebra":{"CONSTRUCT","CONTRACT","RELATION","PROCESS","RULE","PROJECTION"},
"Profile":{"CONSTRUCT","CONTRACT","STATE","RELATION","PROCESS","RULE","PROJECTION"},
"EventRecord":{"CONSTRUCT","STATE","RELATION","PROJECTION"},"Binding":{"RELATION","RULE"},
"Plan":{"CONTRACT","PROCESS"},"FailureMode":{"STATE","PROCESS","RULE"},
"Query":{"CONTRACT","PROCESS","PROJECTION"},"EventSubscription":{"CONTRACT","STATE","RELATION","PROCESS"},
"ContinuousWorker":{"CONTRACT","STATE","PROCESS","RULE"},
"DynamicalSystemProfile":{"CONSTRUCT","CONTRACT","STATE","RELATION","RULE","PROJECTION"},
"AuthorityGatedContract":{"CONTRACT","RULE"},"RecoveryEnvelope":{"CONTRACT","STATE","PROCESS","RULE"}}

RAW_L0=len(OBJECTS)*len(RELATIONS)*len(OBJECTS)
RAW_L1=len(PILLARS)*RAW_L0*len(FORMS)*len(FACETS)*len(MACROS)

def structural_l1(form, macro, src, rel, dst):
    if form not in MACROS[macro]: return "INVALID_MACRO_FORM"
    objs, rels=FORM_BINDINGS[form]
    if rel not in rels: return "INVALID_FORM_RELATION"
    # Bindings name participating object vocabulary, not source/target signatures.
    # If neither endpoint participates, the form cannot explain this cell.
    if src not in objs and dst not in objs: return "INVALID_FORM_OBJECT"
    return "STRUCTURALLY_ADMISSIBLE_TYPE_UNKNOWN"

def l0():
    # No authoritative relation domain/range table is present in the supplied
    # metamodel excerpt. Do not infer it from names.
    return [{"source":s,"relation":r,"target":t,"classification":"TYPE_SIGNATURE_REQUIRED"}
            for s in OBJECTS for r in RELATIONS for t in OBJECTS]

def l1_counts():
    c=Counter()
    representatives={}
    for pillar,s,r,t,form,facet,macro in itertools.product(PILLARS,OBJECTS,RELATIONS,OBJECTS,FORMS,FACETS,MACROS):
        k=structural_l1(form,macro,s,r,t)
        c[k]+=1
        representatives.setdefault(k,{"pillar":pillar,"source":s,"relation":r,"target":t,"form":form,"facet":facet,"macro":macro})
    return c,representatives

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output");ap.add_argument("--include-l0",action="store_true");a=ap.parse_args()
    c,reps=l1_counts()
    out={"schema":"GardenGCSCCoverageReport/v1","raw_l0":RAW_L0,"raw_l1":RAW_L1,
         "method_boundary":"STRUCTURAL_REDUCTION_ONLY_UNTIL_AUTHORITATIVE_RELATION_DOMAIN_RANGE_AND_SCHEMA_INVARIANT_BINDING_INDEX_EXIST",
         "l0":{"TYPE_SIGNATURE_REQUIRED":RAW_L0},
         "l1_structural_counts":dict(c),"representatives":reps,
         "coverage_percent":None,
         "coverage_status":"NOT_COMPUTABLE_WITHOUT_AUTHORITATIVE_TYPE_AND_BINDING_TABLES",
         "anti_gaming":"UNKNOWN is retained rather than guessing relation typing or claiming schema/invariant coverage by keyword."}
    if a.include_l0: out["l0_cells"]=l0()
    raw=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if a.output: open(a.output,"w",encoding="utf-8").write(raw)
    else: print(raw,end="")
if __name__=="__main__": main()
