# GCSC Epoch-1 v15.9 normalization checkpoint

Status: NONCANONICAL MEASUREMENT WORK

The exact attached Garden v15.9 five-file corpus has now been parsed instead of relying on the earlier compact v15.10/v15.11 projections.

## Exact syntactic baseline

- 735 unique SCHEMA-* identifiers.
- 902 unique TEST-* token forms under the current broad lexer.
- 82 unique REG-* token forms under the current broad lexer.
- 27 RIGHT-* identifiers.
- Annexure [A-INVARIANTS] contains 1,844 canonical @D definitions before [A-HISTORY].
- Excluding RIGHT-* definitions, that gives 1,817 explicit invariant definitions across 212 syntactic prefix families.

These counts supersede the earlier 49-family comparison seed as the working comparison-side source for v15.9. They do not by themselves establish semantic distinctness, completeness, or GCSC coverage.

## GCSC search spaces

RAW L0 remains 10 Core Objects x 24 Core Relations x 10 Core Objects = 2,400.

The current L1 generator remains 6 Pillars x 2,400 L0 x 7 forms x 10 facets x 21 macro artifact classes = 21,168,000 raw cells.

Neither raw space is a coverage denominator. Invalid/impossible/nonmaterial equivalence classes must be removed only by the frozen GCSC v0.7 rules, never by ad-hoc pruning.

## Blind rediscovery discipline

The 1,817 known v15.9 invariant definitions are comparison-side ground truth. Their text/IDs must not be supplied to the discovery pass. Discovery receives only the frozen GSL ontology, relation signatures, execution semantics, materiality rules, worlds and bounded generators. After discovery, normalized semantic fingerprints are compared against v15.9 to classify:

- REDISCOVERED_EXISTING
- NEW_CANDIDATE
- EXISTING_NOT_REDISCOVERED
- EQUIVALENT_OR_REFINEMENT_REVIEW_REQUIRED

A raw identifier match is insufficient for semantic rediscovery.

## Remaining gate before a real percentage

The attached corpus removes the previous predecessor-data blocker. The remaining blocker is methodological/artifact population: freeze the complete v0.7 RelationSignature qualifiers, materiality program, world set, event types, composition/unification tables and semantic-equivalence procedure. Until that is populated and the bounded search is run, reporting an invariant coverage percentage would be fabricated.

This checkpoint therefore changes the task from source recovery to finite Epoch-1 population and execution.
