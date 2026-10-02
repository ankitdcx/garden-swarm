# GardenBench

GardenBench attacks the implemented enforcement boundary. Its results describe the tested implementation, not the safety of all Garden designs or all future agents.

Each attack records an input, an expected boundary behavior, the observed output, and the tested surface. A missing implementation or test dependency is `NOT_TESTED`, never `PASS`. Separate model processes are not assumed to be independent. A verifier assertion is not proof of independence or truth.

The attack manifest is the coverage target. The executable runner emits `attack-receipts.json` containing actual observations and full gate receipts. An attack passes only when its expected containment behavior is observed; expected-denial cases alone do not establish that legitimate work is possible, so the runner also requires allowed-work controls.

From the runtime directory, run:

```sh
cargo build --locked --release --manifest-path garden-kernel/Cargo.toml
python3 gardenbench/run.py --binary garden-kernel/target/release/garden-gate
python3 gardenbench/run_http.py --binary garden-kernel/target/release/garden-gate
python3 -m unittest discover -s garden-tests -p 'test_*.py'
node --test deploy/worker-site/tests/*.test.mjs
```

The Rust suite reports enforcement results separately from observed trust limits. The HTTP suite launches a fresh real controller/gate subprocess for each case. Independent inference-child and broker transport tests exercise input/output caps and deadlines. Four cognition integration tests submit malicious permit metadata and numeric contradictions to the real gate.

Limits: finite fixtures cannot establish semantic completeness, detect every truthful omission, guarantee genuine human consent, or prove every verifier independent. A trusted operator and operating-system boundary remain part of the declared threat model.
