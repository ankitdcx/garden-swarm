# GCSC Epoch-1 — Bounded Implementation Report v0.1

Status: NONCANONICAL RESEARCH/MEASUREMENT RESULT
Basis: GCSC v0.7 + exact attached Garden v15.9 five-file corpus.

## 1. Corpus baseline
The attached five-file v15.9 corpus was parsed as the comparison side.
- 735 unique SchemaIDs.
- 1,817 explicit non-right invariant definitions in the canonical Annexure invariant region.
- 212 syntactic invariant-prefix families.
These are syntactic inventory counts, not 1,817 proven semantically independent invariant families.

## 2. Search-space baseline
- RAW L0 = 10 Core Objects × 24 Core Relations × 10 Core Objects = 2,400.
- Legacy Cartesian L1 representation = 21,168,000 cells, retained only as a raw representation space.
- It is NOT the semantic denominator.
- No RAW L0 cell is removed because a current schema/signature is absent.

## 3. Relation-signature result
v15.9 states that Core Relations have domain/range/cardinality/algebraic/context/version semantics, but the attached prose does not expose a complete machine-readable domain/range table.
Accordingly:
- source-explicit exact L0 pairs currently established without semantic inference: AGENCY-acts-ACTION and AGENCY-delegates-AGENCY;
- all other pair predicates remain UNKNOWN at the strict source-certification layer;
- the older 659-cell permissive signature envelope remains a candidate hypothesis, not a certified denominator.

## 4. Independent materiality kernel
The blind discovery side contains no v15.9 invariant catalogue text/IDs.
It currently models 14 independent semantic domains:
authority/consent/rights; epistemics/evidence/provenance; dependency/version/lifecycle; composition/concurrency; human-effects/privacy; safety/physical/recovery; resources/termination; security/adversarial; law/jurisdiction; evolution/self-modification; collective/multi-agent; world/context/temporal; representation/compile/runtime; domain/theory applicability.

The domain kernel currently contains 66 base obligation atoms.

## 5. Primitive/L2 discovery
Primitive relation materiality:
- 2,400 RAW L0 cells.
- 14 current primitive material-signature classes.
- 13 nonempty primitive signatures.
- 1,100 cells have no current seed axiom and remain discovery-incomplete, never treated as no-obligation/PASS.

Relation-pair L2:
- 576 raw relation-pair topologies.
- 10 currently modeled interaction pairs.
- 11 candidate emergent obligation atoms.

Post-discovery v15.9 comparison:
- 8 clear rediscoveries;
- 2 rediscovery/refinement cases;
- 1 broad-existing-support/no-single-exact-invariant case;
- 0 confirmed novel gaps.

## 6. Cross-domain discovery
- 14 semantic domains.
- 91 domain-pair topologies.
- 14 explicitly modeled cross-domain interaction pairs.
- 14 cross-domain candidate emergent obligations.
- 17 bounded L3 domain triples contain at least two modeled cross-domain interactions.

Post-discovery comparison:
- 12/14 clearly rediscovered existing v15.9 semantics.
- 2/14 have broad/partial existing support but no exact combined invariant established in the bounded search.
- 0 confirmed novel gaps.

The two strengthening candidates are:
1. generic deadlock/livelock terminal semantics;
2. explicit combined collective-message-channel integrity semantics.
Neither is yet classified as a missing Garden invariant because equivalent full-corpus semantics may exist.

## 7. What GCSC has demonstrated
The method can independently reconstruct known Garden rules before seeing the invariant catalogue. Successful blind rediscoveries include:
- no authority amplification through delegation;
- no authority union merely through collective membership;
- point-of-use/revocation-aware authority;
- epistemic non-amplification;
- causal-model/assumption/context qualification;
- dependency revalidation;
- jurisdiction/time scoping;
- semantic-to-machine security refinement;
- private-channel noninterference;
- generated-artifact invalidation.

This is evidence that the generator is not merely replaying invariant IDs.

## 8. What is NOT demonstrated
No global Garden coverage percentage is valid yet.
No claim is made that all 1,817 invariant definitions were independently rediscovered.
No claim is made that the current 66 obligation atoms are a complete materiality basis.
No claim is made that the 659 permissive pair envelope is canonical.
No claim is made that unseeded L2/L3/L4/L5 space is safe.

## 9. Why the global percentage remains unavailable
A full rediscovery percentage requires an independent generator capable of generating the semantic domain of every compared invariant. Otherwise A-B measures generator scope rather than Garden gaps.
The current implementation is bounded and deliberately conservative. Unmodeled cases remain UNKNOWN/UNEXPLORED.

## 10. Concrete Garden findings
Confirmed new invariant gaps from the bounded run: 0.
Potential dedicated-strengthening candidates requiring full-corpus equivalence review:
- ownership does not imply control/authority;
- generic deadlock/livelock terminal handling;
- combined collective-message-channel integrity.
These are candidates, not admitted defects.

## 11. Implementation artifacts
Working branch/draft PR contains:
- v0.7 architecture closure;
- exact v15.9 census;
- Epoch-1 population plan/kernel;
- source-grounded relation-signature seed;
- L0 enumerator/classifier;
- blind primitive discovery;
- L2 relation interaction generator;
- 14-domain materiality model;
- cross-domain L2/L3 generator;
- conservative semantic-comparison scaffold;
- blind-comparison reports and tests.

## 12. Honest completion boundary
The requested bounded GCSC prototype and first blind-retention experiment are complete.
The mathematically larger goal — exhaustive semantic coverage of all Garden domains through depth 64 — is not computationally or semantically complete in this prototype and must remain an iterative measurement program. The framework explicitly records this as UNKNOWN/UNEXPLORED instead of fabricating completeness.

The next Garden design decision is therefore not another abstract GCSC architecture review. It is whether to admit the bounded GCSC machinery as a noncanonical verification/research tool and continue expanding its independent materiality/generator library under versioned Measurement Epochs.
