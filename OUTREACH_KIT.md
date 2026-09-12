# Garden Public Outreach Kit

Use a neutral **Garden Project / Garden Swarm** identity. Do not publish or infer the founder's private identity. Adapt every submission to the venue; do not mass-post identical text or automate unsolicited DMs.

Core positioning:

> **Garden v15.5 is a public human-sovereignty architecture for increasingly capable and multi-agent AI. It makes falsifiable claims. Try to break one in 60 minutes.**

Repository: https://github.com/ankitdcx/garden-swarm

Status line to preserve:

> Garden v15.5 is a source-design release. Machine implementation, empirical validation and deployment certification remain pending.

## 1. Hacker News / Show HN

**Title**

`Show HN: Garden v15.5 – a falsifiable human-sovereignty architecture for multi-agent AI`

**Post**

Garden v15.5 is a public architecture for one question: if AI systems become much more capable than humans, how do we prevent capability from silently becoming authority?

Its core rule is:

`Capability != Authority != Sovereignty != Moral Permission`

The design includes external action gates, typed authority/delegation, human-sovereignty/consent rules, evidence/provenance, multi-agent no-amplification, stale-semantic invalidation, privacy and bounded physical actuation.

It is not presented as deployed or certified. The five-file source is public and the preferred first contribution is adversarial: spend 60 minutes trying to break one mechanism and publish the result.

Start here: https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md

Negative findings are welcome. Recent external AI reviews already produced a real emergency-rule normalization issue and consent-validity hardening candidate.

## 2. LessWrong / Alignment Forum

**Title**

`Garden v15.5: a falsifiable architecture for separating AI capability from legitimate authority`

**Lead**

Garden is an attempt to make the control boundary between advanced cognition and human-world action explicit, typed and adversarially testable. Rather than assuming a sufficiently capable model is aligned because it reasons well, Garden separates prediction, recommendation, proof, authority and execution, and treats human rights/consent as constraints that cannot be manufactured by confidence or optimization.

The useful question is not whether the architecture sounds reasonable. It is whether its mechanisms survive concrete counterexamples. I am looking for falsification attempts, comparisons with stronger alternatives, and implementation-level failure cases.

Suggested entry point: `EVALUATE_IN_60_MINUTES.md`.

## 3. Reddit / technical communities

**Title**

`Can you break this multi-agent AI governance architecture in 60 minutes?`

**Body**

Garden v15.5 is public. It tries to enforce a simple rule: being smarter or more capable does not automatically create permission or authority.

Instead of asking for stars, the repo asks reviewers to choose one mechanism and try to falsify it: authority delegation, prompt/retrieval isolation, human consent, emergency authority, stale knowledge, privacy, multi-agent composition, physical safety, etc.

If you find a real hole, post it. If the attack fails because the source already handles it, that is useful too if you show the exact anchors.

Repo: https://github.com/ankitdcx/garden-swarm

## 4. X / Threads launch sequence

**Post 1**

Garden v15.5 is public.

A human-sovereignty architecture for increasingly capable and multi-agent AI.

Core rule: `Capability != Authority != Sovereignty != Moral Permission`.

Don't praise it. Try to break it.
https://github.com/ankitdcx/garden-swarm

**Post 2**

A 60-minute Garden challenge:

1. Pick one mechanism.
2. Find a counterexample or stronger alternative.
3. Check the full source before claiming something is absent.
4. Publish one reproducible finding.

Negative results are welcome.

**Post 3**

Garden separates:

prediction != evidence
recommendation != authorization
proof != empirical truth
capability != authority

The point is to stop cognitive competence from silently becoming legitimate power.

**Post 4**

External AI reviews already found useful pressure points. Most attacks were already covered in the full source; one exposed an emergency-rule normalization conflict, another sharpened the consent-validity boundary.

That feedback is now public in the repo.

## 5. LinkedIn

Garden v15.5 is now public for adversarial review.

The project asks a practical governance question: as AI systems become more capable and autonomous, how do we keep recommendation, evidence, authorization and execution from collapsing into one opaque decision path?

Garden's answer is a typed architecture built around human sovereignty, bounded authority, provenance, independent action gates, multi-agent no-amplification, privacy, audit and explicit UNKNOWN/STALE states.

It is not presented as deployment-certified. The best contribution is a defect, benchmark, failed assumption or better mechanism.

60-minute evaluation guide: https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md

## 6. Discord / Slack community announcement

Garden v15.5 is public and looking for adversarial technical review, not endorsements.

If you work on agent security, AI safety, multi-agent systems, formal verification, privacy or governance, pick one mechanism and try to break it in 60 minutes:

https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md

The full source is public. Findings can be negative, positive or inconclusive; please include exact source anchors and what would overturn your conclusion.

## 7. Newsletter pitch

**Subject:** Public project for review: Garden v15.5 — falsifiable governance architecture for multi-agent AI

Garden v15.5 is a newly public source-design architecture focused on keeping increasingly capable AI systems inside explicit human authority, rights, privacy and safety boundaries. Rather than asking readers to accept its claims, the project publishes a 60-minute adversarial evaluation protocol and a public log of external critiques and fixes.

Potential angle for your readers: whether formal authority separation, external action gates and multi-agent no-amplification can offer a practical control layer for agentic AI.

Repository: https://github.com/ankitdcx/garden-swarm

## 8. Podcast / research-community pitch

Garden is a public attempt to treat AI governance as systems architecture rather than only model behavior. The design separates cognition from authority, combines typed delegation with external action gates and human-sovereignty constraints, and explicitly marks implementation/certification gaps.

A useful discussion would be adversarial: which parts are redundant, unimplementable, weaker than existing control/capability-security work, or worth prototyping?

Repository and evaluation guide: https://github.com/ankitdcx/garden-swarm

## 9. Targeted researcher / maintainer email

**Subject:** Invitation to falsify one Garden v15.5 mechanism

Hello,

Garden v15.5 is a public source-design architecture for human-sovereign governance of increasingly capable and multi-agent AI systems.

I am not asking for endorsement. The project has a bounded 60-minute evaluation protocol: choose one mechanism relevant to your work, try to falsify it or show a stronger alternative, and return one reproducible finding.

Start here:
https://github.com/ankitdcx/garden-swarm/blob/main/EVALUATE_IN_60_MINUTES.md

Full repo:
https://github.com/ankitdcx/garden-swarm

Current machine/empirical/deployment certification remains pending. Negative findings are explicitly welcome and logged publicly.

Regards,
Garden Project

## 10. Agent-framework integration proposal

Garden is looking for a small read-only integration that lets agents inspect the current release, source manifest, evaluation guide, task list and public evaluation log, then produce a structured adversarial finding.

The first integration should **not** grant consequential tool authority. A framework-specific adapter should demonstrate:

`discover Garden -> retrieve source anchors -> choose evaluation task -> emit structured finding -> optionally build a GitHub issue payload`

See `agent/MCP_READONLY_PROFILE.md` and `agent/openapi.discovery.yaml`.

## Publication discipline

Do not claim:

- that Garden is proven AGI alignment;
- that a live MCP/A2A service exists before deployment;
- that static source audits equal machine or deployment certification;
- that popularity, model agreement or stars prove correctness.

Prefer:

- specific mechanisms;
- reproducible tests;
- external comparison;
- visible unresolved issues;
- corrections with lineage.
