# Garden v15.10 Clean Rebuild Candidate — 2026-09-21

Status: NONCANONICAL WORKING CANDIDATE.

A clean standalone three-document v15.10 candidate has been generated from:
1. the exact v15.9 semantic baseline retained inside the verified 2026-09-19 package; and
2. the GCSC abstraction/process developed through the adversarial review series.

## Key change
The clean Catalogue contains 2,660 CURRENT_SEMANTIC_UNIT records. Each carries its complete current semantic text plus structured semantic envelope. Historical v15.9 locations are provenance only; no current semantic interpretation requires opening a predecessor source blob.

## Current-source topology
- Book: plain-language nontechnical projection.
- Technical: GSL v45.1, seven Design Forms, rich RelationInstance, GCSC L0-L5, materiality/composition/validity/closure/anti-gaming semantics.
- Catalogue: 2,660 current semantic payloads plus current identity/definition/family indexes.

## Verification performed
- 2,660/2,660 CURRENT_SEMANTIC_UNIT records parse.
- Each semantic payload SHA-256 matches its embedded text.
- No current semantic unit contains source_blob_ref.
- No current semantic unit uses SOURCE_ONLY as its status.
- Package SHA-256 manifest generated.

## Important
This candidate is not declared canonical, production-certified, or externally admitted merely because it was generated successfully. It is a clean successor candidate that must be compared against the exact retained v15.9/v15.10 oracle and challenged with GCSC before admission.
