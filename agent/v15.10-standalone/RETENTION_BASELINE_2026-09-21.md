# Garden v15.10 Standalone Rebuild — Frozen Retention Baseline

Date: 2026-09-21
Status: WORKING / NONCANONICAL
Goal: rebuild v15.10 as a standalone abstract design with no current semantic dependency on v15.8/v15.9 files.

## Frozen source corpus

v15.8: five attached files (User/System/Technical/Annexure/Theories), 2,903,731 bytes total.
v15.9: five attached unique files (User/System/Technical/Annexure/Theories), 2,925,297 bytes total.

v15.8 remains an anti-loss source. v15.9 is treated as the corrected successor only where its reviewed correction/disposition is explicit.

## Mechanical identifier census

A direct full-text census over the attached five-file corpora produced:

| Class | v15.8 | v15.9 | v15.8 absent from v15.9 | new in v15.9 |
|---|---:|---:|---:|---:|
| H/S/T/A/TH/RA anchors | 315 | 308 | 7 | 0 |
| SchemaIDs | 733 | 735 | 0 | 2 |
| TEST-* identifiers | 881 | 881 | 0 | 0 |
| REG-* identifiers | 62 | 62 | 0 | 0 |
| RIGHT-* identifiers | 27 | 27 | 0 | 0 |
| broad invariant/qualified-ID pattern | 3261 | 3261 | 0 | 0 |

The seven v15.8 anchors not literally present in v15.9 are:
- [A-V155]
- [H-V155]
- [RA-V155]
- [S-V155]
- [T-CLIC-BIND-V155]
- [T-GCL-V155]
- [T-V155]

These are v15.5 release/integration anchors embedded in the inherited lineage. They MUST receive explicit v15.10 historical-alias/supersession dispositions; literal absence is not treated as proof that their semantics may be discarded.

## Standalone acceptance rules

1. No current definition may resolve only by "see v15.8", "see v15.9", predecessor link, Git history, chat history, or REFERENCED_PREDECESSOR_SOURCE.
2. Every current semantic unit must resolve inside the v15.10 Book + Technical Core + Catalogue.
3. Historical provenance may name predecessors, but provenance is not a substitute for the current definition.
4. Every v15.8/v15.9 item receives a disposition: PRESERVED, GENERALIZED, MERGED_EQUIVALENT, SUPERSEDED_WITH_REPLACEMENT, HISTORICAL_NONCURRENT, or UNRESOLVED_RETAINED.
5. UNMAPPED is a release blocker.
6. Unresolved predecessor obligations remain unresolved obligations; abstraction cannot silently promote them to PASS.
7. Rights, authority, safety, epistemic status, proof/evidence distinctions, failure/UNKNOWN behavior, dependencies, invalidators, schemas, invariants, tests and registry identity are semantic data and cannot be dropped as "documentation detail".
8. Reverse closure is mandatory: for any predecessor identifier/semantic family, the v15.10 package must answer where its current meaning or historical disposition lives.
9. Size reduction is accepted only when caused by deduplication/generalization/structured encoding, not externalization of meaning.
10. v15.11 work is downstream and must not be used to paper over a v15.10 retention gap.

## First audit result

At identifier-family level, v15.9 preserves all v15.8 SchemaIDs, TEST identifiers, registries, rights and the broad invariant/qualified-ID set found by the census. The only literal anchor losses are the seven inherited v15.5 integration anchors listed above. This is strong structural retention evidence, but not by itself a semantic no-loss proof.

## Construction order

1. Build complete predecessor-to-v15.10 disposition ledger.
2. Build standalone Catalogue as the semantic backbone.
3. Build Technical Core from Catalogue-owned semantics and current flows/contracts.
4. Write the nontechnical Book from the same current semantic graph.
5. Run internal-reference closure and forbidden-predecessor-dependency scans.
6. Run reverse-retention checks from v15.8 and v15.9.
7. Run external challengers after deterministic closure.
8. Freeze standalone v15.10 only after zero UNMAPPED current semantics.

Authority effect: NONE.
