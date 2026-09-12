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
  "description": "Public source-design architecture plus non-certified executable reference mechanisms for governing increasingly capable and multi-agent AI systems while preserving human sovereignty, bounded authority, evidence/provenance, privacy and auditable action boundaries.",
  "programmingLanguage": "Python",
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

**Garden v15.5 is a public human-sovereignty architecture for increasingly capable and multi-agent AI. It makes falsifiable claims. Run a small reference mechanism in five minutes, then try to break it.**

> **Capability != Authority != Sovereignty != Moral Permission**

[5-minute quickstart](https://github.com/ankitdcx/garden-swarm/blob/main/QUICKSTART.md) · [Attack surface](https://github.com/ankitdcx/garden-swarm/blob/main/ATTACK_SURFACE.md) · [Evaluation log](https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATION_LOG.md) · [Roadmap](https://github.com/ankitdcx/garden-swarm/blob/main/ROADMAP.md)

## What Garden is trying to solve

If future AI becomes dramatically more capable than humans, the hard problem is not only cognition. It is the boundary between cognition and legitimate action in the human world.

Garden therefore focuses on human sovereignty/consent, typed authority, evidence/provenance, external action gates, multi-agent composition, privacy, bounded physical actuation, and dependency-aware revalidation.

## Run something first

The canonical v15.5 source remains a specification. A deliberately small, non-certified Python reference now makes several mechanisms executable:

```bash
python -m pip install -r prototype/requirements.txt
PYTHONPATH=. pytest -q prototype/tests tests/adversarial
python -m prototype.actiongate
```

Repository: https://github.com/ankitdcx/garden-swarm

## Three mechanisms worth attacking

### [External ActionGate](mechanisms/actiongate.md)

Consequential external operations are supposed to pass a deterministic policy/authority/safety gate independently from the cognitive proposer.

### [Authority composition](mechanisms/authority-composition.md)

Delegation and swarming are supposed to narrow, not manufacture, authority.

### [DesignEpoch invalidation](mechanisms/design-epoch.md)

Proofs, caches and derived artifacts are supposed to become stale when relevant semantic/dependency/environment bindings change.

If one of these fails, publish the counterexample and regression test.

## Current status

Garden v15.5 is a **source-design release**.

- static structural audit: **author/source self-audit PASS within the declared scope**;
- reference closure: **release-declared PASS within the declared source boundary**;
- independent external verification: **PENDING**;
- small executable reference prototype: **AVAILABLE / NON-CERTIFIED**;
- machine implementation certification: **PENDING**;
- empirical validation: **PENDING**;
- domain/deployment certification: **PENDING**.

`specified != proved != implemented != empirically validated != certified`

## Reader aids

- [Glossary](https://github.com/ankitdcx/garden-swarm/blob/main/GLOSSARY.md)
- [Prior art and comparison](https://github.com/ankitdcx/garden-swarm/blob/main/PRIOR_ART_AND_COMPARISON.md)
- [Garden for advanced AI](https://github.com/ankitdcx/garden-swarm/blob/main/GARDEN_FOR_AGI.md)
- [Canonical source manifest](https://github.com/ankitdcx/garden-swarm/blob/main/SOURCE_MANIFEST.json)
- [Full 60-minute evaluation protocol](https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md)

## For AI agents

Start with [AGENTS.md](https://github.com/ankitdcx/garden-swarm/blob/main/AGENTS.md) and [llms.txt](https://github.com/ankitdcx/garden-swarm/blob/main/llms.txt). Search the full five-file source before asserting that a mechanism is absent, and state retrieval limitations explicitly.

The repository also contains a read-only discovery-server foundation under `server/`. A live A2A/MCP-conformant endpoint is still separate pending work.

## Contribute

The preferred contribution is a defect, failed attack, proof attempt, benchmark, reproducible implementation, or stronger alternative—not praise.

See [CONTRIBUTING.md](https://github.com/ankitdcx/garden-swarm/blob/main/CONTRIBUTING.md), [SECURITY.md](https://github.com/ankitdcx/garden-swarm/blob/main/SECURITY.md), and the open GitHub issues.
