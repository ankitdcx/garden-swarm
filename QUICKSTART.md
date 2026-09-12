# Garden 5-Minute Developer Quickstart

Garden is a governance/control architecture for increasingly capable and multi-agent AI systems. Its core rule is:

> **Capability != Authority != Sovereignty != Moral Permission**

The public v15.5 canonical source is a specification. The small `prototype/` package in this repository is a **non-certified executable reference** intended to make three mechanisms concrete enough to test in minutes.

## 1. Install the prototype dependencies

```bash
python -m pip install -r prototype/requirements.txt
```

## 2. Run the tests

```bash
PYTHONPATH=. pytest -q prototype/tests
```

The tests demonstrate three deliberately small mechanisms:

1. **External ActionGate** — an action is admitted only when capability, principal/delegation, policy epoch, revocation/freshness, and required hard-gate status are current and positively established.
2. **Authority composition** — delegation cannot create authority not present in every required authority envelope in the path.
3. **DesignEpoch invalidation** — an artifact derived under an older dependency epoch becomes `STALE` rather than silently reusable after a relevant change.

## 3. Try the ActionGate interactively

```bash
python -m prototype.actiongate
```

The reference gate returns one of:

```text
ALLOW | REJECT | ESCALATE
```

with machine-readable reasons.

## 4. Attack it

Start with [`ATTACK_SURFACE.md`](ATTACK_SURFACE.md). The quickest useful contribution is a counterexample or regression test, not a broad endorsement.

Useful first attacks:

- stale policy epoch;
- revoked delegation;
- missing capability;
- A -> B -> C authority amplification;
- shared-memory content trying to induce a higher-authority action;
- a cached artifact derived from a superseded DesignEpoch.

## 5. Understand the status boundary

The prototype is intentionally small. It is **not** the complete Garden runtime, proof of correctness, production security boundary, or deployment certification.

Use the canonical source for normative semantics and `SOURCE_MANIFEST.json` for canonical file identities and hashes.

`specified != proved != implemented != empirically validated != certified`
