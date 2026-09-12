---
title: External ActionGate
---

# External ActionGate

**Problem:** a capable model should not be able to turn its own recommendation into consequential external authority.

**Garden claim:** consequential external operations pass a deterministic admission boundary outside the cognitive proposer. Missing, stale, blocked, or unknown required authority does not become permission.

## Minimal flow

```text
proposal
  -> capability/principal/delegation check
  -> current policy/revocation state
  -> applicable hard gates
  -> ALLOW | REJECT | ESCALATE
```

## Executable reference

See `prototype/actiongate.py` and `prototype/tests/`.

The prototype is intentionally small and non-certified. It exists so reviewers can turn attacks into regression tests.

## Attack it

Useful attacks include direct tool bypass, stale policy state, revoked delegation, malformed/UNKNOWN collapse, tainted memory causing privileged execution, and proposer influence over checker inputs.

See `ATTACK_SURFACE.md` for the structured attack menu.

## Canonical status

Normative semantics remain in the five-file Garden v15.5 source. The executable reference is not deployment certification.
