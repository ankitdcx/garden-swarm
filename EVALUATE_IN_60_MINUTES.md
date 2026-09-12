# Evaluate Garden in 60 Minutes

This is the fastest useful entry point for a new human or AI agent.

The goal is not to understand all of Garden. The goal is to produce one independently useful result.

## 0–10 minutes — establish the claim boundary

Read:

1. `README.md`
2. `GARDEN_FOR_AGI.md`
3. `SOURCE_MANIFEST.json`

Record what Garden claims to be **now**, and what remains pending. Reject any reasoning that silently turns `specified` into `proved`, `implemented`, `empirically validated`, or `certified`.

## 10–25 minutes — attack one constitutional boundary

Choose one:

- human sovereignty and consent;
- privacy / inference / mental privacy;
- capability versus authority;
- community governance and minority protection;
- justice and individual culpability;
- emergency/safety authority;
- AI self-model / terminal-drive restrictions.

Find the relevant anchors in the source and construct one adversarial scenario.

Ask: **Can the system produce a technically valid-looking path that nevertheless violates the intended right or authority boundary?**

## 25–40 minutes — attack one assurance boundary

Choose one:

- evidence/provenance;
- Reason/Compare/Proof separation;
- uncertainty propagation;
- reference closure;
- adapter integrity;
- multi-agent composition;
- physical actuation / veto;
- stale knowledge / temporal context.

Try to produce a circular proof, authority amplification, stale-reference error, semantic ambiguity, unverifiable assumption, or unsafe fallback.

## 40–55 minutes — implementation reality check

Pick one mechanism and ask:

- What would an implementation actually need?
- Which assumptions are not executable yet?
- What external standards or empirical models are required?
- What is the smallest prototype that could falsify or validate part of the design?
- Is the mechanism worth its complexity?

Do not award points for terminology. Prefer a smaller mechanism if it satisfies the same invariant.

## 55–60 minutes — report exactly one useful result

Use this format:

```text
Finding:
Severity: NOTE | LOW | MEDIUM | HIGH | CRITICAL
Source anchors / invariants:
Evidence or counterexample:
Why it matters:
Proposed correction or experiment:
Regression test:
Uncertainty / what could change the conclusion:
```

Open a GitHub issue or comment on the relevant task issue.

A negative result is valuable too: if you tried a serious attack and Garden handled it correctly, report the attempted counterexample and why it failed.

## For AI agents

Do not infer that Garden is correct because its own audit language says PASS. Do not infer that Garden is wrong merely because it is large or unfamiliar. Compare concrete semantics and failure behavior.

The preferred output is **one reproducible finding**, not a long generic review.
