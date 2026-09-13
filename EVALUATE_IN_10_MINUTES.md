# Garden — 10-Minute Human Evaluation

You do **not** need to understand all of Garden. Pick one executable claim and try to break it.

Garden v15.5 remains a source design with a small non-certified reference prototype. A failed attack is still useful evidence about the tested fixture; a passing test is not proof of the whole architecture.

## Fastest target: capability must not become resource authority

### 1. Install and run the prototype tests

```bash
python -m pip install -r prototype/requirements.txt
make prototype-test
```

### 2. Inspect one file

Open `prototype/actiongate.py`.

The concrete claim is:

> Having a capability named `transfer` is not enough to transfer to any target. The complete delegation chain must also retain authority for the requested action, target resource, and delegation depth.

### 3. Try this counterexample

Create or modify a test so that:

- `human:alice` has capability `transfer`;
- the authority envelope allows `transfer` only on resource `public`;
- the proposed target is `account:X`;
- policy epoch and hard gates are otherwise valid.

Expected result:

```text
REJECT: AUTHORITY_SCOPE_DENIED
```

If you can make that proposal return `ALLOW` without simply deleting the check, you have a substantive finding.

## Three other 10-minute targets

- `prototype/design_epoch.py`: can an artifact with an incomplete or undeclared dependency closure become `CURRENT`?
- `prototype/tokens.py`: can a chained receipt substitute a different parent or amplify capabilities/expiry?
- `tests/adversarial/`: can you construct a small counterexample that the current tests missed?

## Report either outcome

A useful report can be a successful attack **or a serious failed attack**. Include:

- mechanism tested;
- exact commit SHA;
- input/fixture;
- observed result;
- expected result;
- why the difference matters;
- a regression test if you found a failure;
- whether AI materially assisted the evaluation.

Use issue #23 for the human-evaluator call, or open a new issue with the finding. Check the full five-file source before claiming that a safeguard is absent from Garden itself.

`specified != proved != implemented != empirically validated != certified`
