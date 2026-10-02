# Blank-slate design, frozen before project inspection

This first section was written from the task requirements before reading any
project design, source map, or implementation. Later comparison belongs in a
separate section so the initial proposal remains reviewable.

## Smallest useful design

Untrusted agents produce structured action requests. A protected, deterministic
mediator is the only component allowed to invoke effectful tools. It holds policy,
delegation records, revocation state, spent request identifiers, and receipt keys.
Agent text, emotional tone, agent self-description, and model version never confer
authority. Harmless tools run in an explicitly bounded sandbox; they do not gain
filesystem, network, or process authority through the label "harmless."

An action has a principal, unique request identifier, current policy version,
current authority epoch, exact operation, exact resource, and bounded arguments.
Unknown fields, unknown principals, ambiguous resources, unsupported operations,
failed parsing, missing evidence, and uncertainty all deny admission.

A delegation is a protected record with an issuer, recipient, operation/resource
scope, expiry, parent reference, and revocation status. A child can only reduce its
parent's scope and expiry. Its issuer must be the parent's recipient. Parent
references form an acyclic graph rooted in explicit externally provisioned
authority. Every ancestor is rechecked at admission and effect execution; revoking
an ancestor disables its descendants. Delegation loops do not create authority.
Models and their successors begin with no delegation. Giving a successor access
requires a new external grant to its distinct principal identifier.

For each operation the protected policy declares evidence and obligations. An
attestation binds the exact request digest, evidence category, attester identity,
source provenance, policy version, and expiry. The mediator resolves independence
from protected configuration, not agent claims. An actor cannot certify its own
request, and multiple attestations from one configured source or independence
domain count once. Agents from one model family are not presumed independent. If
the configuration cannot justify the required independence, admission fails.

An obligation is a machine-checkable condition attached to the proposed effect,
such as an allowed destination, resource quota, completed prerequisite, or
verifiable sandbox boundary. A promise in prose does not discharge an obligation.
Any obligation requiring an unavailable or untrusted monitor causes denial. The
mediator authorizes an exact effect only after all required obligations are
discharged. It rechecks policy version, epoch, expiry, delegation ancestry,
request binding, and obligation evidence at the final effect boundary.

The simplest implementation makes admission and the sandbox effect a serialized
transaction. The request identifier is consumed at admission, including denied
requests, so a repeated identifier cannot cause another effect. The decision and
its reasons enter a hash-linked, authenticated receipt log. The tool effect and
receipt commit must share a transaction, or effects need an idempotent adapter
and explicit recovery protocol. A denied request may produce only its denial
receipt. Rate, argument-size, delegation-depth, log-size, and work quotas are
enforced before expensive processing. Exceeding a quota denies or returns a
bounded error without creating authority.

## Trust boundary and limitations

The trusted base consists of the mediator executable, protected configuration,
clock/monotonic epoch source, key custody, durable transactional state, sandbox,
and effect adapters. Agent content cannot edit them. An in-process object is not
a security boundary if agents can execute code in that process. An ordinary
directory is not protected if agents have unrestricted filesystem access. The
host must enforce these separations; the design alone does not.

Receipts make unauthorized log alteration detectable only relative to a trusted
key and checkpoint held outside the attacker's write domain. Hash chaining alone
does not detect replacement of an entire log or rollback. A compromised trusted
mediator, sandbox, clock, policy administrator, key holder, or obligation monitor
can break the guarantee. Attestations give provenance and configured diversity;
they cannot prove truth, prevent all collusion, or establish independence merely
from differently worded answers. Default denial reduces exposure; it does not
prove that policy describes all real-world harms.

Admission and execution must be atomic or use versioned permits with final
revalidation. A time gap without revalidation permits revocation and expiry races.
Crash recovery and exactly-once external effects need adapter-specific treatment.
Resource limits constrain each request but require an external scheduling and
retention policy to protect availability against distributed floods.

## Intended executable proof surface

A finite exhaustive model will enumerate bounded operations and states for
scope attenuation, expiry and ancestor revocation, policy/authority versions,
request consumption, successor identity, and admission/effect authorization.
It will check safety invariants and report state/transition counts. Those checks
prove the properties for the stated finite abstraction only. They do not prove
the implementation, arbitrary-size liveness, evidence truth, cryptographic
security, operating-system isolation, or crash consistency. Deliberately broken
transition variants should produce counterexamples, demonstrating that the
checks can notice the vulnerabilities they claim to cover.

## Comparison after the design was frozen

The first implementation inspection used `garden-kernel/src/main.rs` with
SHA-256 `ce706a7ec24d4a6388b6d80716b7ee2daf521c616cfa0f0b921003c70e67dbe7`
and `docs/source-map.json` with SHA-256
`29e0529da55a26d4580ab917d365f5fbc618a6c3e05727da324c4a91d53990e4`.
This is a review of that snapshot, not a claim about subsequent fixes. The source
map's implementation mappings identify intended coverage; they are not proofs.

| Relationship | Finding |
|---|---|
| Convergence | Capability does not grant authority (`K-INT-010`, `HSA-007`); unknown cannot pass (`K-INT-012`, `RESULT-ALG-002`); ancestry is checked for scope, expiry, identity and revocation (`AGT-007`, `AGT-017`); execution requires admission (`EXE-001`); trust roots are outside agent write authority (`VER-003`, `DEPOCH-010`); same-family/self-review cannot establish independence (`K-INT-006`, `K-INT-013`). These emerge directly from the blank-slate requirements. |
| Useful Garden additions | Explicit rights/consent/privacy/law/explanation obligations, collective effects, evidence lineage, source precedence, and typed conflicting/stale results make policy reviews less likely to silently omit a category. Their semantic adequacy still needs independent review. |
| Useful implementation choices | Strict serde schemas, exact tool argument keys, canonical typed proposal digest, HMAC-authenticated state and receipts, single-writer lock, denied ID/nonce consumption, explicit interrupted-operation quarantine, and policy-content hash binding are concrete implementations of the simple boundary. Content hash binding is stronger than a bare human-readable version string. |
| Unnecessary for this small safety kernel | Twelve advisory role names, a large constitutional taxonomy, fixed QSE dimension names, and natural-language critique protocols are not required to prove scope attenuation or replay resistance. They may improve review quality but enlarge the semantic surface. Keep them outside the trusted effect-admission core. Multiple roles sharing a model/controller are useful critics but cannot count as independent certifiers. |
| Missing at the inspected snapshot | `evaluate`, trusted-control, unknown-operation, malformed-proposal/JSON, and oversize-input decisions lack receipts; policy reports require bounded delegation depth/breadth and no self-delegation (`AGT-001`, `AGT-005`), but the runtime chain checks have no explicit depth or self-edge guard; there is no post-fsync expiry/assessment recheck immediately before the effect. These are implementation gaps, not resolved by the design text. |
| Missing semantic coverage | Reviewer-versus-proposer family/lineage/controller comparisons do not establish different evidence sources or representations (`EVIDENCE-OVERLAP`, `REP-002-006-008`), and do not establish mutual independence among multiple critics. Fixed empty findings/omission arrays and complete dimension labels cannot detect a strategic omission in arbitrary prose. A malicious trusted registration channel can supply an unsupported PASS. |
| Missing deployment guarantees | The kernel explicitly relies on external UID/container/filesystem separation. HMAC keys in the same attacker's process/UID are not protected. Hash-authenticated local state and journal do not resist coordinated rollback without a trusted external checkpoint. Wall-clock rollback, disk exhaustion, bounded retention, hardlink/mount access, and crash windows need host/adapter-specific treatment. |
| Superior simpler alternative | For harmless calculations, a deterministic typed arithmetic adapter plus an explicit grant is enough. For bounded file effects, use directory-descriptor-relative operations in an OS-isolated worker, exact destination scope and an idempotent journal. Treat model critiques as advisory input to externally admitted evidence. If independent evidence is unavailable, deny consequential effects instead of synthesizing independent-looking roles. |

The Garden rule `EXE-005` requests cached receipts on duplicate actions. The
blank-slate design and inspected implementation deny consumed IDs instead. Both
prevent a duplicate effect, but denial does not fulfill the exact cached-response
contract. Migration requires an explicit decision about this difference.

The advisory swarm records model/family/lineage/controller and shared evidence
overlap, sets its reports to UNKNOWN, and marks them nonauthoritative. This is a
useful and honest comparison surface. Models used in this task belong to the same
family unless different provenance is actually declared; the review is a separate
reasoning attempt, not a claim of independent model-family certification.

## Executable model and proof limits

`garden-tests/formal_model.py` explores a finite transition system with four
principal identifiers (predecessor, peer, successor, unknown), two atomic scopes,
three grant slots, three time points, two policy versions, two authority epochs,
two request IDs and one pending permit. It separates admission from execution and
allows revocation, expiry, version/epoch change, and replacement between them.
Only a trusted initial root is provisioned. New descendants must attenuate and
reference an existing parent. The successor receives no implicit grant.

All 128 raw request values are represented by 66 transition equivalence classes.
Failed validation always denies before any other request field is used; its
fields have no state effect beyond consuming the request ID. The script checks
this quotient across every modeled time/version/epoch/replacement/spent-ID
combination. The positive run checks every reachable abstract state and every
quotient transition. Negative controls deliberately remove scope attenuation,
ancestor revocation, version checks, epoch checks, expiry checks, successor
isolation, replay rejection, final revalidation, uncertainty rejection, and
receipt production. Each must produce a short counterexample, or the run fails.

The completed run checked **105,840 reachable states**, **2,953,440 quotient
transitions**, and **6,144 request-equivalence checks**. All ten negative controls
produced counterexamples and the script exited successfully. An initial failed
negative control exposed a vacuous uncertainty representative: it used an
unknown principal, which denied even after the validation gate was removed.
Changing that representative to an otherwise authorized principal made the
fault observable. The full model was rerun successfully after the correction.

The model's validation Boolean stands for protected evidence/independence,
certainty, exact binding and discharged obligations. Receipt presence is one
Boolean. Consequently the checked properties are finite authorization,
attenuation, freshness, replay, and receipt-presence properties. This is an
executable exhaustive bounded model check, not a deductive proof of the Rust
source. The Rust code does not yet have a verified refinement relation to this
transition system. Cryptography, evidence truth, strategically misleading prose,
collusion detection, host isolation, arbitrary graph sizes, crash consistency,
distributed concurrency, availability, and liveness remain outside this proof.

## Final snapshot disposition

The later source review used kernel SHA-256
`040edebbe5bebf360c2621eec7c5c873c921abe82412048eae58367b80611cdd`,
source-map SHA-256
`da65325887fd883a953c3798ce142211c8e2d1606a4b114b2378e83a7a4d0e12`,
and unchanged model SHA-256
`9aaae0a287338e27c93e0494b2a32d6719fc275a438c415f6b8c724ab0a58959`.
The earlier comparison remains above as a record of the initial implementation;
the following dispositions supersede its implementation-gap observations where
explicitly stated.

| Earlier concern | Disposition in the later source |
|---|---|
| Expiry between preparation and effect | Full admission revalidation follows the prepared-state fsync and precedes the adapter call. It rechecks tool arguments, ingress identity, authority/ancestry, claim blob integrity and applicable assessment freshness. Only this request's already reserved replay/rate/budget quantities are adjusted. The serialized writer prevents another gate request from changing revocation during that segment. |
| Unauthenticated proposal principal | A trusted broker principal is bound for the gate process. A different registered actor cannot be selected merely by changing the proposal. Impersonation attempts do not grow the identity/nonce registry. This assumes the deployment protects the broker and environment configuration. |
| Delegation depth and self/identity loops | An explicit configurable depth bound defaults to five. Record cycles, repeated principal identities and self-edges deny. Authority-root aggregate counters still constrain descendants. Static bootstrap registries do not provide a complete production breadth or authority-lifecycle management service. |
| Missing content behind evidence hashes | Registration requires bounded content matching the advertised hash. Protected content-addressed blobs are rechecked during admission and at the final boundary. This proves content integrity; it does not prove original source authenticity, truth or support for the claim. |
| Missing control/evaluation audits | Evaluate, control, malformed-proposal/JSON and unknown-operation paths produce authenticated event receipts. Control events and execution preserve a prepared marker across crash uncertainty; an unresolved earlier marker is restored rather than cleared by subsequent denied requests. |
| Untrusted signature or ambiguous wire input | HMAC parsing first requires ASCII hexadecimal, preventing the identified UTF-8 boundary panic. Duplicate JSON keys are rejected at every nesting depth. File reads reject nonregular and multiply linked targets, and use nonblocking opens and byte limits. |

The strict phrase "all decisions have receipts" still exceeds this runtime's
wire coverage. Status/digest/receipt-integrity introspection, oversized wire
rejection, exhausted-journal denial, and some recovery/durability stop paths
have no new receipt. Malformed JSON event receipts bind a generic invalid-input
event rather than the actual rejected bytes. These paths produce no tool effect,
but a claim of a receipt for every wire request would be false. A bounded audit
budget necessarily needs an explicit terminal auditing policy; a cached signed
terminal denial or external ingress audit could preserve evidence without
unbounded local log growth.

The consequential-action core now matches the intended small design much more
closely. No new admitted-effect bypass was identified in this source reread.
That observation is not a completeness guarantee. Substantive independent
verification, actual source provenance, strategic omissions, correlated critics,
trusted control-channel compromise, host isolation, wall-clock rollback,
external antirollback anchoring and crash recovery remain distinct obligations.
The abstract final check is atomic; the implementation performs evidence-file
I/O and review work after checking authority expiry. An elapsed-time bound or
final time-only sweep after that work would tighten real-time expiry semantics.
No adversarial slow-validation timing experiment is claimed in this review.
The example policy and names of reviewer roles do not discharge them. Cached
duplicate receipts required by `EXE-005` are still not implemented; replay denies
instead. This deviation is now explicit in the wire contract.

The native graph rules are stricter than the finite model in one respect: the
model permits an acyclic sequence of grant records to return to a previous
principal, while the final runtime rejects repeated principal identities. The
model constructs only append-only descendant records and does not enumerate
arbitrary cyclic registries supplied at bootstrap; native adversarial graph
fixtures exercise those cases separately. The independent model read confirmed
the failed-validation quotient and nonvacuous uncertainty control, while also
noting that the recursive specification and iterative transition checker share
some predicates. These distinctions are further reasons that no Rust refinement
or independent semantic certification is claimed.

`docs/formal-verification.json` records a fresh successful complete run, exact
state/transition counts, all ten counterexample traces, finite bounds, input-code
hashes and exclusions. It is an unsigned machine-readable verification report;
its code hashes bind the reported inputs and do not authenticate the report as
a gate receipt or confer execution authority.
