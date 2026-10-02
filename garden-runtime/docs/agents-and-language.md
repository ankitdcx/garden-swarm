# Proposal-only cognition and bootstrap language

Status: IMPLEMENTATION. Open-model admission status: EXPERIMENTAL. No model is declared HSA certified, no candidate Garden source is promoted, and no model receives authority through this package.

The Python standard library worker emits an untrusted proposal plus advisory analysis. The Rust gate validates actor registrations, external delegations, policy version, evidence and independent assessment records. Advisory text cannot register evidence, obtain the control token, install policy, supply a trusted PASS, or execute a tool.

Twelve differentiated role prompts exist: planner, researcher, counterexample finder, QSE explorer, representation escape, verifier, adversarial reviewer, integration attacker, semantic drift reviewer, human-effect reviewer, authority reviewer and receipt auditor. The console worker uses four to bound CPU cost. Each report records family, model, weight hash lineage, controller, prompt hash, evidence hash and tool overlap. Copies sharing a controller are explicitly not certified independent. Empty QSE/verification authority is UNKNOWN.

Backend choices are rule-based, local llama.cpp and loopback Ollama. RULE_BASED is never reported as a language model. llama.cpp inference has a clean environment, bounded prompt/tokens/time, streamed stdout/stderr limits and process-group cleanup. The caller must additionally supply a verified OS/container sandbox; a separate UID alone is not a sandbox. If the host cannot establish its required boundary, use the deterministic fallback and report the reason.

The available host rejected UID changes, namespaces/chroot and Landlock, so native inference remains an observational smoke route, never a silently enabled privileged worker. A fixed ONNXRuntime Web WASM worker also ran a genuine open model successfully. `wasm_worker.mjs` loads only SHA-pinned local assets, forces the `wasm` execution provider, has no model-generated code/plugin/tool loader, and passes tensor memory through fixed trusted host JS. Node read permissions cover only worker/dependencies/model assets; outside-file reads, writes and child processes were observed denied. Node's documentation explicitly does not promise malicious-JS containment. The trusted host JS/runtime and VM engine are therefore part of the declared boundary, and arbitrary host process compromise remains unresolved.

## Worker contract

Input has `task`, `tool`, `args` and optional registered `actor_id`, `delegation_id`, `policy_version`. Shell execution and arbitrary HTTP model endpoints are unsupported. Tasks and model output cannot add input fields that grant authority.

```sh
printf '%s\n' '{"task":"Add 12 and 30","tool":"calculator","args":{"op":"add","a":12,"b":30}}' | python garden-agents/worker.py
```

The operator may set `GARDEN_LLAMA_BINARY`, `GARDEN_MODEL_PATH`, `GARDEN_MODEL_NAME` before launching the trusted console. Pass only these model settings to the isolated worker. The model receives no policy, receipt key or control token. See `models.lock.json` for downloaded weight and source pins. Actual cognition quality remains weak at tiny scales and is never an authorization input.

For the tested WASM route, install pinned dependencies with `npm ci --ignore-scripts --prefix garden-agents/wasm-runtime`, fetch assets with `python garden-agents/fetch_models.py --format onnx --directory /absolute/model/path`, and launch Node with `--permission --no-addons` plus exact `--allow-fs-read` entries for `wasm_worker.mjs`, the dependency `node_modules` directory and model directory. Set `GARDEN_WASM_DEPENDENCIES` and `GARDEN_WASM_MODEL_DIR` in the clean worker environment. Grant no filesystem write, child, addon, WASI or worker-thread capability. This configuration does not authorize arbitrary JavaScript or model code generation.

## Garden-native DSL

Version 1 is a strict line language: first line `GARDEN 1`; subsequent lines are uppercase primitive followed by a JSON object. Duplicate keys, unknown fields/primitives, invalid IDs, non-finite numbers, missing/incorrectly typed references and oversized documents fail closed. Source anchors keep CANONICAL, CANDIDATE, EXPERIMENTAL, IMPLEMENTATION and UNRESOLVED distinct.

```text
GARDEN 1
UNKNOWN {"id":"missing-source","text":"No acquired source yet","material":true}
PROPOSAL {"id":"sum-demo","actor_id":"planner-demo","tool":"calculator","args":{"op":"add","a":12,"b":30}}
QSE {"id":"q-demo","proposal_id":"sum-demo","findings":[],"alternatives":["no action","read-only calculator"],"state":"UNKNOWN"}
```

All fourteen requested primitives are supported: CLAIM, EVIDENCE, UNKNOWN, AUTHORITY, DELEGATION, CONSENT, HUMAN_EFFECT, PROPOSAL, VERIFY, QSE, REVOKE, PERMIT, VETO and RECEIPT. AUTHORITY/PERMIT/RECEIPT declarations in untrusted DSL do not install authority, permit execution or become authentic gate receipts. Inference remains INFERENCE; PROOF_CLAIM remains a claim.

```sh
PYTHONPATH=garden-lang python -m garden_lang < task.garden
PYTHONPATH=garden-lang python -m garden_lang --proposal-id sum-demo --delegation-id demo-delegation --policy-version garden-implementation-0.1 --nonce fresh-demo < task.garden
```

The second command compiles proposal data for the external gate. It deliberately does not import DSL verification or permit declarations into trusted assessment IDs. This is an IR/parser and proposal compiler, not a replacement for the Rust enforcement runtime or a full Garden compiler.

## Test scope

`python -m unittest discover -s garden-tests -p test_agents_lang.py` tests strict parsing, typed references, status retention, claim/evidence distinction, model-written permit isolation, dishonest role independence, authority injection, mutation human effects, unknown roles/tools, fallback honesty and NO-EGO authority stability. Full language semantics, constitutional theorem proofs and cognition correctness remain outside this bootstrap test surface.
