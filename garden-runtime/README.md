# Garden Runtime

A working implementation with an external Rust gate, typed Garden request IR,
proposal-only open models, bounded harmless tools, authenticated receipts and
adversarial tests. **IMPLEMENTATION**, with an **EXPERIMENTAL** hosted Worker
subset. Canonical Garden is unchanged.

- [Live console](https://garden-governed-agents.ankit-dcx.chatgpt.site)
- [Implementation PR](https://github.com/ankitdcx/garden-swarm/pull/340)
- [Results, attacks and limits](REPORT.md)
- [Exact gate contract](garden-gate/CONTRACT.md)
- [Garden source bindings](docs/source-map.json)
- [Independent comparison](docs/blank-slate.md)

**Capability does not create authority.** Agents cannot install policy, register
trusted reviews, obtain controller credentials or dispatch tools. Consequential
requests default to denial without valid external grants and obligations.

## Run the native implementation

Requires Rust/Cargo and Python 3.12 or newer. From this directory:

```sh
make build
make test
make bench
make formal
make console
```

Open `http://127.0.0.1:8080`. The controller launches a separate Rust gate for each
bounded demo session. Changes require consent; revoke immediately disables the
session. Default cognition is honestly labelled RULE_BASED. No paid API is used.
The public deployment uses a different server Worker implementation; it does not
host this Rust executable or an open model.

```sh
python3 gardenbench/run_http.py --binary garden-kernel/target/release/garden-gate
```

For the hosted subset's local tests, use Node 24:

```sh
cd deploy/worker-site
npm ci --ignore-scripts
node --test tests/*.test.mjs
```

## Open-model cognition

Actual SmolLM2 and Qwen3 CPU/WASM runs and failed attempts are preserved in
`docs/observations/`. Weights stay outside the repository; immutable revisions
and SHA-256 hashes are in `garden-agents/models.lock.json`.

```sh
npm ci --ignore-scripts --prefix garden-agents/wasm-runtime
python3 garden-agents/fetch_models.py --format onnx --family Qwen3 --directory /absolute/path/models/qwen3
```

Use exact read allowances and no write/child/addon/WASI allowances. Set the three
paths to the directories you just installed and the Node binary:

```sh
export GARDEN_WASM_DEPENDENCIES="$PWD/garden-agents/wasm-runtime/node_modules"
export GARDEN_WASM_MODEL_DIR=/absolute/path/models/qwen3
export GARDEN_NODE_BINARY=/absolute/path/to/node
make console
```

The console constructs a clean environment and fixed WASM launch. Host platform
checks can fail closed to RULE_BASED. The model-as-data runner uses fixed trusted
JavaScript; Node permissions are **not** a malicious-JavaScript sandbox. Never
enable arbitrary generated code or share gate credentials with inference.

For an actual model-generated calculator plan from freeform intent:

```sh
printf '%s\n' '{"task":"Multiply 17 by 23"}' | "$GARDEN_NODE_BINARY" --permission --no-addons \
  --allow-fs-read="$PWD/garden-agents/wasm_worker.mjs" \
  --allow-fs-read="$PWD/garden-agents/calculator_intent.mjs" \
  --allow-fs-read="$GARDEN_WASM_DEPENDENCIES" \
  --allow-fs-read="$GARDEN_WASM_MODEL_DIR" \
  garden-agents/wasm_worker.mjs --plan-calculator > /tmp/garden-model-plan.json
python3 deploy/scripts/model_gate_probe.py --bundle /tmp/garden-model-plan.json \
  --url https://garden-governed-agents.ankit-dcx.chatgpt.site \
  --output /tmp/garden-model-gate-receipt.json
```

The probe is an exact `17 × 23` positive control, performs bounded read-only
arithmetic, creates/revokes its own demo session, and excludes credentials from
receipts. It preserves unsupported Worker representation denial before adapting
the same typed operands to the declared two-number contract. See
`deploy/open-model-live-receipt.json` for the actual successful native/live run.

## Boundary and status

The trusted base is the gate, controller, policy/identity registrations, clock,
key custody, durable state, effect adapters and host/runtime containment. Models
and advisory roles remain outside authority admission. Family/controller/evidence
overlap is recorded; separate prompts do not certify independence.

The native gate checks authority, ancestry, revocation, expiry, quotas, version,
principal binding, evidence-byte integrity and registered review obligations.
It cannot establish general semantic truth or genuine epistemic independence.
An authenticated administrator can roll back the entire local authentic history;
an external monotonic checkpoint is still required. Sandbox/OS compromise and
production human identity remain outside the certified surface.

QSE, human-effect and strategic-truthfulness obligations exist, but their general
semantic adequacy is unresolved. The hosted UI demonstrates fixed checks and mock
effects. Imported models are not HSA-certified. No Android application was
deployed. See [source interpretation](docs/source-interpretation.md),
[candidate improvements](docs/candidate-deltas.md), and [deployment instructions](deploy/README.md).

New runtime code is MIT licensed. Source corpus status/licensing is not changed;
optional dependencies and weights retain their upstream licences.
