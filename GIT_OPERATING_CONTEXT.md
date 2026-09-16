# Garden Git Operating Context v1

**Observed:** 2026-09-16  
**Scope:** `ankitdcx/garden-main` and `ankitdcx/garden-swarm`  
**Status:** operational process source; **not** Garden canonical semantics, Proof, authority, or promotion.

## Mandatory use

Before any AI/agent performs a GitHub write, branch creation, file mutation, pull request, workflow rerun, merge attempt, branch replacement, or state-branch update for Garden:

1. Read this file first.
2. Reuse the last verified repository state only while its head/ruleset identity is unchanged.
3. Fetch the current default-branch head and relevant live ruleset(s) before starting a new write package.
4. Inspect open PR/work-intent overlap before choosing shared paths.
5. If the live GitHub rules disagree with this snapshot, **the live rules win**; update this file in the same bounded work package if practical.
6. Do not infer that a red workflow is a Git-process defect. Some Garden workflows intentionally fail closed when an assurance, authority, evidence, AAP, or conformance obligation is not met.

The objective is: **fresh base + bounded intent + minimal remote requests + no history rewriting + exact evidence + one clean merge path**.

---

## Repository snapshot

### `ankitdcx/garden-main`

Observed default branch head when this context was created:

`46516375cf0c0db387c6c2fc665282409da7278a`

Active rulesets observed:

- **Garden Main - Verified merges** — ruleset `23542743`
  - applies to default/main;
  - deletion blocked;
  - non-fast-forward updates blocked;
  - pull request required;
  - review threads must be resolved;
  - extra approval is required for unattributed changes;
  - allowed merge methods: merge, squash, rebase;
  - strict required-status policy enabled;
  - required checks: **`validate`** and **`trusted-base-admission`**;
  - no bypass actor is available to the connected agent.
- **Garden Main - Work branch history** — ruleset `23542796`
  - applies to non-main branches;
  - non-fast-forward updates blocked.

Important consequence: a branch history rewrite that needs force-push is not the normal recovery path. Prefer a merge-from-current-main when safe, or create a **fresh replacement branch from current main** and supersede the old PR.

High-level structure used during Git work:

- `canonical/current/` — canonical-current identity and source manifest.
- `implementation/garden_kernel/` — private/reference kernel implementation.
- `implementation/tests/` — deterministic kernel/conformance tests.
- `governance/` — authority, admission, process and governance records.
- `design_deltas/` — successor/candidate deltas, including v15.7 work.
- `reviews/evolution/` — Reason / Algebra / Assurance / Production receipts.
- `.github/workflows/` — protected CI and admission workflows.

Garden-main PR intents must be bound to the **actual current PR base SHA**, source root and DesignEpoch from the base branch. Canonical v15.5 is not edited in place unless a separately authorized successor process explicitly permits it.

### `ankitdcx/garden-swarm`

Observed default branch head when this context was created:

`2e6de899e0cf21085928ead6f39910f42130c1cb`

Active rulesets observed:

- **Garden Swarm - Verified merges** — ruleset `23543047`
  - applies to default/main;
  - deletion blocked;
  - non-fast-forward updates blocked;
  - pull request required;
  - review threads must be resolved;
  - extra approval is required for unattributed changes;
  - allowed merge methods: merge, squash, rebase;
  - strict required-status policy enabled;
  - required checks: **`verify`** and **`guard`**;
  - no bypass actor is available to the connected agent.
- **Garden Swarm - Work branch history** — ruleset `23543069`
  - applies to ordinary non-main work branches;
  - non-fast-forward updates blocked.
- **Garden Swarm - Persistent review state** — ruleset `23543091`
  - applies to `garden-review-state`;
  - deletion blocked;
  - non-fast-forward updates blocked.

Observed repository behavior: GitHub auto-merge is disabled. Do not depend on auto-merge.

High-level structure used during Git work:

- root five-file/public Garden source and `SOURCE_MANIFEST.json`;
- `agents/` — machine policies, routing, review and provider constraints;
- `tools/` — worker, selector, review, audit and integration tooling;
- `gsl/` — repository GSL profiles/contracts/registries;
- `swarm/` — orchestrator and integration-provenance implementation;
- `prototype/` — non-certified executable reference mechanisms;
- `server/` — read-only discovery/MCP foundation;
- `tests/` and `swarm/tests/` — regression and conformance tests;
- `docs/` — operating and mechanism documentation;
- `.github/workflows/` — CI and review execution surfaces.

`garden-review-state` is durable execution state, not an ordinary feature branch. Never delete, rewrite, or casually reconstruct it.

---

## Required Git process

### A. Before writing anything

1. Read this file.
2. Fetch current `main` once.
3. Fetch current relevant rulesets once if the saved ruleset snapshot is not already fresh for this workstream.
4. Search current open PRs / declared AgentWorkIntents for overlapping paths, symbols, semantic domains, invariants, and contracts.
5. Decide the bounded work package and expected changed paths **before** creating the PR.
6. Prefer a new uniquely named branch from current main. Do not share a work branch with another chat/agent unless explicitly coordinated.

### B. Before opening a PR

Run the cheapest deterministic checks first:

- parse every changed JSON/YAML file;
- compile/run directly affected code tests;
- run repository reference-closure checks when references or path-like strings changed;
- run config-surface/fingerprint tests when model/reviewer/policy surfaces changed;
- update tests that intentionally encode the old policy shape;
- for `garden-main`, run the applicable evolution Reason/Algebra/AAP/Production audits for material governance changes;
- ensure AAP safety tier/modules are **derived from the change** and are not below the minimum floor;
- ensure runtime/generated paths are registered in the reference policy rather than pretending they are tracked files.

### C. PR intent

Every guarded PR must carry an `AgentWorkIntent` covering the **actual complete diff**.

Rules:

- base SHA must match the PR's actual current base;
- target paths must cover every changed file;
- semantic domains/invariants/contracts must include cross-file effects, not only filenames;
- `garden-main` also binds source root + DesignEpoch;
- review/proposal evidence never grants authority or canonical status.

If another open intent overlaps, independently compare the two changes and add an `IntegrationReceipt` only after confirming compatibility and running post-composition tests. Never fabricate compatibility.

### D. While CI runs

- Do not poll in a loop.
- Observe once after mutation; wait for a new completion event/user turn before another status read unless completion is already known.
- If a workflow fails, read **the failed job/step only** first.
- Classify the failure before retrying:
  - Git/process/config defect → fix exact cause;
  - expected fail-closed semantic/assurance result → repair the underlying design/receipt or leave blocked;
  - transient provider/network error → preserve checkpoint; bounded retry only if the owning policy permits it.
- Rerun only the failed job/workflow when possible; do not rerun successful lanes without cause.

### E. Before merge

1. Fetch current main head.
2. Compare it with the PR base. Strict required-status rules mean **old green checks are not sufficient after main advances**.
3. If base is stale:
   - do not attempt to bypass required checks;
   - do not force-push rewritten history;
   - either compose current main into the branch with a normal forward update when clean, or create a fresh current-base replacement branch/PR;
   - when replacing a PR, **close/supersede the old PR before opening the replacement** when practical, so it is no longer treated as concurrent work.
4. Confirm exact required checks for that repository are green on the current composition.
5. Confirm review threads are resolved.
6. Merge through the PR path only.

### F. After merge

- Verify default-branch head once.
- Fetch the changed file directly from `main` when proof of deployed repository state matters.
- Do not rely on stale code-search indexing immediately after merge.
- Record any new failure mode in this file if it represents a reusable Git/process lesson.

---

## Failure catalogue and prevention rules

### 1. Stale base under strict required checks

**Observed:** a PR had green head checks, but `main` advanced before merge; GitHub returned required checks as expected/pending and refused merge.

**Prevention:** always re-read `main` immediately before merge. Green checks are valid only for the current strict composition. If stale, compose/recreate and let checks rerun.

### 2. Superseded PR still counted as concurrent intent

**Observed:** replacement PR opened while its predecessor was still open, causing integration-provenance collision with the old identical intent.

**Prevention:** when replacing rather than composing, close/mark the predecessor superseded **before** opening the new PR where possible. If both must remain open, include an explicit IntegrationReceipt.

### 3. Missing AgentWorkIntent

**Observed:** integration provenance blocked PRs with `MISSING_AGENT_WORK_INTENT`.

**Prevention:** create the complete intent in the PR body at PR creation, not after CI fails.

### 4. Changed path missing from intent

**Observed:** guarded PRs can fail when actual changed files are absent from declared `target_paths`.

**Prevention:** derive target paths from the actual final diff; after adding a new file, update the PR intent before expecting provenance CI to pass.

### 5. Integration receipt missing for semantic/path overlap

**Observed:** provider-policy and v15.7/review changes overlapped broad semantic domains or paths and were blocked until a compatibility receipt was supplied.

**Prevention:** check open work before editing. When overlap is intentional, compare semantics and add `IntegrationReceipt/v1` with concrete composition evidence and tests.

### 6. Concurrent edits caused merge conflicts

**Observed:** another workstream changed the same review subsystem while a PR was in progress.

**Prevention:** do preflight overlap search first; keep work packages narrow; refresh main before final composition; preserve the newer work rather than overwriting it.

### 7. Non-fast-forward / protected branch write

**Observed:** direct update/force-style operations were blocked by repository rules or PR-only behavior.

**Prevention:** never plan on force push. Use forward commits on a work branch and merge via PR. If history becomes awkward, create a fresh branch from current main.

### 8. Malformed JSON discovered by reference closure

**Observed:** a context-policy JSON typo made the file unreadable; ordinary tests passed until reference closure failed.

**Prevention:** parse every changed JSON before PR. Reference closure is still required because syntactically valid strings can contain bad repository references.

### 9. Runtime/generated reference looked like a missing file

**Observed:** reference closure failed on paths such as runtime state/directive outputs until their generator/owner was registered.

**Prevention:** never create a fake tracked placeholder merely to satisfy closure. Register generated/runtime references with the owning producer in the reference policy.

### 10. Stale config-surface fingerprint

**Observed:** changing reviewer/model-policy shape invalidated the config-surface fingerprint and consumers.

**Prevention:** whenever a watched config changes, recompute the fingerprint and update all registered consumers/tests in the same work package.

### 11. Stale tests hardcoded old policy cardinality/model assumptions

**Observed:** model/provider changes broke tests that still assumed the old number of families or old model identities.

**Prevention:** search for old policy/model/family assumptions before PR; update tests to assert invariants rather than obsolete exact counts where exact counts are not themselves an invariant.

### 12. Required workflow aggregation produced duplicate/premature red runs

**Observed:** `pipeline-aggregate` can be triggered once per mandatory workflow completion; an aggregate may run while other mandatory lanes are still unsettled, producing noisy duplicate failures.

**Prevention/optimization:** aggregate must treat an unsettled mandatory set as `UNKNOWN/DEFERRED`, not as final PASS/FAIL. Final FAIL/PASS is authoritative only after every mandatory lane has a completed current attempt.

### 13. Classic commit-status endpoint is not enough for Actions checks

**Observed:** commit-status lookup can be empty while GitHub Actions check runs exist.

**Prevention:** use PR/workflow-run evidence and ruleset-required check contexts; do not conclude "no checks" from an empty classic status list.

### 14. Code search lag after merge

**Observed:** GitHub code search returned stale old-commit snippets shortly after merge.

**Prevention:** use direct `fetch_file`/contents at `ref=main` or exact SHA for authoritative state; code search is discovery, not post-merge proof.

### 15. Auto-merge assumption

**Observed:** `garden-swarm` rejected auto-merge because repository auto-merge is disabled.

**Prevention:** do not spend a call attempting auto-merge unless repository settings were freshly verified to permit it.

### 16. Garden-main AAP assurance floor mismatch

**Observed:** kernel CI failed because a production evolution receipt selected a safety tier below/different from the derived AAP minimum floor.

**Prevention:** run the assurance audit before PR/merge and derive the selected tier/modules from the actual material change; never hand-select a lower tier to make CI pass.

### 17. Human admission / trusted-base mismatch

**Observed class:** protected/human admission checks are exact-base and exact-change bound; candidate text cannot manufacture its own approval.

**Prevention:** never fabricate or broaden human approval. Bind any real human admission to the exact PR/base/source/change set required by the trusted-base mechanism.

### 18. Blind retry of a failed workflow

**Observed pattern:** repeated runs can reproduce the same deterministic failure and create noise.

**Prevention:** inspect the failing step and typed receipt first. Retry only after an input/code/state change or when the failure is proven transient.

---

## CI result interpretation

A red workflow is not automatically a repository defect.

### Git/process defect examples

- missing/stale work intent;
- undeclared changed path;
- missing integration receipt;
- stale PR base under strict checks;
- merge conflict;
- malformed JSON/YAML;
- stale config fingerprint;
- unresolved repository reference;
- incorrect required-check assumption.

### Legitimate fail-closed Garden result examples

- AAP tier below derived floor;
- missing trusted authority/human admission;
- stale DesignEpoch/source root;
- missing Proof/Evidence/conformance obligation;
- constitutional change without required human gate;
- unknown billing/call completion that blocks further inference.

Do **not** weaken the safety gate merely to make the workflow green.

---

## Request-efficiency rules for Git work

- No repeated same-hash reads.
- No active CI/status polling loop.
- Prefer one broad authoritative read over several equivalent reads.
- Read only the failed job/step first.
- Preserve verified base/head/ruleset/check data as a checkpoint and invalidate it only on a relevant event.
- After `429 / Too Many Requests`, stop optional calls in that lane and resume from checkpoint on a later event.
- Use direct exact-ref fetches for proof; use search only for discovery.
- Do not batch independent model reviews in a way that leaks peer answers.

---

## Minimal preflight checklist

Before **every** Garden Git mutation, answer these internally:

- [ ] Which repo am I changing?
- [ ] What is current `main` SHA?
- [ ] Are the saved ruleset IDs/required check names still current?
- [ ] Which exact files/symbols/domains will change?
- [ ] Is another open PR/work intent touching the same responsibility?
- [ ] Is my work branch based on current main?
- [ ] Does my AgentWorkIntent cover the complete final diff?
- [ ] Do I need source-root/DesignEpoch binding (`garden-main`)?
- [ ] Do I need Reason/Algebra/AAP/Production receipts?
- [ ] Did changed JSON/YAML parse?
- [ ] Did relevant unit/conformance/reference-closure/config-surface tests pass locally/CI?
- [ ] If replacing a PR, is the old PR closed before the replacement becomes concurrent?
- [ ] Immediately before merge, is main still the same base?
- [ ] Are the exact required checks green for the current composition?
- [ ] Am I avoiding force push, bypass, fabricated approval, and blind retries?

If any answer required for safe mutation is unknown, resolve that item before writing or fail closed.
