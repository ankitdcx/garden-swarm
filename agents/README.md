# Garden Multi-Model Review Bus

This directory defines the durable operational contract for Garden's public model-review bus.

## Current OpenRouter process

Read `docs/OPENROUTER_PROCESS_V2_2026-09-19.md`.

The default paid board is five low-cost specialist families:

- DeepSeek — determinism, hidden inputs and derivation.
- Xiaomi MiMo — implementation interactions and practical failure cases.
- NVIDIA Nemotron — architecture boundaries, ownership and scalability.
- Pareto — equivalence, proof language and assurance claims.
- Mistral — serialization, ordering, state, timing and edge cases.

The normal path is five blind reviews, ChatGPT source/evidence reconciliation, deterministic repair tests, then five bit-identical final reviews only when the candidate changed. At most one five-reviewer confirmation round may follow a valid final patch.

Agreement is never Proof. One reproducible material counterexample is sufficient to block or repair.

## Provider routing

`provider-exclusion-policy.json` is fail-closed. The explicit human directive of 2026-09-19 re-authorized NVIDIA/Nemotron and Mistral for future low-cost Garden review. Anthropic/Claude remains excluded unless another explicit future human directive changes that.

This is an operational routing rule only. It does not assert wrongdoing by any provider and creates no Garden semantic authority.

## Cost posture

Deterministic checks come first. No material event means no paid call.

- default daily OpenRouter ceiling: USD 1.00;
- routine task ceiling: USD 0.25;
- per-call reservation ceiling: USD 0.05;
- maximum calls per task: 15;
- automatic expensive escalation: USD 0.

Expensive models require explicit human opt-in for a specific unresolved question.

Model-value evidence from the v15.10 campaign is recorded in `docs/OPENROUTER_MODEL_VALUE_REVIEW_2026-09-19.md`.

## Reviewer quality

`reviewer-quality-policy.json` and `reviewer-slot-registry.json` govern slot quality. Model identities are pinned. Replacement requires governed evidence; agreement with ChatGPT or peers is not a quality score.

GLM 5.3 is currently shadow-only because it produced one strong substantive answer in five campaign calls but insufficient visible-output reliability for routine quorum.

## Durable state

- `inbox/` — bounded public review tasks.
- `outbox/` — reserved finding/output path; CI artifacts preserve run evidence.
- `shared/` — human/release-admitted findings only.
- `HANDOFF.md` — structured finding handoff contract.

Unknown completion or billing fails closed. `NO_SUBSTANTIVE_OUTPUT` is not approval and is not automatically retried against an unchanged packet.

## Privacy and authority

The public lane handles already-public Garden source only. Private chats, secrets, personal data and unpublished private source must not be sent to public review endpoints.

Model outputs remain proposal evidence. They cannot create truth, Proof, authority, canonical status, merge permission or human admission.
