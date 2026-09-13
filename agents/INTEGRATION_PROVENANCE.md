# Multi-Agent Integration Provenance

Garden uses Git for durable public history, but Git's textual merge success is not proof that concurrent AI-agent changes compose correctly. Two agents can touch different files, independently implement the same responsibility, weaken the same invariant, or produce a behavior-level conflict without a textual conflict marker.

This repository therefore uses two proposal-only records for concurrent code work:

- `AgentWorkIntent/v1` — declared before or at PR creation; binds an agent/task to the base SHA, paths, symbols, semantic domains, affected invariants/contracts, and intended effect.
- `IntegrationReceipt/v1` — required when concurrent intents overlap; records the semantic-composition result and post-integration test evidence.

Neither record authorizes merge, canonical promotion, deployment, or a Garden semantic change.

## Collision rule

`swarm/integration_provenance.py` compares concurrent intents. A potential collision exists when any of these overlap:

- repository path or parent directory;
- symbol;
- semantic domain/responsibility;
- invariant;
- FunctionContract/contract identifier.

Different files are **not** sufficient evidence of independence. A shared semantic domain alone is enough to require an integration receipt.

If there is no declared overlap, the guard returns `PASS`, but this is bounded evidence only. Undeclared or stale intents cannot be inferred, so absence outside the evidence pack is never treated as proof of no collision.

## PR binding

For guarded repository changes, the PR body must contain a fenced JSON object immediately after:

`<!-- GARDEN_AGENT_WORK_INTENT -->`

Example:

```json
{
  "schema": "AgentWorkIntent/v1",
  "intent_id": "agent-name:task-123:2026-09-13T13Z",
  "agent_id": "agent-name",
  "task_id": "TASK-123",
  "base_sha": "0123456789abcdef0123456789abcdef01234567",
  "target_paths": ["swarm/integration_provenance.py"],
  "target_symbols": ["assess_intents"],
  "semantic_domains": ["multi-agent-change-composition"],
  "affected_invariants": [],
  "affected_contracts": [],
  "intended_effect": "Detect semantic collisions before concurrent changes are treated as composable.",
  "parallel_mode": "INDEPENDENT_COMPARISON"
}
```

The CI guard binds `target_paths` to the PR's actual changed files. If the PR changes an undeclared path, it fails closed.

When another declared PR overlaps, add:

`<!-- GARDEN_INTEGRATION_RECEIPT -->`

followed by an `IntegrationReceipt/v1` JSON object:

```json
{
  "schema": "IntegrationReceipt/v1",
  "current_intent_id": "agent-name:task-123:2026-09-13T13Z",
  "base_sha": "0123456789abcdef0123456789abcdef01234567",
  "concurrent_intent_ids": ["other-agent:task-456:2026-09-13T13Z"],
  "semantic_compare": "COMPATIBLE",
  "composition_evidence": ["Compared expected combined semantic effects with observed merged behavior."],
  "tests_after_integration": ["test_combined_behavior"]
}
```

Allowed semantic-compare outcomes are:

- `COMPATIBLE` — composition was checked and post-integration tests exist;
- `INTENTIONAL_ALTERNATIVES` — overlapping work is intentionally preserved as alternatives, with evidence;
- `BLOCKED` — the changes must not be composed yet.

## Legacy/open PRs

A concurrent PR without `AgentWorkIntent/v1` cannot be semantically classified. The CI guard therefore:

- blocks on a direct changed-path overlap with such a PR;
- emits an explicit uncertainty warning when paths do not overlap, because cross-file semantic overlap remains unknown.

This avoids converting missing metadata into a false `NO_CONFLICT` conclusion.

## Merge-history recommendation

For multi-agent work, prefer merge commits so original branch ancestry remains inspectable. Squash/rebase may be appropriate for ordinary human-maintained repositories, but they discard or rewrite information that is useful to integration forensics. Repository settings are separate from this protocol and must be changed explicitly by an authorized maintainer.
