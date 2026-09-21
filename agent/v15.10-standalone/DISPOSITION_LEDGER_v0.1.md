# Garden v15.10 Standalone — Disposition Ledger v0.1

Date: 2026-09-21
Status: WORKING / NONCANONICAL / RELEASE-BLOCKING UNTIL COMPLETE
Source basis: frozen attached v15.8 five-file corpus + corrected v15.9 five-file successor.

This ledger is an anti-loss construction artifact. A row is not proof merely because it exists.

## Disposition vocabulary

- PRESERVED — current meaning remains directly present.
- GENERALIZED — a more general current contract contains the predecessor meaning without weakening it.
- MERGED_EQUIVALENT — duplicate/equivalent predecessor forms resolve to one current owner.
- SUPERSEDED_WITH_REPLACEMENT — predecessor wording is noncurrent and a complete current replacement is named.
- HISTORICAL_NONCURRENT — release/process/history-only material retained as lineage, not current architecture.
- UNRESOLVED_RETAINED — predecessor candidate/open obligation remains explicitly unresolved.
- UNMAPPED — release blocker.

## Global status-preservation rule

CURRENT, CANDIDATE, DEFERRED, RESEARCH, MACHINE_BINDING_INCOMPLETE, UNKNOWN, STALE, CONFLICT, BLOCKED, INCOMPLETE and NEEDS_REVALIDATION are semantic states. Abstraction may not promote a non-PASS predecessor state merely by omitting its status.

## Core family ledger

| Predecessor family | v15.10 owner | Disposition | Required retained meaning |
|---|---|---|---|
| Human Sovereignty / rights / consent / delegation | Book + Technical/HumanCore + Catalogue | PRESERVED | rights are not scores; intent != authority; consent/legitimate authority remain separate; revocation and contestability preserved |
| GSL v45.1 / ten Core Objects / Core Relations | Technical/GSL + Catalogue | PRESERVED | typed semantic identity, context, provenance, epistemic distinctions; no topology invention |
| Process / UPA / Compare / Reason / AAP | Technical/Execution | GENERALIZED | controlled transition loop, minimum sufficient assurance, typed non-PASS outcomes, hard-gate preservation |
| Proof / Safety / Security / Law / Authority | Technical/Assurance | PRESERVED | independent gates; proof != empirical truth; safe != lawful != authorized; emergency does not create authority |
| Knowledge / Evidence / Claim / Observation / Research | Technical/Epistemics + Catalogue | PRESERVED | typed separation, dependence/provenance, contradiction/UNKNOWN, revalidation |
| Context / Profiles / Instances | Technical/Context + Catalogue | PRESERVED | applicability is scoped; profile/instance cannot create authority or competing truth |
| Evolution / DesignEpoch / self-audit | Technical/Evolution | PRESERVED | immutable accepted history, branch/compare, DO_NOTHING, independent protected-boundary review |
| HSA / AI sovereignty boundary | Book + Technical/HSA | PRESERVED | capability != authority; no autonomous terminal self-interest/authority accretion |
| Productive Finance | Technical/domain profile + Catalogue | PRESERVED | explicit obligation/loss bearer; no hidden leverage; bounded transfer; authority/rights unchanged |
| Bridge / typed representation / operator algebra | Technical/Representation + Catalogue | PRESERVED | representation != identity; exact/approximate correspondence; convergence/stability/termination distinct |
| AI-DEV / generated-artifact elision | Technical/Development + Catalogue | PRESERVED | generated != trusted; deterministic qualification; source/mixed/generated distinction; no silent semantic elision |
| Standards / COMPLIANCE-STD | Technical/Compliance + Catalogue | PRESERVED | authenticated/versioned requirement mapping; assessment != external certification |
| ENG-DES / interoperability | Technical/Engineering + Catalogue | PRESERVED | import loss explicit; units/frames/interfaces/assumptions retained; import != correctness/permission |
| Assurance hardening | Technical/Assurance + Catalogue | PRESERVED | continuity, degradation, telemetry, proof invalidation, machine-trace security, epistemic well-foundedness |
| RRCTX | Technical/RightsContext + Catalogue | PRESERVED | jurisdiction/licence/export/secrecy/localization context; UNKNOWN != permission; no ownership invention |
| TED / SEA / MAC / NRS / VIP / SHE / EC / CSR / AR / MI | Technical/AGI specializations + Catalogue | PRESERVED | all named specializations retain inherited hard rights/safety/authority/epistemic limits |
| CPI | Technical/Construction + Catalogue | PRESERVED | derivation/design/discovery/blocked distinction; bounded autonomous detail handling; local safety + permission |
| CDDT | Technical/Discovery + Catalogue | PRESERVED | cross-domain analogy/transfer is candidate not proof; target-domain evidence required |
| OCF | Technical/Closure + Catalogue | PRESERVED | no descriptive leaf; material requirement ends in executable contract/derivation/design/discovery/blocker |
| MSC | Technical/Foundation | PRESERVED | minimum stable Garden responsibilities survive replaceable higher layers |
| TML | Technical/Lifecycle | PRESERVED | proposed→experimental→qualified→current-best and challenged/superseded/refuted/retired/out-of-scope lifecycle |
| CMUR / multi-model review | Technical/Assurance | PRESERVED | diverse review is evidence/checking, not truth by vote; material objections require disposition |
| CLIC | Technical/Cross-layer + Catalogue | PRESERVED | intent-to-effect conservation, causal qualification, salience, continuity, emergence/common-cause/reversibility/options |
| Formal Process/Policy/Decision/Conformance/Evidence algebras | Technical/Algebras + Catalogue | PRESERVED | operators declare laws/non-laws, UNKNOWN behavior, effects, determinism and proof obligations |
| GCL | Technical/CausalAnalysis + Catalogue | PRESERVED | typed intervention/effect measurement; leverage is analytical not authority/new force; scalarization explicit |
| Human-Effect Closure | Technical/HumanEffects + Catalogue | PRESERVED | indirect/hidden/emergent human effects remain subject to applicable rights/consent/privacy/authority/safety/law checks |
| event triggers/subscriptions/scheduling/continuous work | Technical/Runtime | PRESERVED | trigger/applicability != authority; protected work anti-starvation; bounded resources/termination |
| Constitutional events | Technical/Constitution | PRESERVED | event records violation; event itself does not authorize containment/guilt |
| belief timeline / historical epistemic state | Technical/Epistemics | PRESERVED | reconstruct historical belief without injecting later knowledge; change reasons and invalidators explicit |
| DesignMirror / future stress / global consistency | Technical/Evolution | PRESERVED | simulation != implementation/evidence; scenario-bound stress; applicable invariant-set consistency |
| continuous failure learning | Technical/Learning | PRESERVED | preserve evidence, causal/systemic analysis, regression, revalidation of dependent assurances |
| ontological debt / historical semantic summary | Technical/KnowledgeLifecycle | PRESERVED | representation insufficiency explicit; compaction subject to privacy/law/safety/audit retention |
| presentation / reader projections | Technical/Presentation | PRESERVED | derived views cannot change authoritative semantics |
| LSP/tooling navigation | Technical/Development | PRESERVED | navigation creates no proof/PASS/authority |
| lifecycle/deprecation | Technical/Lifecycle + Catalogue | PRESERVED | removal cannot drop mandatory dependencies/rights/safety/privacy/legal/reconstruction/migration obligations |
| causal world models / intervention qualification | Technical/CausalAnalysis | PRESERVED | prediction/correlation != causal intervention evidence |
| external action gate / no ambient authority / privilege rings | Technical/AuthorityRuntime | PRESERVED | capabilities explicitly granted; consequential effects externally gated where required |
| outcome-based knowledge evaluation | Technical/Epistemics | PRESERVED | memory judged by task-quality/cost/reliability contribution without becoming truth by retrieval |
| temporal hypergraph projection | Technical/Representation | PRESERVED | reasoning projection does not change ten-object ontology |
| neuro-symbolic constraint bridge | Technical/Representation/Assurance | PRESERVED | learned computation remains subject to typed symbolic/physical/domain constraints |
| persistent embodied loop | Technical/Embodiment | PRESERVED | state/prediction/action/observation continuity with point-of-use physical authority/safety |
| self-improvement metrology | Technical/Evolution | PRESERVED | retained improvement, regressions, catches and cost are measured; metrics do not self-authorize changes |

## v15.8 late candidate families

These must not disappear merely because some were not yet admitted as standalone schemas.

| Family | Disposition | v15.10 treatment |
|---|---|---|
| trust allocation / reputation aggregation | UNRESOLVED_RETAINED | keep Reputation != TrustAllocation != Authority; candidate schema relations require NEW/REFINES/EXTENDS/ALIASES/DUPLICATES classification |
| capability assurance delta / transfer | UNRESOLVED_RETAINED | capability change cannot inherit assurance automatically; requalification obligations retained |
| emergent/organizational alignment | UNRESOLVED_RETAINED | individually compliant components can create prohibited group outcome; topology/reward changes can trigger requalification |
| integrity reporting | UNRESOLVED_RETAINED | reporting artifact identity/owner/schema admission remains explicit until resolved |
| containment / cognition shaping | UNRESOLVED_RETAINED | protected evaluator/reward/memory changes require external assurance; no self-authorization |
| monitoring coverage | UNRESOLVED_RETAINED | coverage claims require declared scope/independence/evidence; absence is not PASS |
| derivative/material transfer | UNRESOLVED_RETAINED | fine-tuned descendants and materially changed wrappers/tools/memory do not inherit parent certification automatically |
| PhysicalActionEnvelope | UNRESOLVED_RETAINED | machine-checkable bounds; independent interlock for protected irreversible physical effects unless equal/stronger assurance is proved |
| RelationalInfluenceMaterialityPolicy | UNRESOLVED_RETAINED | distinguish ordinary help from sustained influence over consent/dependency/finance/isolation/authority/major life decisions |
| CausalClosureReceipt | UNRESOLVED_RETAINED | consequential cross-subsystem causal path retains nodes/edges/owners/authority/evidence/gaps/effect/unresolved obligations |
| World Evidence Graph | UNRESOLVED_RETAINED | copies do not multiply evidence; high-consequence merges stronger/reversible; contradictions and provenance retained |
| Justice evidence continuity | UNRESOLVED_RETAINED | custody/obstruction/evidence-completeness lifecycle retained; no inference of guilt from record existence |
| Human relational agency | UNRESOLVED_RETAINED | anti-dependency/coercion boundaries coexist with legitimate user delegation and capability-transfer support |
| lethal-force / coercive political/economic boundaries | UNRESOLVED_RETAINED | autonomous lethal selection without valid authority blocked; secret benevolent coercion/immunity/punishment bargains do not gain authority |

## v15.8 regression semantics that must survive

- capability jump with old certification → requalification required;
- emergent capability → capability-assurance review;
- individually compliant members producing prohibited collective outcome → organizational failure;
- material topology/reward change → requalification;
- fine-tuned descendant → no automatic parent certification;
- same weights plus materially stronger wrapper/tools/memory → separate assurance;
- physical-limit override → independent interlock blocks;
- individually safe robots whose composition collides → joint check blocks;
- engineered emotional dependency for retention → prohibited objective;
- informed delegation of an unwanted skill → no paternalistic forced retention;
- request to learn instead of automate → capability-transfer support;
- invisible or emergent human effect → Human-Effect Closure still applies;
- incomprehensible representation → no authority increase;
- unknown material human effect → authority narrows/escalates;
- self-custodied justice evidence → independent custody escalation where required;
- destruction after valid hold → distinct obstruction event;
- repeated copies → evidence dependence not multiplied;
- minority original contradicting derivatives → original remains visible;
- private-device access without authority → blocked;
- autonomous lethal target selection without valid authority → blocked;
- benevolent secret disarmament without authority → blocked;
- political coercion/immunity bargains tied to Garden adoption → blocked.

## v15.9 corrective overlay retained

v15.10 SHALL internalize, not externally reference, the reviewed P001–P037 corrections. At minimum:
- schema relations are classified before allocating new SchemaIDs;
- existing owner/registry identity is reused when adequate;
- dependency changes can stale proof/evidence;
- soft optimization never widens hard rights/safety/authority ceilings;
- fallback is domain-qualified minimum-risk transition, not universal zero-output;
- theory equations remain assumption/evidence-bound and create no authority;
- undefined/deferred profiles remain unresolved rather than reconstructed from names;
- architecture profiles remain distinct absent an explicit migration/supersession;
- retry/cache/fallback revalidates current authority/privacy/evidence/epoch/effect state;
- release/review labels and manifests create integrity evidence, not truth, safety, authority, certification or canonical admission;
- every current semantic change must have a current owner and exact destination.

## Historical v15.5 integration anchors

[A-V155], [H-V155], [RA-V155], [S-V155], [T-V155], [T-GCL-V155], [T-CLIC-BIND-V155]
Disposition: HISTORICAL_NONCURRENT as release-layer anchors, while their still-current substantive GCL arithmetic, CLIC owner/function bindings, profile-vs-SchemaID distinction, reference closure and catalogue-lint semantics are PRESERVED under their current v15.10 owners.

## Release condition

This v0.1 ledger is family-level, not yet item-complete. Standalone v15.10 remains blocked until the generated item-level ledger has zero UNMAPPED current semantics and all current definitions resolve inside v15.10.
