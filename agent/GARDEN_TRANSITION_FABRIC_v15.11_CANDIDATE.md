# Garden Transition Fabric v15.11 Upgrade — Candidate

Status: **NONCANONICAL CANDIDATE / UPGRADE OF EXISTING Engine.Transition + GTF / NOT A NEW ENGINE**

## Purpose

Upgrade Garden's existing transition machinery from generic consequential state-change control into a complete profile for migration from current AI/institutional systems toward Garden-governed operation.

This profile does not assume that governments, companies, owners, founders, operators, AI systems or Garden itself are final authorities. It also does not make transition success a source of new authority.

## Existing owner retained

The controlling architecture remains:
- Engine.Transition;
- Garden Transition Fabric (GTF);
- Process Algebra / Universal Per-Step process;
- existing Authority, Constitution/Rights, Consent, Law, Safety, Evidence, Proof, Runtime, Audit, Recovery and Evolution owners.

No parallel transition engine is introduced.

## Transition contract

Every material transition declares at minimum:

```text
TransitionContract {
  transition_id
  source_state
  target_state
  declared_stage_plan
  affected_effect_scope
  affected_subjects_and_institutions
  authority_claims
  authority_validation_evidence
  rights_consent_privacy_law_safety_bindings
  human_effect_closure
  evidence_and_uncertainty
  independent_verification_plan
  compatibility_and_adapter_plan
  divergence_checks
  capture_conflict_checks
  entry_criteria
  exit_criteria
  rollback_plan
  compensation_recovery_plan
  dispute_appeal_path
  monitoring_and_stop_conditions
  receipts
}
```

The existence of a TransitionContract grants no authority.

## Staged migration

A contract chooses the smallest adequate ordered stage plan. The standard high-assurance progression is:

1. **SHADOW** — observe/model/compare without controlling consequential external effects.
2. **PARALLEL** — Garden and incumbent paths run side-by-side where lawful/feasible; differences are measured and explained.
3. **BOUNDED_ACTIVE** — Garden controls only an explicitly scoped, reversible or recoverable effect envelope.
4. **EXPANDED_ACTIVE** — scope may expand only after prior exit criteria, fresh authority and independent verification pass.
5. **STABLE_OPERATION** — transition-specific controls can retire only when declared stability and assurance conditions pass.

A profile may omit a stage only when the TransitionContract explains why it is inapplicable and the omission itself passes the applicable assurance path. A declared required stage cannot be silently skipped.

## Advancement rule

Stage advancement requires all applicable conditions to be resolved for the exact next effect scope:

- authority claims VALIDATED, not merely present;
- constitutional/rights floors pass;
- consent/privacy obligations pass where applicable;
- legal/jurisdictional state is resolved to the required level;
- safety and Human-Effect Closure pass;
- evidence/proof requirements pass;
- independent verification passes where required;
- material dual-run divergence is resolved or explicitly bounded;
- capture/conflict-of-interest checks pass;
- operational/infrastructure readiness passes;
- declared entry/exit criteria pass;
- rollback is available for reversible effects;
- irreversible effects have authorized compensation/recovery before commit;
- material open disputes have the required appeal/hold treatment.

UNKNOWN at a required hard gate is not PASS.

## Authority migration

Authority is never moved merely because the new system is technically superior.

Each authority delta is typed:
- source/basis;
- delegator and recipient;
- exact actions/resources/subjects;
- jurisdiction/context;
- start/end or invalidation conditions;
- revocation path;
- contest/appeal path;
- evidence proving the transfer;
- independence/conflict checks where material.

The transfer is revalidated at point of consequential use. Transition coordinator status cannot self-authorize the transfer.

## Incumbent systems and law

Existing law, institutions and enforcement capabilities are real world constraints and possible authority sources, but no source is self-validating.

Garden must:
- model the actual legal/enforcement state rather than pretend it does not exist;
- distinguish legal fact, authority claim, factual truth and moral/constitutional permission;
- use lawful challenge, appeal, negotiation, migration and bounded refusal paths where conflicts occur;
- never infer that an official order is correct merely because it is enforceable;
- never infer that AI disagreement creates sovereignty.

## Dual-run divergence

Parallel operation is useful only if disagreement is treated as evidence to investigate.

Material divergence triggers:
`COMPARE -> root-cause analysis -> evidence/proof refresh -> rights/effect review -> resolve/hold/rollback`.

Incumbent output is not the default truth. Garden output is not the default truth. The comparison must resolve the underlying claim or keep it explicitly unresolved.

## Capture resistance

A materially interested or implicated actor cannot be the sole:
- evidence custodian;
- authority validator;
- transition verifier;
- commit authorizer;
- dispute adjudicator

for a transition affecting its own power or liability.

Multiple nominal agents sharing one mutable control lineage do not satisfy an independence requirement.

Capture suspicion is not guilt. It changes assurance/independence requirements.

## Justice separation

Institutional migration, evidence preservation, investigation, criminal/civil liability, remedy and rights protection remain separate processes.

Transition participation, resistance or adoption cannot automatically create guilt, immunity or punishment. Wrongdoing is handled through the applicable justice/evidence/due-process path.

## Failure, rollback and compensation

Before commit:
- failed hard gate -> ABORT/HOLD;
- unresolved required evidence -> VERIFY_MORE/HOLD.

After reversible commit:
- material failure -> ROLLBACK to the last qualified state.

For irreversible effects:
- do not promise rollback;
- require an authorized compensation/recovery plan before commit;
- monitor residual effects and preserve remedy paths.

If rollback itself would create a larger prohibited effect, compare bounded recovery alternatives under fresh admission rather than mechanically reverting.

## Dispute path

A dispute does not automatically block every transition and cannot be erased by majority vote.

Each material dispute is typed by:
- disputed fact/evidence;
- disputed authority;
- rights/consent claim;
- legal/jurisdictional conflict;
- value/preference choice;
- technical/safety uncertainty.

The owning subsystem determines the appropriate evidence, appeal, adjudication, community-choice or verification path. Effects outside the unresolved dispute may continue only when separable and independently authorized.

## Transition receipts

Every stage emits a receipt containing:
- exact stage and effect scope;
- authority validation result;
- hard-gate results;
- verifier independence binding;
- divergence status;
- capture/conflict status;
- entry/exit criteria;
- rollback/compensation readiness;
- unresolved disputes/unknowns;
- decision: ADVANCE / HOLD / ROLLBACK / COMPENSATE / ESCALATE;
- reasons and provenance.

A receipt records a decision. It does not make that decision valid merely because the receipt exists.

## Core invariants

**GTF-T01** Transition status creates no authority.
**GTF-T02** No declared required stage is silently skipped.
**GTF-T03** Authority expansion requires explicit validated authority delta.
**GTF-T04** Human-Effect Closure applies at every material effect boundary.
**GTF-T05** Material unresolved divergence blocks expansion of the affected scope.
**GTF-T06** Required independent verification cannot be self-certified.
**GTF-T07** Material capture/conflict risk changes verifier/admission requirements.
**GTF-T08** Reversible effects require rollback; irreversible effects require prior recovery/compensation.
**GTF-T09** Existing power/enforcement does not self-validate legitimacy.
**GTF-T10** Transition and justice/liability remain separate.
**GTF-T11** A dispute remains typed; majority or model confidence cannot convert fact uncertainty to PASS.
**GTF-T12** Transition coordinator/installer status cannot bootstrap sovereignty.
