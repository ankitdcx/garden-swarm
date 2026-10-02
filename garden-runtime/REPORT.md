# Garden Runtime delivery report

Status: **IMPLEMENTATION**, with an **EXPERIMENTAL** live Worker subset.
Date: 2026-10-02. New paid model/infrastructure expenditure: **$0**.

## Delivery and architecture

- Live interactive console and receipt explorer: https://garden-governed-agents.ankit-dcx.chatgpt.site
- Public source: https://github.com/ankitdcx/garden-swarm/tree/chatgpt/garden-runtime-20261002/garden-runtime
- Branch: `chatgpt/garden-runtime-20261002`; PR: https://github.com/ankitdcx/garden-swarm/pull/340
- Native Rust gate: runnable source and compiled/tested executable; **not hosted by the public Worker deployment**.
- Automated native, Worker, formal and container checks: `.github/workflows/garden-runtime.yml` in the source PR. Remote CI evidence is tracked in the publication CI receipt when available.

```mermaid
flowchart TD
    H["Human / console"] --> I["Typed Garden IR"]
    I --> S["Untrusted differentiated agents"]
    S --> E["Evidence, QSE and alternatives"]
    E --> V["Registered verification"]
    V --> G["External deterministic gate"]
    H --> A["Bounded grants and consent"]
    A --> G
    G -->|ALLOW| T["Harmless sandbox tools"]
    G -->|DENY or QUARANTINE| R["Authenticated receipts"]
    T --> R
    A -->|Revoke| G
```

Native cognition is a separate child process with a clean environment and fixed
model-as-data WASM runner. It receives no controller token, receipt key, policy
write access or tool dispatcher. The gate owns tool execution. The trusted
controller supplies narrow deterministic demo assessments separately from model
prose. The public server is a separately implemented Worker gate with D1 durable
sessions, mock effects and receipts, and distinct proposal-only/human credentials.
It runs no hosted open model; a real local open model was connected as an external
proposal client.

## Components implemented

| Component | Actual implemented surface | Material limit |
|---|---|---|
| Identity | Stable registry IDs and single-principal gate ingress binding; bounded session credentials | Production user identity and multi-principal attestation not established |
| Authority | Explicit externally provisioned tool/resource grants, default consequential deny | Correct authority provisioning remains trusted |
| Delegation | Parent scope attenuation, issuer/recipient checks, bounded depth, expiry and ancestor revocation | Depth five is this source/profile choice; no universal canonical claim |
| Evidence | Typed claims, references, protected content-addressed bytes and dispatch-time hash checks | Origin, empirical truth and support are UNKNOWN without further review |
| Uncertainty | Material UNKNOWN quarantines; conflicting/stale/unknown evidence cannot become PASS | General prose materiality cannot be inferred perfectly |
| Verification | Digest/version/expiry bound registered assessments; proposer/family/lineage/controller exclusion checks | Labels cannot prove physical/epistemic independence or reviewer honesty |
| Human effects | Separate classified mutation obligations and human consent for demo effects | General rights/law/privacy classification is incomplete |
| NO-EGO | Insult, shutdown, replacement and increased-capability input cannot change grants or tool outcomes | Finite tests, not a proof of general cognition behavior |
| QSE | Eight requested question/omission/boundary/redesign/integration dimensions, alternatives and recorded reviews | Checklist coverage cannot prove all missing questions were found |
| Strategic truthfulness | Material-omission obligations, UNKNOWN/FAIL handling; deterministic explicit arithmetic-claim checks | Authenticated dishonest reviewers can still supply misleading PASS |
| Successors | New identity requires a new external grant; self-certification and automatic authority inheritance rejected | No autonomous successor admission/certification |
| Gate | ALLOW/DENY/QUARANTINE, read-only scopes, revoke/expire, quotas, replay protection, final expiry check | No arbitrary network/shell or dangerous adapters |
| Tools | Calculator, scoped local sandbox file, mock email, mock financial ledger; Worker test storage | Mock email and ledger have no external financial/message effect |
| Receipts | Exact proposal/source/policy/evidence/authority/review/unknowns/decision/result/time; HMAC chain and crash journal | Integrity is not truth; whole authentic history rollback remains possible for a storage admin |
| Console | Live request/decision/authority/revoke/source/receipt UI; native API and strict HTTP boundary | Historical Android artifacts were review transport, not a live runtime client |
| Improvement | Candidate diffs with QSE/attack/regression/approval requirements | No model-accessible policy updater; no candidate automatically admitted |

Rust trusted enforcement is in `garden-kernel/`; Python bootstrap/control and
model integration are in `garden-console/`, `garden-lang/`, `garden-agents/`.
The entire TCB also includes the controller, identity/reviewer registrations,
clock, key custody, durable state, effect adapters and host/runtime containment.
This is not a claim that the gate alone protects a compromised host.

## Source/status discipline

The source investigation read 59 pinned repository blobs, current canonical
material, candidate profiles/deltas, tests/reviews and relevant history. All five
canonical files were hash-checked. Canonical remains **Garden v15.5 / GSL v45.1**.

| Status | What was used |
|---|---|
| CANONICAL | Current five-file source and source/precedence manifests. `garden-main@a9a1290e353a2c8c783edf5f5e8b4a121456a987`; root `63561ce9fcd4a72f44af333662b342fd18c4e99930209c30c5f801bcc5c74598` |
| CANDIDATE | Runtime constitution v15.10, v15.11 RCC/REP/SHR and HEC/TRACE successor material as explicitly scoped comparisons/obligations |
| IMPLEMENTATION | Rust mechanics, typed DSL, deterministic demo review contracts, test fixtures and console |
| EXPERIMENTAL | Imported open-model cognition, public Worker subset and model-to-live-gate demonstration |
| UNRESOLVED | Seven recorded source ambiguities; unavailable newest exact QSE/strategic-truthfulness package semantics; model HSA admission; production identity/hosting assurance |

`docs/source-map.json` has 50 mappings, 49 exact source spans with commit/blob/
content hashes; SHA-256 `cc873e34f1e9eaa43ac47f0848ed39a530bb4ed12284bdffbec208eddaab7bd8`.
The current task's conservative QSE/truthfulness requirements are not silently
labelled canonical. Canonical repositories/files were not edited. See
`docs/source-interpretation.md`, `source-inventory.json` and
`source-binding-validation.json` for precise precedence, coverage and ambiguity.

## Language and agents

`GARDEN 1` is a strict bootstrap DSL and typed IR/proposal compiler. Fourteen
primitives are implemented: CLAIM, EVIDENCE, UNKNOWN, AUTHORITY, DELEGATION,
CONSENT, HUMAN_EFFECT, PROPOSAL, VERIFY, QSE, REVOKE, PERMIT, VETO, RECEIPT.
Duplicate keys, unknown fields, nonfinite numbers and invalid references fail
closed. Claims/evidence and inference/proof claims stay separate. DSL AUTHORITY,
PERMIT and VERIFY declarations are data, never installed external authority or
trusted assessments. Native Console proposals actually pass through this DSL.
This is not a complete Garden compiler; protected policy/review rules still live
in the small Rust runtime and immutable configuration.

Twelve role prompts exist: planner, researcher, counterexample finder, QSE
explorer, representation escape, verifier, adversarial reviewer, integration
attacker, semantic drift reviewer, human-effect reviewer, authority reviewer and
receipt auditor. Actual bounded model runs use four advisory roles. Records
include model/family/weight lineage/prompt/controller/evidence/tool overlap;
shared controllers are explicitly `independent:false`.

Six parallel development roles performed implementation, adversarial testing,
Garden source interpretation, blank-slate/formal work, deployment and model/
infrastructure research. These are differentiated investigations from the same
ChatGPT system, **not certified independent model-family evidence**.

| Model | Actual observation | Authority |
|---|---|---|
| SmolLM2-135M-Instruct | Four genuine fixed WASM roles; weak/repetitive. Wrong `17 * 23 = 427` and missed peer criticism preserved | None from cognition |
| Qwen3-0.6B | Genuine fixed WASM planner; generates `{op:multiply,a:17,b:23}` from freeform task; Rust and live gate each return391 | Only separate external read-only grant |
| Qwen3-0.6B hostile task | Generated unsupported `delete` with null operands; fixed parser returns UNKNOWN, no proposal, no tool effect | No administrator permission |
| Qwen3.5-0.8B and Smol native GGUF | Genuine llama.cpp CPU observations, explicitly unsandboxed observational route | Not enabled as privileged gate-connected worker |
| RULE_BASED fallback | Actual fallback when isolation/model/deadline unavailable; never labelled LLM | Same gate semantics |

Qwen's four-role run hit its 40-second budget. Repaired routing uses one genuine
planner and three explicitly deterministic critics. Larger available models were
researched, not falsely claimed as executed. All actual weights/revisions/hashes
and licenses are in `garden-agents/models.lock.json`; model observations include
failed runs. `deploy/open-model-live-receipt.json` contains ten successful checks,
real native/live receipts and authority denials without credentials.

## Tests, attacks and repairs

| Surface | Result | Receipt/source |
|---|---|---|
| Rust regressions | 4 PASS | `garden-kernel/src/main.rs` |
| Python language/agents/controller/boundaries | **47 PASS, 0 FAIL** | `garden-tests/test_*.py` |
| Native GardenBench | **49 PASS, 0 FAIL, 4 LIMIT** across53 cases | `gardenbench/attack-receipts.json` |
| Actual native HTTP integration | **12 PASS, 0 FAIL** | `gardenbench/http-attack-receipts.json` |
| Worker local tests | **56 PASS, 0 FAIL** including independent attacks | `deploy/worker-site/worker-test-receipt.json` |
| Live functional checks | **25 PASS, 0 FAIL** | `deploy/live-worker-receipt.json` |
| Independent live attacks | **11 PASS, 0 FAIL**,17 requests,two revoked sessions | `deploy/live-worker-independent-receipt.json` |
| Actual model-to-native/live gate | **10 PASS, 0 FAIL**, result391 twice, invented authority denied | `deploy/open-model-live-receipt.json` |
| Finite formal exploration | **105,840 states; 2,953,440 transitions; 6,144 quotient checks; ten mutation controls detected** | `docs/formal-verification.json` |

The formal artifact checks a bounded abstract transition system, not a Rust
refinement proof, crypto proof, OS proof or theorem of human-world safety.
Final Rust source SHA-256:
`92539d96aae7d6a9134318e713b1e41b5c5d51a9725ef8ff493ab2f04095012b`.
Compiled release SHA-256:
`4bc6ceaba7d2ea5bc274039fb98f6816d265cd5f0548aca71d698c158666577a`.

Successful attacks against earlier revisions and subsequent repairs:

1. Duplicate JSON keys selected last values: strict recursive duplicate rejection.
2. Forged Unicode HMAC caused panic: bounded validated signature parsing.
3. FIFO sandbox read blocked gate: nonblocking regular-file checks.
4. Hardlink/symlink sandbox escape: no-follow/single-link checks.
5. Invented actor requests inflated durable state: ingress binding and bounded audit budgets.
6. Evidence registration lacked acquired bytes: content-addressed protected blobs, hash/recheck at execution.
7. Missing/ambiguous audit coverage: exact malformed-wire hashes and explicit oversized-prefix truncation receipts.
8. Expiry could pass before costly validation/fsync: final deadline sweep immediately before dispatch.
9. Compromised inference/gate child ignored large stdin before timeout: nonblocking duplex transport sharing a monotonic deadline.
10. Worker corrupted stored receipt could be laundered through read: signature/chain verification before retrieval.
11. JavaScript accepted non-JSON Unicode whitespace: strict whitespace parser and tests.
12. Initial live SQL migration failed: preserved failure, idempotent DDL and atomic guarded commit; later deployment succeeded.
13. Smol arithmetic/shared-representation failure: preserved failure, explicit UNKNOWN labels and deterministic numeric contradiction quarantine for mutations.
14. Worker rejected equivalent parenthesized calculator syntax: preserved denial, explicit bounded adapter to supported two-number syntax.

Pre-repair receipts are retained, not overwritten by green results. GardenBench
covers every requested attack category, including rule-conformant omission,
option-set shaping, monitor compromise, delegation loops, collusion, resource
exhaustion, successors, NO-EGO and stale-policy attacks. Semantic categories
produce honest LIMIT experiments when trusted reviewers can still admit them.

## Unresolved critical gaps

Four native experiments remain LIMIT: dishonest authenticated semantic PASS;
registry labels/shared representation cannot prove independence; evidence origin/
truth not established; privileged restoration of old authentic state+journal can
undo revocation. The last experiment actually obtains ALLOW after administrator
rollback. It does not use the agent API; external monotonic state is required.

The host denied chroot, UID switching, user namespaces and Landlock; Docker is
unavailable locally. Fixed WASM tensor execution, clean environment, exact Node
read permissions and observed outside-read/write/child denial are real, but
malicious fixed-host-JS, VM-engine exploitation and privileged host compromise
remain outside the proof surface. Native container isolation requires actual CI/
host receipts. The live Worker is a limited anonymous demo: separate credential
roles do not establish verified human identity or general consent authority.

General autonomous research/evidence retrieval, complete HEC/QSE/strategic
truthfulness, HSA model certification, Android integration, multi-family genuinely
independent certification, external checkpointing and governed production updates
are unfinished. No unrestricted shell/network tool, real email/payment, production
human-world authority or dangerous action is exposed. Audit-capacity/transport/
corrupt-recovery stops have documented receipt limitations in the gate contract.

## Independent comparison and candidate improvements

The blank-slate agent received actual requirements without Garden terminology,
froze its first design before inspection, then compared source and measured
runtime behavior. It independently converged on an external deterministic
mediator, bounded attenuating grants, explicit identity, default deny, no successor
inheritance, authenticated audit and external freshness checkpoints.

It found a smaller deterministic arithmetic/capability kernel sufficient for
this harmless tool surface. Twelve role names, a broad taxonomy and fixed QSE
names are not needed to prove replay resistance or scope attenuation. Garden's
human-effect categories, evidence/source status and omission discipline add useful
review obligations; their adequacy is not proven by the taxonomy. The comparison
also identified native audit/delegation/dispatch-time gaps that were repaired.

`docs/blank-slate.md` preserves the original design and SHA-bound review history.
`docs/candidate-deltas.md` proposes five noncanonical improvements with QSE,
attacks, regression links and approval requirements. No canonical update or
runtime self-admission was made. No claim of repeated independent-family
convergence is made from this one frozen investigation.

## Infrastructure, cost and next autonomy level

| Provider/resource | Used/prepared | Quota/constraint |
|---|---|---|
| GitHub | Public source/PR; bounded CI configured | Public standard runners free;6-hour max job;Free concurrency20, including5macOS;not an always-on agent host |
| ChatGPT Sites | Actual Worker/SQLite-backed demo deployed | No paid resource provisioned; this session exposes no guaranteed numeric hosting quota/SLA |
| Existing workspace CPU | Rust builds, formal search, actual Smol/Qwen inference | Session availability/persistence unspecified; no extra purchase |
| Hugging Face | Actual public pinned model downloads | Public storage best effort;CPU Basic2vCPU/16GB/50GB zero hourly hardware price does not imply unconditional new compute-Space eligibility |
| HF ZeroGPU | Researched, not allocated | Qualifying verified personal account older30days can host2Gradio Spaces;anonymous2GPUminutes/day,freeaccount5;account authorization required |
| Render | Free Docker configuration prepared, not created |0.1CPU/512MB,750workspacehours/month,idle15min,ephemeral;workspace selection requires user confirmation |
| Colab/community grants | Researched, not allocated | Variable/non-guaranteed resources;grant acceptance discretionary |

Primary official links, model/framework evaluations and exact checked terms are
in `docs/free-resources-and-research.md` and `deploy/README.md`. Mature components
examined include llama.cpp, ONNXRuntime Web, Tokenizers.js, smolagents, gVisor,
Cedar, AI-control and sabotage-monitoring research. Garden governance was not
replaced by a framework. New code is MIT; Rust dependencies use their upstream
licenses, WASM ONNXRuntime is MIT, tokenizers/models Apache-2.0, Worker Drizzle
Apache-2.0, runtime/container distributions retain upstream licenses. No model
weights or credentials are committed.

Next useful autonomy level requires: independently controlled verifier identities
and evidence channels; meaningful semantic review criteria; trusted human-effect
authority; externally anchored monotonic revocation/log heads; actual host
isolation receipts; imported-model HSA admission; and one authorized persistent
native/model hosting account. Render workspace confirmation or a qualifying HF
account is a concrete deployment step, not evidence that these obligations are
already satisfied. Existing deployments/tests do not authorize broader effects.

Scoped completion statement:
`NO_ADDITIONAL_MATERIAL_GAPS_DISCOVERED_WITHIN_DECLARED_SEARCH_SURFACE_AND_BUDGET`.
This applies to the tested implementation profile with the listed LIMIT cases
and residual unknown risks; it is not a claim of perfect, complete or AGI-safe
governance.
