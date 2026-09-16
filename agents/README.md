# Garden Free Multi-Model Review Bus

This directory defines the durable contract for Garden's automated review bus.

## Provider exclusions

`provider-exclusion-policy.json` is a fail-closed human operator routing constraint for all Garden work. Anthropic/Claude, NVIDIA/Nemotron, and Mistral/Mistral AI are excluded from model selection, provider endpoints, fallbacks, reviewer/challenger assignment, and active contact. Historical references may remain for provenance but do not authorize operational use. Only an explicit future human directive may change the exclusion list.

## Event-driven quality policy

`event-driven-model-quality-policy.json` makes review quality materiality-driven rather than clock-driven.

- Unchanged/non-material state: no model call.
- Optional unresolved triage: Qwen3.7 Flash, DeepSeek V4 Flash 0731, or GLM 5.3 Flash when deterministic classification remains UNKNOWN/INCONCLUSIVE.
- Material paid board: DeepSeek V4 Pro 0813 + Qwen3.8 Max + GLM 5.3, blind before cross-examination.
- Separate Google lane: Gemini 3.8 Flash, free-tier only with no paid fallback.
- Separate ChatGPT frontier: user-selected ChatGPT model; never routed through OpenRouter and never hardcoded by this repository.

The OpenRouter daily ceiling remains $1.00. Higher-quality models are justified by fewer event-triggered calls, not by increasing the daily budget.

## Roles and diversity

The free lane rotates allowed model families rather than treating one vendor as an independent committee. Preferred allowed families/postures include:

- DeepSeek — adversarial reasoning / code
- Qwen — architecture / implementation
- Llama — open-weight baseline
- GLM — semantic/formal reasoning
- Gemma — cheap/open Google-family reviewer
- Cohere — retrieval/grounding posture
- Poolside — implementation correctness
- Dots / Inkling — additional open-weight reasoning baselines when free endpoints exist
- Gemini hosted — optional direct free-tier reviewer only when a separate `GEMINI_API_KEY` is configured on a billing-disabled/free-tier project

Execution limits and lifetime-versus-daily budget scope are defined only in [openrouter-paid-review-policy.json](openrouter-paid-review-policy.json). Family counts describe review-cycle diversity, not a per-dispatch call allowance. The Coordinator is paused. Legacy batch workers are blocked until the shared quota ledger and incremental dispatch path are qualified.

## Durable state

- `inbox/` — bounded task definitions checked into Git.
- `outbox/` — reserved path/schema for model findings. CI publishes run outputs as immutable GitHub Actions artifacts rather than allowing an agent to push directly to protected branches.
- `shared/` — human/release-admitted findings only. Automated workflows must never write here.
- `HANDOFF.md` — required structured finding format, including mandatory `search_trace`.

Git remains the durable design/task state. GitHub Actions artifacts preserve exact automated run receipts without granting models repository write authority.

## Division of labor

The single Coordinator must accumulate independent reviews and cross-examinations over separate bounded event-driven dispatches. Findings stay proposals until the required cross-reference, quorum and independent admission checks pass. Artifact upload alone is not durable governed publication.

## Privacy

The free lane is strictly limited to already-public `garden-swarm` source. Private `garden-main`, private chats, diary material, secrets, and unpublished source must never be sent to free endpoints.
