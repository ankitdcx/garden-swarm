# Garden/GSL repository compliance audit — merged closure plan

This file records the merged result of the canonical-design review, the public-repository compliance audit, and the repository-wide GSL review. It is an audit/provenance artifact, not a canonical Garden design document and not an acceptance certificate.

## Status

- Garden v15.5 canonical source remains immutable.
- `garden-swarm` is governed as `SPECIFIED_DESIGNEPOCH_CANDIDATE` until the acceptance requirements in `gsl/DESIGN_EPOCH.json` are satisfied by trusted evidence.
- Repository compliance is evaluated through machine receipts and fail-closed change governance; artifact classification alone is not semantic certification.

## Closed findings carried forward

1. FunctionContract coverage: direct contracts plus deterministic generated contracts, exactly-one resolution, source hash binding.
2. Typed result algebra for delegation receipt validation; legacy Bool adapter scheduled for removal in this closure.
3. QualifiedProfileParameter registry for operational policy constants.
4. DesignEpoch/source-root binding without self-acceptance.
5. GardenSkillManifest alignment and manifest hashing.
6. CIConformancePipelineReceipt generation and enforcement.
7. MCP AgentEnvelope and exact tool allowlist enforcement.
8. Structural repository ReferenceClosureReceipt.
9. Typed repository provenance.

## Remaining closure requirements

1. Durable committed/release-bound conformance and reference-closure receipts.
2. Remove the non-compliant `verify_receipt` compatibility adapter after callers migrate.
3. Preserve STALE/UNKNOWN as typed states/reasons feeding ActionGate while keeping ALLOW/REJECT/ESCALATE as the Decision Algebra.
4. Derive constitutional classification from protected-base policy and observed diff; proposed policy cannot authorize itself.
5. Govern every material diff as a `RepoChangeEnvelope` with exact changed paths, source obligations, DesignEpoch, applicable modules, trusted authority, evidence/review bindings, disposition and durable receipt.
6. Add DEV-AI ExactReviewBinding, AIIndependenceAssessment and MachineProjectionReceipt where AI-assisted development applies.
7. Make runtime configuration resolve QualifiedProfileParameters instead of relying on coincidentally matching literals.
8. Publish shared conformance vectors used by public prototype, private kernel and historical/bootstrap implementations.
9. Expand source-obligation extraction/coverage and bind implementation deltas to obligations.
10. Material changes carry Compare/DO_NOTHING, Reason, Proof/Test/Evidence and applicable algebra/AAP/authority bindings without decorative invocation of irrelevant modules.
11. Complete bootstrap/frozen-verifier ceremony artifacts required for first DesignEpoch acceptance, while keeping canonical promotion human-controlled.

## Decision rule

No PASS in this repository means canonical Garden certification, empirical validation or deployment permission unless the receipt explicitly establishes that narrower claim. Unknown, stale, inconclusive or malformed evidence cannot be relabeled PASS.
