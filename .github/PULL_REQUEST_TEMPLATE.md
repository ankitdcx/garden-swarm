## Problem

What concrete problem, defect, gap, experiment, or task does this PR address?

## Change

What changed?

## Evidence / tests

What evidence, proof, benchmark, reproduction, or tests support this change?

## Garden impact

- Affected anchors / invariants / contracts:
- Rights impact:
- Privacy impact:
- Authority impact:
- Safety/security impact:
- Interoperability impact:
- IP/licensing impact:

## ChatGPT workstream isolation

For new ChatGPT work, open a unique `chatgpt/...` branch and draft PR before substantial editing. One chat thread + one bounded work package = one workstream. Declare dependencies here; semantic collisions are integrated on a fresh `integration/...` branch rather than by editing another chat's branch.

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
  "status": "ACTIVE"
}
```

## Multi-agent integration provenance

For code/workflow/config/agent changes covered by the integration-provenance workflow, fill the JSON block below. `target_paths` must cover every actual changed path. Use semantic domains even when another agent is editing different files.

<!-- GARDEN_AGENT_WORK_INTENT -->
```json
{
  "schema": "AgentWorkIntent/v1",
  "intent_id": "",
  "agent_id": "",
  "task_id": "",
  "base_sha": "",
  "target_paths": [],
  "target_symbols": [],
  "semantic_domains": [],
  "affected_invariants": [],
  "affected_contracts": [],
  "intended_effect": "",
  "parallel_mode": "INDEPENDENT_COMPARISON"
}
```

If CI reports an overlapping concurrent intent, add a complete receipt here after comparing the combined semantics and tests. Otherwise leave this placeholder untouched.

<!-- GARDEN_INTEGRATION_RECEIPT -->
```json
{
  "schema": "IntegrationReceipt/v1",
  "current_intent_id": "",
  "base_sha": "",
  "concurrent_intent_ids": [],
  "semantic_compare": "BLOCKED",
  "composition_evidence": [],
  "tests_after_integration": []
}
```

## Uncertainty / limitations

What remains unknown, unproved, unimplemented, or unvalidated?

## Checklist

- [ ] New ChatGPT work uses one unique branch/workstream per bounded package and an early draft PR.
- [ ] I distinguished claims from evidence/proof/authorization.
- [ ] I did not silently change canonical v15.5 source semantics.
- [ ] I added or updated regression tests/checks where applicable.
- [ ] I declared the actual and semantic work set for guarded multi-agent changes.
- [ ] Concurrent semantic collisions use a fresh integration branch with explicit comparison/receipt rather than cross-editing source branches.
- [ ] I checked that existing workflows still trigger and pass for the changed paths.
- [ ] I did not treat textual merge success as proof of semantic compatibility.
- [ ] I did not include secrets, credentials, or unnecessary personal data.
- [ ] I read `CONTRIBUTING.md` and `PATENT_AND_USE_NOTICE.md`.
