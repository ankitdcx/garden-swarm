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

Execution limits and lifetime-versus-daily budget scope are defined only in [openrouter-paid-review-policy.json](openrouter-paid-review-policy.json). Family counts describe review-cycle diversity, not a per-dispatch call allowance. The Coordinator is paused. Legacy batch workers are blocked until the shared quota ledger and incremental dispatch path are qualified.

## Durable state

- `inbox/` — bounded task definitions checked into Git.
- `outbox/` — reserved path/schema for model findings. Hourly CI publishes run outputs as immutable GitHub Actions artifacts rather than allowing an agent to push directly to protected branches.
- `shared/` — human/release-admitted findings only. Automated workflows must never write here.
- `HANDOFF.md` — required structured finding format, including mandatory `search_trace`.

Git remains the durable design/task state. GitHub Actions artifacts preserve exact automated run receipts without granting models repository write authority.

## Hourly division of labor

The single Coordinator must accumulate independent reviews and cross-examinations over separate bounded dispatches. Findings stay proposals until the required cross-reference, quorum and independent admission checks pass. Artifact upload alone is not durable governed publication.

## Privacy

The free lane is strictly limited to already-public `garden-swarm` source. Private `garden-main`, private chats, diary material, secrets, and unpublished source must never be sent to free endpoints.
