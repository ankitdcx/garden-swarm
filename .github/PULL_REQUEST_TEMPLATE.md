## Problem / bounded work package

What exact work package, defect, gap, or implementation obligation does this PR address?

## Change

What changed?

## Evidence / tests

What reproducible evidence supports the change?

## Garden impact

- Source anchors / obligations:
- Affected invariants:
- Affected FunctionContracts:
- Rights / privacy / authority / safety impact:
- Canonical effect: NONE unless separately authorized successor work

## ChatGPT workstream isolation

For new ChatGPT work, create one bounded `chatgpt/...` branch, make only an intent-only bootstrap commit, then open this draft PR before substantial editing. Genuine semantic collisions use a fresh `integration/...` branch.

<!-- GARDEN_CHATGPT_WORKSTREAM -->
```json
{
  "schema": "GardenChatGPTWorkstreamIntent/v1",
  "workstream_id": "chatgpt:<bounded-workstream-id>",
  "work_package_id": "<bounded-work-package-id>",
  "branch": "chatgpt/<bounded-work-package>",
  "base_sha": "<40-char PR base SHA>",
  "dependency_intent_ids": [],
  "integration_strategy": "INTEGRATION_BRANCH_IF_COLLISION",
  "draft_pr_created_before_substantial_edit": true,
  "draft_opened_at": "<ISO-8601 UTC>",
  "last_activity_at": "<ISO-8601 UTC>",
  "status": "ACTIVE"
}
```

## Git preflight acknowledgement

This receipt proves bounded preflight facts/acknowledgement, not private cognition, correctness, authority, or approval.

<!-- GARDEN_GIT_PREFLIGHT_RECEIPT -->
```json
{
  "schema": "GardenGitPreflightReceipt/v1",
  "workstream_id": "chatgpt:<bounded-workstream-id>",
  "repository": "ankitdcx/garden-swarm",
  "base_sha": "<40-char PR base SHA>",
  "git_context_revision": 2,
  "git_context_source_sha256": "<sha256 of base GIT_OPERATING_CONTEXT_SOURCE.json>",
  "process_pointer": "ankitdcx/garden-main:governance/PROCESS_CURRENT.json",
  "process_version": "<current process version>",
  "verified_merge_ruleset_id": 23543047,
  "overlap_checked_open_prs": [],
  "overlap_result": "NO_MATERIAL_COLLISION_WITH_DECLARED_SCOPE",
  "created_before_substantial_edit": true,
  "authority_effect": "NONE"
}
```

## Multi-agent integration provenance

Fill this with the actual PR base SHA and the source/DesignEpoch bindings required by the work package and current Garden process.

<!-- GARDEN_AGENT_WORK_INTENT -->
```json
{
  "schema": "AgentWorkIntent/v1",
  "intent_id": "<agent>:<work-package>:<unique-id>",
  "agent_id": "<agent-id>",
  "work_package_id": "<bounded-work-package-id>",
  "base_sha": "<40-char PR base SHA>",
  "target_paths": ["<file-or-directory>"],
  "target_symbols": [],
  "semantic_domains": ["<semantic-responsibility>"],
  "affected_invariants": [],
  "affected_contracts": [],
  "intended_effect": "<bounded semantic/implementation effect>",
  "parallel_mode": "INDEPENDENT_COMPARISON"
}
```

If the integration-provenance check reports a declared collision, add a receipt after independently comparing the changes and testing the composed result.

<!-- GARDEN_INTEGRATION_RECEIPT -->
```json
{
  "schema": "IntegrationReceipt/v1",
  "current_intent_id": "<intent-id>",
  "work_package_id": "<work-package-id>",
  "base_sha": "<same base SHA>",
  "concurrent_intent_ids": [],
  "semantic_compare": "COMPATIBLE",
  "composition_evidence": [],
  "tests_after_integration": []
}
```

## Recovery, if this PR repairs a bad merge

Record whether the recovery is `REVERT` or `FORWARD_FIX`, the bad merge SHA, downstream invalidations, and why the chosen recovery is safer. Never reset or force-push `main`.

## Uncertainty / limitations

What remains unknown, FRONTIER, unproved, or not cross-referenced?

## Checklist

- [ ] I loaded the Git operating-context source, current process pointer/process file, and applicable Garden policies before routing this work.
- [ ] New ChatGPT work uses one unique branch/workstream per bounded package and an early draft PR.
- [ ] The Git preflight receipt is present and bound to the actual PR base.
- [ ] Actual changed paths are covered by the declared work intent.
- [ ] The intent is bound to the current PR base and applicable source/process bindings.
- [ ] Textual merge success is not treated as semantic compatibility.
- [ ] Concurrent semantic collisions use a fresh integration branch with explicit comparison/receipt rather than cross-editing source branches.
- [ ] Changed structured files parse; generated Git-context views match their source.
- [ ] Changed content passed central secret scanning.
- [ ] Canonical v15.5 files are not silently modified in place.
- [ ] Proposal/review/test/preflight evidence is not treated as authority or canonical promotion.
