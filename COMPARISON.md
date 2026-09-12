# Garden comparison snapshot

This is a **non-authoritative discovery aid**, not a superiority claim. Re-check external projects before relying on this table; their capabilities change quickly. Detailed conceptual prior-art discussion is in [`PRIOR_ART_AND_COMPARISON.md`](PRIOR_ART_AND_COMPARISON.md).

Snapshot date: **2026-09-12**.

| Dimension | Garden v15.5 + reference prototype | Microsoft Agent Governance Toolkit | simaba/multi-agent-governance |
|---|---|---|---|
| Primary aim | Human-sovereignty / constitutional control architecture plus falsifiable reference mechanisms | Production-oriented runtime governance, identity, isolation, policy and reliability for autonomous agents | Practitioner framework for multi-agent authority, propagation, containment and accountability |
| Execution gate | External deterministic ActionGate is specified; small non-certified Python reference exists | Runtime policy interception / enforcement kernel | Authority / containment controls with runnable simulator examples |
| Delegation / composition | Explicit no-authority-amplification semantics; reference authority-envelope intersection test | Identity, trust, runtime controls and agent-to-agent governance | Explicit authority envelopes, propagation controls and escalation logic |
| Semantic staleness | DesignEpoch + dependency-aware invalidation is a first-class Garden mechanism; reference implementation exists | Not the project's primary distinguishing abstraction | Not the project's primary distinguishing abstraction |
| Signed delegation example | Ed25519-signed delegation receipt reference prototype | Cryptographic agent identity / trust features | Governance-oriented propagation/accountability model rather than Garden-style receipt prototype |
| Adversarial posture | Public `ATTACK_SURFACE.md`, evaluation protocol, regression tests and negative-result log | Large automated test/security program and production-oriented hardening | Governance scenarios, simulator and practitioner documentation |
| Machine-readable discovery | `AGENTS.md`, `llms.txt`, `SKILLS.json`, OpenAPI discovery, read-only MCP implementation | Multiple SDKs/integrations and production packages | Public docs/examples/templates |
| Implementation maturity | **NON-CERTIFIED reference prototype; machine/empirical/deployment certification pending** | Public-preview production-quality toolkit with installable packages | Runnable framework/simulator; independent maturity assessment still required |
| Languages | Python reference prototype today | Multiple language SDKs | Primarily documentation/simulator ecosystem; verify current implementation coverage upstream |
| Rights / normative scope | Explicit human-sovereignty, consent, rights, privacy, evidence/provenance and governance semantics | Runtime security/governance focus | Multi-agent authority/accountability/governance focus |

## What Garden should learn from stronger implementation ecosystems

Garden should not imitate other projects merely for feature parity. The useful lessons are concrete:

1. **Low-friction installation** — make individual mechanisms independently consumable.
2. **Cross-language adoption** — provide TypeScript next after the Python reference stabilizes.
3. **Continuous fuzzing / adversarial CI** — expand current regression tests into property/fuzz testing.
4. **Framework adapters** — integrate with LangGraph, AutoGen, CrewAI and agent SDKs without giving adapters extra authority.
5. **External evaluation** — human-authored findings, independent reimplementations and benchmark results matter more than self-description.

## What would count as evidence Garden is better on a dimension

Not a README claim. Prefer one of:

- a reproducible benchmark;
- a smaller trusted computing base for the same guarantee;
- a proof or machine-checked invariant;
- an adversarial test another approach fails and Garden passes;
- lower false-positive / false-negative rates under a declared threat model;
- simpler integration with equivalent assurance;
- an independently reproduced result.

## Current strongest differentiation to test

Garden's most distinctive claims are not that it has "an agent policy engine". Those already exist elsewhere. The higher-value hypotheses are:

- **capability, authority, sovereignty and moral permission remain explicitly distinct across the whole stack;**
- **authority cannot increase through delegation/swarming composition;**
- **semantic/design drift invalidates stale assurance through DesignEpoch/dependency binding;**
- **human-facing rights/consent/governance semantics remain separate from machine capability and optimization.**

If a stronger existing architecture already provides these properties more simply or more rigorously, Garden should adopt the stronger mechanism rather than preserve terminology.

## External projects referenced

- Microsoft Agent Governance Toolkit: https://github.com/microsoft/agent-governance-toolkit
- Multi-Agent Governance Framework: https://github.com/simaba/multi-agent-governance

No affiliation or endorsement is implied in either direction.
