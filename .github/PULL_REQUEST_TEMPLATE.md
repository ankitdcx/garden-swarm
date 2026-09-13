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

- [ ] I distinguished claims from evidence/proof/authorization.
- [ ] I did not silently change canonical v15.5 source semantics.
- [ ] I added or updated regression tests/checks where applicable.
- [ ] I declared the actual and semantic work set for guarded multi-agent changes.
- [ ] I did not treat textual merge success as proof of semantic compatibility.
- [ ] I did not include secrets, credentials, or unnecessary personal data.
- [ ] I read `CONTRIBUTING.md` and `PATENT_AND_USE_NOTICE.md`.
