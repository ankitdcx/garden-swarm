# Garden Branch Lifecycle Rule

RuleID: `RULE-BRANCH-LIFECYCLE-001`
Status: APPROVED OPERATIONAL RULE — executable check/receipt pending
Scope: `garden-swarm`, `garden-main`, Garden successor-candidate branches
Authority: bounded repository-hygiene rule; does not alter canonical Garden semantics

## Rule

`main` is the authoritative repository state. Non-main branches are temporary bounded work containers, not permanent work queues.

A working branch MUST have exactly one governed disposition:

1. **MERGED** — after required tests, independent review, SemanticImpactAssessment, Challenger/governance gates, and applicable receipts pass, merge to `main` and delete the working branch promptly.
2. **REJECTED** — preserve the decision/evidence in the ledger/PR, close the PR, then delete the working branch.
3. **SUPERSEDED** — preserve the supersession link/evidence, close the obsolete PR, then delete the working branch.
4. **ACTIVE** — retained only while bounded work or required review is genuinely in progress.
5. **FROZEN** — retained only while an explicit active FreezeRecord blocks disposition; the branch may not silently become permanent.

## Historical preservation

Historical evidence should normally be preserved by commits, merged/closed PRs, typed receipts, tags, releases, or immutable archives. Do not keep both an original working branch and an `archive/*` branch merely to preserve the same commit history.

Permanent `archive/*` branches require an explicit preservation justification. Where a tag/release/receipt provides equivalent or better provenance, prefer it and delete the redundant branch.

## Successor candidates

Normally maintain at most one active Garden successor-candidate branch for the current predecessor/DesignEpoch. Individual design deltas belong in the governed delta ledger and should not each create long-lived candidate branches.

## Housekeeping invariant

A completed branch MUST NOT survive after its PR is merged, rejected, or formally superseded unless a documented retention exception exists.

The integrator/repository hygiene check should periodically detect:

- merged branches still present;
- closed/rejected branches still present;
- duplicate branches pointing to the same commit without distinct active purpose;
- redundant `archive/*` + source-branch pairs;
- stale branches with no active PR/work item/freeze;
- more than the configured active-branch budget.

Default operational target: fewer than 10 active non-main branches per repository, with lower counts preferred. Exceeding the target is a hygiene finding, not by itself semantic failure.

## Required executable closure

This rule is not fully enforced until it has:

- `CheckID: CHECK-BRANCH-LIFECYCLE-001`;
- a deterministic branch/PR state scanner;
- a typed `BranchLifecycleReceipt/v1`;
- CI or scheduled enforcement appropriate to the repo;
- RuleID -> CheckID -> Receipt traceability.

Until then, this document is an approved rule but implementation closure remains pending.
