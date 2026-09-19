# Single OpenRouter Review / Convergence Process

Current process: [OPENROUTER_PROCESS_V2_2026-09-19.md](OPENROUTER_PROCESS_V2_2026-09-19.md).

This file previously documented the four-family branch-reconciliation process. That process is superseded for new Garden OpenRouter work.

## Active rules

- deterministic/local checks before model calls;
- five independent cheap specialist families;
- identical blind source packet;
- no peer-answer sharing;
- no routine model-to-model or per-branch follow-up;
- ChatGPT verifies and dispositions every finding against source/tests;
- five-model final review only after a material candidate change;
- at most one five-model confirmation round after a valid final patch;
- 5-call easy path, 10-call normal changed-candidate path, 15-call absolute maximum;
- USD 0.05 per-call reservation, USD 0.25 routine task ceiling, USD 1/day default ceiling;
- no automatic expensive escalation;
- `NO_SUBSTANTIVE_OUTPUT` is recorded and not automatically retried on an unchanged packet;
- one valid material counterexample overrides any number of approvals;
- agreement is evidence, not Proof or authority.

The executable policy sources are:

- `agents/openrouter-paid-review-policy.json`
- `agents/independent-branch-convergence-policy.json`
- `agents/event-driven-model-quality-policy.json`
- `agents/reviewer-slot-registry.json`
- `agents/provider-exclusion-policy.json`

Historical four-branch receipts remain audit evidence but are not the active protocol for new work.
