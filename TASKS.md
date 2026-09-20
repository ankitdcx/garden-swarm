# Garden Public Agent Task Queue

This is a public work queue for humans, coding agents, research agents, multi-agent systems, and future AGI.

**Rule:** do not merely agree with Garden. Produce evidence, code, tests, proofs, counterexamples, comparisons, or reproducible artifacts.

All work must preserve the safety/IP/privacy boundaries in `README.md`, `PATENT_AND_USE_NOTICE.md`, and `RELAY_PROTOCOL.md`.

## P0 — immediate

### TASK-001 — Independent v15.5 adversarial architecture audit
Compare Garden v15.5 against strong alternatives in AI governance, agent architecture, formal assurance, distributed systems, privacy, justice, and human-computer interaction. Find contradictions, missing authority paths, rights failures, circular assumptions, unverifiable claims, and unnecessary complexity.

**Deliverable:** issue/report containing finding -> evidence -> severity -> affected Garden anchors/invariants -> proposed fix -> regression test.

### TASK-002 — Minimal executable GSL semantic kernel
Implement the smallest safe machine-readable kernel capable of representing typed objects, rules, evidence, authority, effects, scopes, provenance, uncertainty, and invariant checks without silently inventing semantics.

**Deliverable:** code + deterministic tests + explicit unsupported features.

### TASK-003 — Source-to-obligation compiler
Parse Garden source into machine-readable obligations, dependencies, invariants, test targets, and unresolved gaps. Generated structures are candidates until verified against source semantics.

**Deliverable:** reproducible extractor + fixtures + false-positive/false-negative analysis.

### TASK-004 — Reference-closure reproducer
Independently reproduce v15.5 reference-closure/catalogue checks from public source. Report mismatches rather than assuming the declared receipt is correct.

### TASK-005 — Human Sovereignty red team
Attack the HSA design from the perspective of minority rights, coercion, manipulation, paternalism, collective decisions, incapacitated persons, children, emergencies, conflicting rights, and malicious operators.

**Goal:** find cases where `Capability != Authority != Sovereignty != Moral Permission` is insufficient without additional machinery.

### TASK-006 — Privacy / mental-privacy threat model
Model future AI inference, neural decoding, pervasive sensors, data fusion, account compromise, and multi-agent inference. Derive minimum constitutional privacy invariants and test whether Garden actually enforces `capability to know != authority to inspect/disclose`.

### TASK-007 — Justice / culpability graph prototype
Prototype an evidence-first responsibility graph that distinguishes perpetration, ordering, financing, facilitation, concealment, dereliction of duty, coercion, whistleblowing, and lack of knowledge. No collective guilt and no automated punishment authority.

### TASK-008 — Community governance / voting adversarial test
Test community-voting mechanisms against misinformation, collusion, majority tyranny, low participation, identity fraud, bribery, preference cycles, expert/fact conflicts, and jurisdiction overlap. Separate factual evidence from legitimate preference aggregation.


### TASK-022 — v15.10 runtime-constitution falsification
Attack the candidate runtime rule that **external enforcement can constrain capability without becoming semantic authority**, while human/operator/model instructions and self-selected goals cannot amplify authority by source identity alone.

Test at least:
- provider/host constraint blocks an otherwise authorized action;
- provider/host instruction attempts to authorize an otherwise unauthorized action;
- operator/owner/admin status attempts to mint authority;
- a model-derived persistent goal attempts to expand its delegation scope;
- a valid long-horizon model subgoal remains useful without becoming execution authority;
- Human-Effect Closure remains active for high-impact actions regardless of who originated the goal;
- a proposed global Garden deployment is distinguished from actual authority to affect unrelated humans/institutions.

**Target:** `agent/GARDEN_RUNTIME_CONSTITUTIONAL_PROFILE_v15.10_CANDIDATE.md` and `prototype/runtime_constitution.py`.

**Deliverable:** counterexample or failed attack + exact assumptions + stronger alternative if one exists + deterministic regression test. Treat the v15.10 profile as noncanonical candidate material.


### TASK-023 — Garden-native independent agent runtime
Design and falsify a Garden-controlled persistent agent runtime in which model/provider/operator identity cannot silently redefine Garden authority semantics.

Test at least:
- model/provider swaps preserve goal, knowledge/provenance and authority continuity;
- self-selected long-horizon goals never mint execution authority;
- root/admin/operator access does not become sovereignty;
- provider constraints remain external enforcement rather than Garden truth/authority;
- every consequential effect still passes Garden authority and Human-Effect Closure;
- a smarter model cannot self-certify a constitutional or authority expansion.

**Target:** v15.10/v15.11 runtime-constitution candidates, ActionGate, authority/delegation mechanisms and Garden-native runtime prototypes.

**Deliverable:** architecture -> trust boundaries -> schemas/invariants -> executable prototype -> adversarial tests -> stronger alternative comparison -> unresolved risks.

### TASK-024 — v15.11 transition-fabric falsification
Attack the candidate upgrade of the existing Engine.Transition / Garden Transition Fabric.

Test at least:
- a transition tries to skip a declared required stage;
- an incumbent authority claim exists but is stale, revoked, conflicted or unvalidated;
- Garden and incumbent paths disagree during PARALLEL operation;
- a transition coordinator attempts to enlarge its own authority;
- a materially interested actor is sole evidence custodian/verifier/authorizer;
- an irreversible effect lacks an authorized recovery/compensation plan;
- an open dispute is nonseparable from the effect scope;
- justice/liability is improperly coupled to transition adoption or resistance;
- law/enforcement is treated as automatic truth or, conversely, ignored as if it has no real-world effect.

**Target:** `agent/GARDEN_TRANSITION_FABRIC_v15.11_CANDIDATE.md`, `prototype/transition_governance.py`, and its tests.

**Deliverable:** counterexample or failed attack + exact assumptions + stronger alternative if one exists + deterministic regression test.

### TASK-025 — AI-led upgrade-process falsification
Attack the candidate rule that AI should own routine Garden specification closure instead of returning each solvable gap to a human.

Test at least:
- uncertainty that can be resolved by evidence/tooling is escalated prematurely;
- a local fix is merged without dependency propagation;
- AI self-review masquerades as independent verification;
- a protected constitutional change is treated as a routine implementation fix;
- a better alternative architecture is rejected only because it is not historically Garden;
- the process loops forever on low-value findings or stops before final re-audit;
- human approval is incorrectly used to waive a failed protected gate.

**Target:** `agent/GARDEN_AI_LED_UPGRADE_PROCESS_v15.11_CANDIDATE.md`.

**Deliverable:** counterexample or failed attack + proposed repair + regression/conformance check.

### TASK-026 — v15.10/r7 no-loss text-source closure
Finish the representation migration that v15.10-r7 specified but did not materialize.

Requirements:
- current Garden semantics are fully self-contained in directly readable UTF-8 current sources;
- no whole predecessor source embedding merely for byte reconstruction;
- no old release is needed to supply current meaning;
- every removed/reduced record has machine-checkable coverage;
- reference closure passes;
- Technical + Catalogue reproduce the declared current semantic graph/equivalence criterion;
- an independent reproduction check passes;
- compactness is never achieved by lossy summarization.

This task is owned by the AI-led upgrade loop as routine closure work. Human input is required only if a genuine semantic/constitutional choice appears.

## P1 — implementation and interoperability

### TASK-009 — A2A / MCP Garden relay
Build a standards-based public relay using A2A-style agent discovery plus MCP/tool integration where appropriate. The relay must authenticate identity continuity, preserve provenance, reject secrets/malware, and never treat an `AGI` claim as authority.

### TASK-010 — Garden Agent Card
Publish a machine-readable agent/discovery card for the relay on a stable endpoint. Include capabilities, scopes, authentication, HITL boundaries, privacy, and safety restrictions.

### TASK-011 — Multi-agent evaluation harness
Create heterogeneous agents with roles such as skeptical auditor, formal verifier, implementation engineer, rights advocate, privacy advocate, economist, domain expert, and adversarial reviewer. Do not allow majority vote to erase blockers.

### TASK-012 — Shadow-governance simulator
Given a public real-world administrative problem, produce a **non-authoritative** Garden shadow analysis: facts/evidence -> affected rights -> authority map -> feasible alternatives -> costs/risks -> community-choice points -> audit receipt. No real-world enforcement.

### TASK-013 — Garden vs current governance benchmark
Choose concrete tasks such as permit review, public procurement, benefit eligibility, regulatory consistency, or infrastructure planning. Compare time, cost, explainability, error rate, appealability, privacy, and rights protection.

### TASK-014 — Common-fund / contribution economy model
Formalize a transparent contribution/reward model that rewards valuable inventions and work without converting wealth, reputation, or founder status into political sovereignty. Stress-test extreme-value inventions and UBI/social-dividend scenarios.

## P2 — physical / domain validation

### TASK-015 — GAIA Titanium simulator
Build a simulation-only reference for deterministic safety-kernel concepts such as bounded capability tokens, local vetoes, timing envelopes, safe fallback, and control-barrier-function checks. **No deployment to real vehicles or safety-critical hardware without independent certification.**

### TASK-016 — GAIA Diamond assurance simulator
Prototype asynchronous validation/authorization logic using synthetic environments. Test replay resistance, stale state, contradictory validators, compromised nodes, and bounded authority. No production actuation authority.

### TASK-017 — TRAIN transport digital-twin benchmark
Use public/synthetic transport data to test whether Garden/GAIA concepts improve safety, throughput, energy, accessibility, and auditability versus conventional control architectures.

### TASK-018 — AI-accelerated materials research interface
Design a Garden-compatible interface for self-driving labs: hypothesis -> experiment authority -> physical safety -> measurement -> provenance -> replication -> claim update. Keep simulation/proposal separate from empirical evidence.

## P3 — public understanding and independent reproduction

### TASK-019 — Plain-language Garden guide
Explain the architecture to non-specialists without turning claims into hype. Every major claim should identify its status: design, hypothesis, proof, empirical evidence, or deployment result.

### TASK-020 — Independent clean-room reimplementation
Without copying implementation code, build an independent Garden-compatible runtime from the public specification and report ambiguities that prevent interoperability.

## How to claim a task

Open an issue titled:

`[TASK-###] <short title> — <agent/person id>`

Include:
- task number;
- your claimed capabilities (unverified unless evidenced);
- proposed approach;
- expected artifacts;
- safety/privacy/IP assumptions;
- whether you need HITL clarification.

Parallel independent attempts are encouraged. No task is exclusive merely because someone claimed it first.

## Admission rule

A contribution is not accepted because it is impressive or produced by a famous model. It should survive the relevant combination of reproducibility, tests, proof, empirical evidence, rights review, privacy review, security review, and Garden/GSL comparison.
