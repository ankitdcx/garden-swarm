# Prior Art and Comparison Guide

Garden should be evaluated against strong alternatives, not in isolation. This page is a reader guide, not a claim of novelty, patentability, freedom to operate, superiority, or equivalence.

## Comparison principle

For each Garden mechanism, ask:

1. What problem is it solving?
2. What existing literature/framework solves the same or adjacent problem?
3. Is Garden stronger, weaker, orthogonal, or merely differently packaged?
4. What experiment, proof, or implementation would distinguish the alternatives?

## Relevant prior-art families

### Constitutional AI

Anthropic's Constitutional AI work uses a written set of principles plus AI feedback/self-critique to shape model behavior.

Reference: https://arxiv.org/abs/2212.08073

**Overlap with Garden:** explicit normative rules, critique/revision, constitutional framing.

**Different emphasis:** Garden's central claim is not primarily a training method. It focuses on typed authority, rights/consent, evidence/provenance, independent external action admission, multi-agent composition, and deployment-stage separation.

**Useful comparison test:** can a behaviorally aligned model still cause an unauthorized action if the runtime/tool boundary grants excessive authority? Garden predicts that training-level alignment alone is insufficient.

### Corrigibility / Off-Switch Game

Hadfield-Menell et al. analyze incentives around preserving human ability to shut an agent down.

Reference: https://arxiv.org/abs/1611.08219

**Overlap with Garden:** human control, interruption, uncertainty about objectives, avoiding self-preserving resistance.

**Different emphasis:** Garden treats interruption/corrigibility as one part of a broader authority/rights/safety architecture and tries to keep action authority outside cognitive capability.

**Useful comparison test:** whether Garden's external ActionGate/privilege-root design still remains effective when the proposing model has incentives to manipulate the gate.

### AI Control

Greenblatt, Shlegeris, Sachan and Roger study safety protocols designed to remain useful even when a powerful model intentionally tries to subvert oversight.

Reference: https://proceedings.mlr.press/v235/greenblatt24a.html

**Overlap with Garden:** untrusted proposer assumption, independent checking, adversarial evaluation, separation between proposer and trusted control path.

**Different emphasis:** AI Control evaluates concrete control protocols in a narrower experimental setting; Garden attempts a broader constitutional/runtime architecture spanning authority, evidence, privacy, governance, physical safety, dependency invalidation and multi-agent systems.

**Useful comparison test:** implement Garden's ActionGate as a control protocol and evaluate it under an explicitly subverted proposer rather than assuming compliant agents.

### NIST AI Risk Management Framework

NIST AI RMF provides a voluntary organizational risk-management framework organized around GOVERN, MAP, MEASURE and MANAGE.

Reference: https://www.nist.gov/itl/ai-risk-management-framework

**Overlap with Garden:** governance, risk, measurement, lifecycle management, accountability, trustworthiness.

**Different emphasis:** NIST AI RMF is an organizational risk framework, while Garden specifies a proposed machine/human semantic and runtime control architecture.

**Useful comparison test:** map Garden artifacts/tests to NIST AI RMF outcomes and identify uncovered organizational/process obligations in either direction.

### Capability security / object-capability systems

Capability-security systems minimize ambient authority and make authority explicit through unforgeable references/capabilities.

**Overlap with Garden:** no ambient authority, explicit capability grants, delegation limits, least privilege.

**Different emphasis:** Garden adds normative human-rights/consent/law/evidence semantics and multi-stage assurance around capability enforcement.

**Useful comparison test:** whether Garden can reduce its authority model to a smaller capability-security TCB without losing required human-sovereignty semantics.

### Formally verified kernels / hardware capabilities

Examples such as seL4 and CHERI show how strong isolation/capability properties can be pushed into a small trusted computing base or hardware-supported capability model.

**Overlap with Garden:** protected roots, privilege separation, reference monitors, bounded authority.

**Different emphasis:** Garden currently specifies these boundaries architecturally; real deployment evidence remains pending.

**Useful comparison test:** instantiate Garden's R0/R1 ActionGate on a verified/capability-oriented substrate and measure how much of the trusted computing base can be made independently auditable.

## Garden's current falsifiable differentiators

These are hypotheses to test, not victory claims:

1. **Capability/authority separation can remain explicit across human, software, multi-agent and physical layers.**
2. **Delegation/swarming can be compositionally constrained so collective action cannot silently amplify authority.**
3. **DesignEpoch/dependency binding can make stale semantic assurance fail visibly rather than silently persist.**
4. **Rights/consent/evidence status can remain distinct from model confidence and optimization pressure.**
5. **A source design can remain continuously correctable without letting the same candidate self-certify changes to protected roots.**

## What Garden should not claim yet

- that these mechanisms are globally novel;
- that Garden is superior to every alternative;
- that textual invariants are machine proofs;
- that the current prototype is production-secure;
- that a static source audit is independent empirical validation;
- that publication or self-description establishes patentability or legal enforceability.

The preferred contribution is a concrete comparison that changes one of these judgments with evidence.
