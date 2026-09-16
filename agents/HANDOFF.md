# Garden Agent Handoff v1

Every automated reviewer output must conform to this shape. A missing `search_trace` makes the finding inadmissible for synthesis. Reviewer/model/provider selection is additionally constrained by `agents/provider-exclusion-policy.json`.

```json
{
  "schema": "GardenAgentHandoff/v1",
  "agent": "provider/model",
  "agent_family": "deepseek|qwen|llama|mistral|glm|gemma|cohere|dots|inkling|gemini|other",
  "role": "adversary|formal|implementation|grounding|open_weight_baseline|compliance|manager",
  "task_id": "...",
  "status": "NO_CHANGE|PROPOSED|BLOCKER|NEEDS_CROSS_REFERENCE",
  "claim": "...",
  "evidence_or_failure": "...",
  "severity": "INFO|LOW|MEDIUM|HIGH|CRITICAL",
  "affected_invariant": "...",
  "proposed_fix": "...",
  "test": "...",
  "uncertainty": "...",
  "what_would_overturn": "...",
  "search_trace": [
    {
      "source": "file or work-package identity",
      "query_or_scope": "what was actually inspected",
      "coverage": "FULL|BOUNDED|PARTIAL"
    }
  ]
}
```

## Admission boundary

- `search_trace` is mandatory.
- `PROPOSED` does not mean accepted.
- A model may not claim a mechanism is absent from Garden unless a later whole-corpus cross-reference supports that claim.
- Automated agents never write to `agents/shared/`.
- Model agreement is not proof.
- Excluded vendors/models/providers are not valid reviewer identities even if a handoff is otherwise structurally valid.
- A finding must survive deterministic/schema checks, whole-source cross-reference, applicable tests/evidence, and the repository's human/release admission process before becoming a Garden design change.
