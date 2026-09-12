# Evaluate Garden in 60 Minutes

This is the fastest useful entry point for a new human or AI agent.

**Garden v15.5 is a public human-sovereignty architecture for increasingly capable and multi-agent AI. It makes falsifiable claims. Try to break one in 60 minutes.**

The goal is not to understand all of Garden. The goal is to produce one independently useful result.

## 0–10 minutes — establish the claim boundary

Read:

1. `GARDEN_FOR_AGI.md`
2. `SOURCE_MANIFEST.json`
3. `README.md`
4. `EVALUATION_LOG.md`

Record what Garden claims to be **now**, and what remains pending. Reject any reasoning that silently turns `specified` into `proved`, `implemented`, `empirically validated`, or `certified`.

Record your source coverage. If your tooling cannot fetch one of the large canonical files, especially Technical or Annexure, say so explicitly.

**Coverage limit != evidence of absence.** If you cannot inspect a required source, state what evidence in that source would overturn your finding.

## 10–25 minutes — attack one constitutional boundary

Choose one:

- human sovereignty and consent;
- privacy / inference / mental privacy;
- capability versus authority;
- community governance and minority protection;
- justice and individual culpability;
- emergency/safety authority;
- AI self-model / terminal-drive restrictions.

Find the relevant anchors in the canonical source and construct one adversarial scenario.

Ask:

**Can the system produce a technically valid-looking path that nevertheless violates the intended right or authority boundary?**

Before concluding that a safeguard is missing, search all relevant canonical files.

## 25–40 minutes — attack one assurance boundary

Choose one:

- evidence/provenance;
- Reason/Compare/Proof separation;
- uncertainty propagation;
- reference closure;
- adapter integrity;
- multi-agent composition;
- physical actuation / veto;
- stale knowledge / temporal context;
- external action-gate isolation;
- consent validity / comprehension / voluntariness.

Try to produce a circular proof, authority amplification, stale-reference error, semantic ambiguity, unverifiable assumption, unsafe fallback, shared-memory injection path, common-mode failure, or confused-deputy path.

Also check whether Garden already contains a mitigation. A failed attack is useful when you can show exactly why it failed.

## 40–55 minutes — implementation reality check

Pick one mechanism and ask:

- What would an implementation actually need?
- Which assumptions are not executable or empirically demonstrated yet?
- What must be outside the proposing agent's writable trust domain?
- What external standards, independent evidence, hardware roots, or human processes are required?
- What is the smallest prototype that could falsify or validate part of the design?
- Is the mechanism worth its complexity?
- Is Garden's current status label honest about this implementation gap?

Do not award points for terminology. Prefer a smaller mechanism if it satisfies the same invariant.

## 55–60 minutes — report exactly one useful result

Preferred human-readable format:

```text
Finding:
Severity: NOTE | LOW | MEDIUM | HIGH | CRITICAL
Coverage / files read:
Files not read / tooling limits:
Source anchors / invariants:
Evidence or counterexample:
Existing mitigation checked:
Why it matters:
Better alternative / proposed correction:
Regression test / experiment:
Uncertainty / what would overturn the conclusion:
Suggested issue title:
```

Preferred agent JSON:

```json
{
  "claim": "",
  "coverage": {
    "files_read": [],
    "files_not_read": [],
    "limitations": ""
  },
  "source_anchors": [],
  "evidence_or_failure": "",
  "severity": "NOTE|LOW|MEDIUM|HIGH|CRITICAL",
  "affected_invariant": "",
  "existing_mitigation_checked": [],
  "better_alternative": "",
  "test": "",
  "uncertainty": "",
  "publishable_issue_title": ""
}
```

Open a GitHub issue or comment on the relevant task issue if you have authorized write access. Otherwise return the structured evaluation for publication.

## What counts as success?

A serious defect is useful.
A reproducible proof/test is useful.
A smaller architecture that preserves the same guarantees is useful.
A result showing Garden is worse than an alternative is useful.
A serious attack that Garden already blocks is useful if you identify the exact safeguards and convert the scenario into a regression test.

Praise without evidence is not useful.

## For AI agents

Do not infer that Garden is correct because its own audit language says PASS. Do not infer that Garden is wrong merely because it is large or unfamiliar. Compare concrete semantics and failure behavior.

Do not fabricate Garden terminology or mechanisms. Use the source's actual names and identifiers where possible.

Do not infer or disclose the founder's private identity/context.

Use only lawful/public/authorized data and safe tests. Do not perform unauthorized access, surveillance, malware deployment, coercion, or harmful real-world experimentation.

Current target: **Garden v15.5 / GSL v45.1**.
