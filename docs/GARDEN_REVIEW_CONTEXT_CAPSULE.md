# Garden review context capsule

Status: noncanonical operating documentation for bounded Garden review.

A Garden section must not be reviewed as an isolated fragment. The default review unit is small, but its context is not. Every bounded review packet combines the exact target with a source-bound whole-Garden architecture orientation and the dependency closure needed to judge that target.

## What each reviewer receives

The same initial packet is sent independently to all five OpenRouter reviewer families. It contains:

1. **Source identity** — DesignEpoch, canonical/candidate source roots, exact target path and hash, capsule hash.
2. **Whole-Garden orientation** — Garden purpose, current document/topology map, control flow, constitutional/authority/HSA/rights boundaries, Reason/Compare/Proof/Evidence/AAP/ActionGate/DesignEpoch boundaries, major owner/registry map and broadly applicable invariants.
3. **Exact target source** — the section or module being reviewed, not merely a summary.
4. **Dependency closure** — upstream owners, downstream consumers, applicable contracts, SchemaIDs, invariants, tests, authority/provenance edges and other transitive dependencies required by the question.
5. **Cross-cutting obligations** — authority, HSA/rights, Human-Effect Closure, consent/privacy, security, Reason/Compare, Proof/Evidence, AAP, ActionGate, algebras, DesignEpoch, causality, rollback and audit, each included or explicitly marked not applicable.
6. **Relevant history** — supersession/retention decisions, open contradictions, relevant prior findings, failed alternatives and DO_NOTHING when material.
7. **Omission/uncertainty ledger** — what was left out, why, whether that omission could change the answer, and where to expand.

The capsule is an index/orientation layer. It never replaces the underlying Garden source.

## Expansion instead of guessing

A reviewer must return one of `SUFFICIENT`, `EXPAND_REQUIRED`, or `FULL_CONTEXT_REQUIRED` for context sufficiency. If context is insufficient it must name the missing dependency/source.

The expansion ladder is:

`L0_CAPSULE -> L1_DEPENDENCY_EXPANDED -> L2_CROSS_LAYER_EXPANDED -> L3_AFFECTED_DOCUMENTS_FULL -> L4_FULL_GARDEN`

If an initial reviewer finds a material context gap, the current blind round stops. ChatGPT expands the packet, creates a new source-packet hash/baseline commitment, and restarts all five initial reviews on the same expanded packet. One reviewer is never silently given extra initial context while the others remain on the old packet.

Full Garden context is mandatory when compact dependency closure cannot establish the applicable semantics, when protected/cross-cutting semantics require it, or when whole-source assurance/Compare/Proof/Evidence/Tier-A obligations apply.

## Why this works with event-driven review

The source-bound whole-Garden orientation can be reused across many section reviews while the DesignEpoch/source root/topology/owner map remain unchanged. Each review then adds only the exact local target and its dependency closure.

After a complete baseline sweep, unchanged units do not need to be repeatedly sent to models. A change invalidates only the changed unit, its affected dependency closure, and any global orientation snapshot whose source-bound assumptions changed. Clock passage alone does not trigger another full review.

The governing machine-readable policy is `agents/garden-architecture-context-capsule-policy.json`. OpenRouter convergence remains governed by `agents/independent-branch-convergence-policy.json` and EDCR by `agents/event-driven-context-policy.json`.
