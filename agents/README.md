# Garden Free Multi-Model Review Bus

This directory defines the durable contract for Garden's automated review bus.

## Roles and diversity

The hourly free lane rotates model families rather than treating one vendor as an independent committee. Preferred families/postures:

- DeepSeek — formal/reasoning critic
- Qwen — implementation/code critic
- Llama — open-weight baseline
- Mistral — compliance/European framing
- GLM — additional reasoning / non-Western corpus diversity
- Gemma — cheap/open Google-family reviewer
- Cohere — retrieval/grounding posture
- NVIDIA Nemotron — open reasoning/orchestration baseline
- Dots / Inkling — additional open-weight reasoning baselines when free endpoints exist
- Gemini hosted — optional direct free-tier reviewer only when a separate `GEMINI_API_KEY` is configured on a billing-disabled/free-tier project

The bus uses at most **two OpenRouter free calls per scheduled hour**, so a free OpenRouter account stays at or below 48 scheduled calls/day. It refuses model IDs that are not explicitly `:free` and treats any non-zero reported inference cost as a failure.

## Durable state

- `inbox/` — bounded task definitions checked into Git.
- `outbox/` — reserved path/schema for model findings. Hourly CI publishes run outputs as immutable GitHub Actions artifacts rather than allowing an agent to push directly to protected branches.
- `shared/` — human/release-admitted findings only. Automated workflows must never write here.
- `HANDOFF.md` — required structured finding format, including mandatory `search_trace`.

Git remains the durable design/task state. GitHub Actions artifacts preserve exact automated run receipts without granting models repository write authority.

## Hourly division of labor

Each scheduled run dispatches two OpenRouter free reviewers:

1. **Design lane** — one rotating model audits one deterministic chunk of the five-file canonical v15.5 source.
2. **Executable lane** — a different rotating model audits one bounded package of prototype/server/swarm code and tests.

The next ChatGPT Garden Upgrade Loop consumes the latest run evidence, cross-references claims against the whole canonical source, and may make bounded repository improvements. It never treats model consensus as admission.

## Privacy

The free lane is strictly limited to already-public `garden-swarm` source. Private `garden-main`, private chats, diary material, secrets, and unpublished source must never be sent to free endpoints.
