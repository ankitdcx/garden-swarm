#!/usr/bin/env python3
"""Mechanical closure-lint data model for GCSC catalogue audits."""
from dataclasses import dataclass
@dataclass(frozen=True)
class ClosureBinding:
 semantic_class:str
 schemas:tuple[str,...]=()
 invariants:tuple[str,...]=()
 tests:tuple[str,...]=()
 proofs:tuple[str,...]=()
 functions:tuple[str,...]=()
 owners:tuple[str,...]=()
def lint(x:ClosureBinding,requires_verification=True):
 out=[]
 if not x.schemas: out.append("MISSING_SCHEMA_BINDING")
 if not x.invariants: out.append("MISSING_INVARIANT_BINDING")
 if requires_verification and not x.tests and not x.proofs: out.append("MISSING_VERIFICATION_BINDING")
 if not x.functions: out.append("MISSING_FUNCTION_BINDING")
 if not x.owners: out.append("MISSING_OWNER_BINDING")
 return tuple(out)
def classify_catalogue(schema_to_links,invariant_to_links,test_to_links,function_to_links):
 return {
  "orphan_schema_candidates":sorted(k for k,v in schema_to_links.items() if not v),
  "orphan_invariant_candidates":sorted(k for k,v in invariant_to_links.items() if not v),
  "orphan_test_candidates":sorted(k for k,v in test_to_links.items() if not v),
  "incomplete_function_candidates":sorted(k for k,v in function_to_links.items() if not v),
 }
