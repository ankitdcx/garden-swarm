#!/usr/bin/env python3
"""Conservative semantic comparison primitives for GCSC blind rediscovery."""
import re
CANON={
 "AUTHORITY":("authority","authorize","authorization","delegat","permission","consent"),
 "CONTEXT":("context","scope","applicab","jurisdiction"),
 "TIME":("time","expiry","expire","stale","validity"),
 "AUDIT":("audit","trace","receipt","provenance"),
 "PROVENANCE":("provenance","lineage","source"),
 "EPISTEMIC":("evidence","epistemic","warrant","claim","proof"),
 "DEPENDENCY":("dependenc","invalidate"),
 "UNKNOWN":("unknown","unresolved","inconclusive"),
 "CONFLICT":("conflict","contradict"),
 "SAFETY":("safety","k0p","hazard"),
 "RIGHTS":("right","sovereign","dignity"),
 "PRIVACY":("privacy","retention"),
 "RECOVERY":("recovery","rollback","compensat"),
 "RESOURCE":("resource","termination","liveness"),
}
def fingerprint(text):
 t=text.lower()
 return frozenset(k for k,terms in CANON.items() if any(x in t for x in terms))
def compare(discovered,existing):
 d,e=fingerprint(discovered),fingerprint(existing)
 if not d or not e: return "UNRESOLVED"
 if d==e:return "EQUIVALENT_CANDIDATE"
 if d<e:return "EXISTING_REFINES_DISCOVERY"
 if e<d:return "DISCOVERY_REFINES_EXISTING"
 if d&e:return "OVERLAP_REVIEW_REQUIRED"
 return "NOVEL_OR_UNMAPPED"
