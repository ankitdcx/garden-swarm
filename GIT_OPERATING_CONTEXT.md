# Garden Git Operating Context — revision 2

**Revision ID:** `2026-09-16-r2`  
**Source SHA-256:** `2881e9429a98a4d1e0f4d460c8d0ff8ea30b5d2c7bcb95f568a754c51a2b844f`  
**Normative source:** `ankitdcx/garden-main:GIT_OPERATING_CONTEXT_SOURCE.json`  
**Status:** ACTIVE_NONCANONICAL_OPERATIONAL_PROCESS_SOURCE

> This Markdown is generated. Do not edit it by hand. Edit `GIT_OPERATING_CONTEXT_SOURCE.json` and regenerate.

Live GitHub rules and current repository heads override stale snapshot values in this document.

## 1. Mandatory loading order

- GIT_OPERATING_CONTEXT_SOURCE.json or generated GIT_OPERATING_CONTEXT.md
- live default-branch head and applicable GitHub rulesets
- ankitdcx/garden-main:governance/PROCESS_CURRENT.json
- the process file named by PROCESS_CURRENT.json
- CHATGPT_WORKSTREAM_POLICY.json for parallel ChatGPT Git work
- canonical/source manifests and applicable domain policies/modules

The Git operating context is loaded first for mutation mechanics, but the current Garden process pointer and the process file it names must be loaded before routing semantic/design work.

## 2. Repository snapshots

### `ankitdcx/garden-main`

- **auto_merge:** `False`
- **canonical_source_root_sha256:** `63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598`
- **design_epoch_ref:** `Garden-v15.5@63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598`
- **non_fast_forward_blocked:** `True`
- **required_checks:** `validate`, `trusted-base-admission`
- **revision_base_sha:** `1034bae620bc794637c4c1e056f9467e369eca8b`
- **strict_required_status_checks:** `True`
- **verified_merge_ruleset_id:** `23542743`
- **work_branch_ruleset_id:** `23542796`

### `ankitdcx/garden-swarm`

- **auto_merge:** `False`
- **non_fast_forward_blocked:** `True`
- **persistent_review_state_ruleset_id:** `23543091`
- **required_checks:** `verify`, `guard`
- **review_state_branch:** `garden-review-state`
- **revision_base_sha:** `c2bcaa8dcfe1284e53523f3f075616899c2af56c`
- **strict_required_status_checks:** `True`
- **verified_merge_ruleset_id:** `23543047`
- **work_branch_ruleset_id:** `23543069`

## 3. Preflight receipt

Future ChatGPT workstreams require `GardenGitPreflightReceipt/v1` before substantial editing.
The only allowed pre-receipt mutation is the small intent-only bootstrap commit needed to create the draft PR.
The receipt proves bounded preflight facts and acknowledgement; it does not prove private cognition or that a model literally 'read' a file.

**Required fields:**

- workstream_id
- repository
- base_sha
- git_context_revision
- git_context_source_sha256
- process_pointer
- process_version
- verified_merge_ruleset_id
- overlap_checked_open_prs
- overlap_result
- created_before_substantial_edit
- authority_effect

ChatGPT work branches use `chatgpt/`; integration branches use `integration/`.

## 4. Parallel ChatGPT workstreams and merge train

Workstream unit: **ONE_CHATGPT_THREAD_PLUS_ONE_BOUNDED_WORK_PACKAGE**.

**Statuses:** `ACTIVE`, `REVALIDATE_REQUIRED`, `INTEGRATING`, `STALE_DRAFT`, `ABANDONED_REVIEW_REQUIRED`, `SUPERSEDED`, `CLOSED`

- Stale draft: 72 hours without activity.
- Abandoned-review threshold: 14 days without activity.
- Time thresholds are evaluated only on a new event or maintenance scan; no polling loop is created.
- Stale/abandoned work is never auto-deleted.

**Merge train:**

- Driver: `EXTERNAL_CHATGPT_FRONTIER_OR_EXPLICIT_HUMAN_TRIGGER`.
- Scheduling: `EVENT_DRIVEN_NOT_CLOCK_DRIVEN`.
- Order: `DEPENDENCIES_FIRST_THEN_READY_TIME`.
- no unresolved semantic collision
- declared dependencies merged or satisfied
- current main/base freshness established
- required checks green for current composition
- workstream not stale abandoned superseded or closed
- Dependency invalidation moves affected work to `REVALIDATE_REQUIRED`.
- Exit: `ALL_WORKSTREAMS_MERGED_SUPERSEDED_CLOSED_OR_EXPLICITLY_BLOCKED_WITH_RECEIPT`.
- Final admission to `main` is serial.

## 5. Reviewer-quality lifecycle

Normative metric/threshold definition: `ankitdcx/garden-swarm:agents/reviewer-quality-policy.json`.
This document intentionally does not duplicate those weights as authority; the referenced policy is normative.

**Recovery:**

- DEGRADED → ACTIVE: REQUIRES_SUCCESSFUL_BLIND_REQUALIFICATION_AND_GOVERNED_REGISTRY_PR.
- QUARANTINED → ACTIVE: REQUIRES_SUCCESSFUL_BLIND_REQUALIFICATION_ZERO_HARD_FAILURES_AND_GOVERNED_REGISTRY_PR.
- No direct state jump back to ACTIVE.

**If a required reviewer becomes non-ACTIVE while a task is in flight:**

- Default: `PAUSE_CURRENT_CONVERGENCE_WITH_REVIEWER_SLOT_INVALIDATED`.
- No silent model swap.
- The same exact model may resume only after governed return to ACTIVE and a fresh source-binding check.
- A replacement model starts a new convergence cycle.

**Quality queue retention/backpressure:**

- Soft pending limit: 64.
- Hard pending limit: 128.
- Overdue after: 72 hours.
- Closed archive hash limit: 512.
- Unadjudicated items are never silently deleted.
- Crossing the hard limit blocks new convergence admission until quality debt is reduced.

## 6. Bad-merge recovery

A bad merge is recovered without rewriting protected history.

- freeze dependent merge-train entries by dependency invalidation
- create recovery branch from current main
- choose revert commit or forward-fix with explicit rationale
- open recovery PR with AgentWorkIntent and preflight receipt
- run ordinary required checks and applicable Garden process/ActionGate/human gates
- merge through protected PR path
- revalidate downstream workstreams

- `main` must never be reset or force-pushed as rollback.
- Prefer a revert when: bounded reversal is safer and preserves exact provenance.
- Prefer a forward fix when: revert would remove valid intervening dependent work or worsen state.

## 7. Secret scanning

- Central CI scanning is mandatory; local hooks are optional and not authoritative.
- Scan changed text files for high-confidence credential patterns.
- Allowlisting requires exact rule + exact path + reason.
- Fake fixtures may be allowlisted; real credentials may not.

## 8. Branch cleanup

- A merged branch may be deleted only after `MERGED_DELETE_ELIGIBLE` classification.
- `garden-review-state` is never auto-deleted.
- Stale or abandoned workstreams are never auto-deleted.
- Cleanup is event-driven and requires a cleanup receipt.

## 9. GitHub ruleset field note

GitHub ruleset field concerning unattributed Copilot-created PRs; with required approving review count 0 it does not currently add a functional approval requirement.

## 10. Request efficiency

- no repeated same-hash reads by default
- no active CI/status polling loop
- read failed job/step first
- reuse verified head/ruleset/process/context hashes until invalidated
- after 429 stop optional calls and resume from checkpoint
- exact-ref fetch is proof; search is discovery

## 11. Failure catalogue

### 1. Stale base under strict checks

**Rule:** Refresh main immediately before merge; stale green checks are insufficient.

### 2. Superseded PR still counted as concurrent intent

**Rule:** Close/supersede predecessor before replacement when practical or provide a real IntegrationReceipt.

### 3. Missing AgentWorkIntent

**Rule:** Create complete intent at draft PR creation.

### 4. Changed path missing from intent

**Rule:** Derive target paths from the final diff and keep intent current.

### 5. Missing IntegrationReceipt

**Rule:** Compare overlapping semantics and record composition evidence/tests before claiming compatibility.

### 6. Concurrent edits caused merge conflicts

**Rule:** Use early draft intents, narrow branches, and fresh integration branches for genuine collisions.

### 7. Protected/non-fast-forward branch update

**Rule:** No force push; use forward commits or fresh replacement branches.

### 8. Malformed JSON discovered late

**Rule:** Parse changed structured files before PR and still run reference closure.

### 9. Runtime/generated reference looked like missing file

**Rule:** Register generated/runtime references with their producer; never create fake placeholders.

### 10. Stale config-surface fingerprint

**Rule:** Recompute fingerprints and consumers/tests in the same work package.

### 11. Tests hardcoded old model/family assumptions

**Rule:** Search for stale assumptions and assert invariants rather than obsolete exact values unless exactness is required.

### 12. Premature duplicate aggregate failures

**Rule:** Incomplete mandatory set is UNKNOWN/DEFERRED; final PASS/FAIL only after all required lanes settle.

### 13. Classic commit-status endpoint incomplete for Actions

**Rule:** Use workflow/PR check evidence and ruleset contexts.

### 14. Code-search lag after merge

**Rule:** Use direct exact-ref fetch for proof; search is discovery.

### 15. Auto-merge assumption

**Rule:** Do not attempt auto-merge without fresh setting evidence.

### 16. AAP floor mismatch

**Rule:** Derive assurance tier/modules from the material change; never lower them to make CI green.

### 17. Human admission / trusted-base mismatch

**Rule:** Never fabricate or broaden human approval; bind it to exact governed scope.

### 18. Blind workflow retry

**Rule:** Inspect typed failure first; retry only after state/input change or proven transient failure.

### 19. Bad merge discovered after admission

**Rule:** Never rewrite main; recover via typed revert-or-forward-fix PR from current main and revalidate dependents.

## 12. Boundaries

- This is an operational Git/process source, not canonical Garden semantics.
- Receipts are evidence, not Proof, authority, human approval, or promotion.
- Request efficiency never weakens correctness, assurance, authority, privacy, safety, or process gates.

## 13. Source-of-truth rule

`ankitdcx/garden-main:GIT_OPERATING_CONTEXT_SOURCE.json` is authoritative. `GIT_OPERATING_CONTEXT.md` and `GIT_OPERATING_CONTEXT.json` are generated views.
The `garden-swarm` source copy is an exact pinned mirror and must match the authoritative source SHA-256 for the same revision.
For ChatGPT Project Sources, use the generated Markdown view rather than maintaining a separate manually edited copy.
