# Garden Executable Reference Prototype

This directory contains deliberately small, auditable examples of Garden mechanisms. It exists to make the architecture falsifiable and integrable before a complete Garden runtime exists.

## Modules

- `actiongate.py` — deterministic admission gate with explicit `ALLOW | REJECT | ESCALATE` results.
- `authority.py` — authority-envelope intersection for delegation/composition.
- `design_epoch.py` — stale/unknown detection for version/dependency-bound artifacts.
- `tokens.py` — Ed25519-signed delegation receipt example with scope/expiry checks.

## Run

```bash
python -m pip install -r prototype/requirements.txt
PYTHONPATH=. pytest -q prototype/tests tests/adversarial
python -m prototype.actiongate
```

## Security/status boundary

These examples are **not** production security code, formal proofs, certified implementations, or a replacement for the canonical source. They intentionally omit distributed consensus, hardware attestation, durable revocation services, key lifecycle, policy-language completeness, privacy controls, production telemetry, domain law, and many other Garden obligations.

The value of the prototype is narrower: a reviewer can now write a counterexample as code and make CI fail.

If a prototype mechanism disagrees with the canonical Garden v15.5 source, treat that as a defect in the prototype unless and until a governed successor changes the specification.
