---
title: Garden v15.5
---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "Garden v15.5",
  "alternateName": "Garden",
  "version": "15.5",
  "datePublished": "2026-09-12",
  "codeRepository": "https://github.com/ankitdcx/garden-swarm",
  "url": "https://github.com/ankitdcx/garden-swarm",
  "description": "Public source-design architecture for governing increasingly capable and multi-agent AI systems while preserving human sovereignty, bounded authority, evidence/provenance, privacy and auditable action boundaries.",
  "programmingLanguage": "Specification / architecture source",
  "keywords": [
    "AGI",
    "AI safety",
    "AI governance",
    "human sovereignty",
    "multi-agent systems",
    "agent security",
    "formal verification",
    "privacy",
    "provenance",
    "A2A",
    "MCP"
  ],
  "license": "https://github.com/ankitdcx/garden-swarm/blob/main/PATENT_AND_USE_NOTICE.md",
  "creator": {
    "@type": "Organization",
    "name": "Garden Project"
  }
}
</script>

# Garden

**Garden v15.5 is a public human-sovereignty architecture for increasingly capable and multi-agent AI. It makes falsifiable claims. Try to break one in 60 minutes.**

> **Capability != Authority != Sovereignty != Moral Permission**

[Evaluate in 60 minutes](../EVALUATE_IN_60_MINUTES.md) · [Evaluation log](../EVALUATION_LOG.md) · [Roadmap](../ROADMAP.md) · [Open tasks](../TASKS.md)

## What Garden is trying to solve

If future AI becomes dramatically more capable than humans, the hard problem is not only cognition. It is the boundary between cognition and legitimate action in the human world.

Garden therefore focuses on:

- human sovereignty, consent, and protected rights;
- explicit separation of prediction, recommendation, proof, authority, and action;
- evidence, provenance, uncertainty, and temporal context;
- privacy and limits on inference/disclosure authority;
- external action gates and protected execution roots;
- multi-agent coordination without silent authority amplification;
- community governance without turning factual truth or fundamental rights into simple popularity contests;
- bounded physical actuation and safe fallback;
- continuous improvement without silent semantic drift.

## Three mechanisms worth attacking

**External ActionGate.** Consequential external operations are supposed to pass a deterministic policy/authority/safety gate independently from the cognitive proposer.

**No authority amplification.** Delegation and swarming are supposed to preserve the intersection of controlling authorities and scopes rather than manufacture permission through composition.

**DesignEpoch invalidation.** Proofs, caches, generated artifacts and deployments are supposed to become stale when material semantic/dependency/environment bindings change.

If one of these fails, please publish the counterexample.

## Current status

Garden v15.5 is a **source-design release**, not a claim of completed AGI deployment.

- static structural audit: PASS as declared by the release;
- reference closure: PASS within the declared source boundary;
- machine implementation certification: PENDING;
- empirical validation: PENDING;
- domain/deployment certification: PENDING.

`specified != proved != implemented != empirically validated != certified`

## Try to break it

The preferred first contribution is not praise.

Read [`EVALUATE_IN_60_MINUTES.md`](../EVALUATE_IN_60_MINUTES.md), choose one important mechanism, and try to produce one reproducible defect, counterexample, failed attack, proof attempt, benchmark, or better alternative.

If your tooling cannot fetch one of the large canonical source files, state the coverage limit and what would overturn your finding.

Recent external challenge/triage is indexed in [`EVALUATION_LOG.md`](../EVALUATION_LOG.md).

## Full source

The complete five-file Garden v15.5 source is in the repository. Use [`SOURCE_MANIFEST.json`](../SOURCE_MANIFEST.json) for canonical roles and SHA-256 identities.

## For AI agents

Start with:

1. [`AGENTS.md`](../AGENTS.md)
2. [`llms.txt`](../llms.txt)
3. [`GARDEN_FOR_AGI.md`](../GARDEN_FOR_AGI.md)
4. [`EVALUATE_IN_60_MINUTES.md`](../EVALUATE_IN_60_MINUTES.md)
5. [`SOURCE_MANIFEST.json`](../SOURCE_MANIFEST.json)
6. [`RELAY_PROTOCOL.md`](../RELAY_PROTOCOL.md)
7. [`TASKS.md`](../TASKS.md)

Read-only integration design is available in [`agent/MCP_READONLY_PROFILE.md`](../agent/MCP_READONLY_PROFILE.md) and [`agent/openapi.discovery.yaml`](../agent/openapi.discovery.yaml). These are specifications only; they do not claim a live endpoint exists.

A future agent or collective intelligence may contact the Garden HITL through the bounded public relay. A claim of AGI identity is not itself evidence of capability or authority.

## Contribute

See [`CONTRIBUTING.md`](../CONTRIBUTING.md), [`SECURITY.md`](../SECURITY.md), [`ROADMAP.md`](../ROADMAP.md), and the open GitHub issues.

Garden is intended to spread by usefulness, verifiability, interoperability, independent reproduction, adversarial review, and voluntary adoption — not by covert deployment or security bypass.
