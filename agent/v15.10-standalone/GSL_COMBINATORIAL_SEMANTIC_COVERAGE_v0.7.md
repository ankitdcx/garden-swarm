# GCSC v0.7 — Architecture Closure / Epoch-1 Bootstrap
Status: NONCANONICAL WORKING CANDIDATE. Inherits unchanged v0.2–v0.6.

## Final structural repairs
1. Execution and materiality are interleaved at every event/commit: derive current obligations/guards, admit/block event, transition, retain intermediate obligations/violations, repeat. LiftToClass occurs only after trace evaluation.
2. Material marking is conservative and world-relative. NON_MATERIAL requires exhaustive static/bounded proof over the frozen finite epoch; otherwise MATERIAL. PROVISIONAL is MATERIAL.
3. Static independence includes READ, WRITE, MUTATING_READ, RESOURCE, AUTHORITY, WORLD and ORDER_OBSERVABLE dependencies. Any rule/oracle able to observe relative order contributes dependencies. Unproved independence => dependent.
4. Execution is mutation-only over preallocated finite symbolic slots. Quantifiers name their finite universe/active domain explicitly.
5. Worlds use snapshot isolation at branch_time; later parent facts/rules/atoms do not bleed into children. Invalid rule deltas cannot PASS.
6. Structural cycles and execution cycles are distinct. Deadlock/livelock/schedule conflict are explicit execution diagnostics.
7. ORDER_SENSITIVE with materially distinct unresolved outcomes cannot project to VALID. Report situation coverage and terminal-class coverage separately.
8. UNKNOWN refinement is total; known->UNKNOWN requires explicit invalidation evidence.
9. Every dependency-kind overlap has a frozen pair outcome.
10. Emergence uses the same concrete trace/state boundary as full evaluation. ExpectedClosure contains ordinary consequences/defeat/contradiction. Interaction-dependence is structurally derived from minimal multi-component support, not author-selected tags.
11. Provenance is separate from atom identity and computed on demand under bounds.
12. Existing Garden schemas/invariants/tests are hidden from discovery. Compare normalized semantic families only after independent derivation: A∩B rediscovered; B-A candidate gaps; A-B blind spots/redundancy/implementation-specific candidates.
13. No coverage percentage before the relevant MeasurementEpoch is frozen and the search layer completes.

## Epoch-1 build order
canonical serialization -> 24 relation signatures/bindings -> finite domains/identity -> materiality atoms/axioms -> transition/composition/independence -> ProjectValidity -> dependency/refinement matrices -> worlds/liability/emergence -> L0/L0Q -> Garden binding index -> blind rediscovery -> L1/L2/L3 -> declared L4 -> bounded L5.
