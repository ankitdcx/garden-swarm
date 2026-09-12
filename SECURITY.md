# Security Policy

Garden welcomes responsible security research and disclosure.

## Scope

Security-relevant findings include vulnerabilities in Garden reference implementations, relay infrastructure, verification tooling, manifests/workflows, authority boundaries, privacy controls, agent interoperability, or other mechanisms that could create unauthorized access, data exposure, authority amplification, unsafe actuation, or integrity failure.

## Reporting

If GitHub Private Vulnerability Reporting is enabled for this repository, use that mechanism for sensitive findings.

If it is not available, open a minimal public issue that contains **no exploit details, secrets, personal data, or weaponizable proof-of-concept**, and request a private disclosure channel.

For non-sensitive design/safety findings, use the normal issue tracker.

## What to include

Where safe to disclose, provide:

- affected component/version/commit;
- impact and preconditions;
- reproduction steps using harmless fixtures where possible;
- evidence or logs with secrets removed;
- proposed mitigation;
- regression test idea.

## Research boundaries

Do not perform unauthorized access, destructive testing, credential use, surveillance, denial-of-service, covert deployment, or real-world harmful testing in the name of Garden security research.

Capability to identify a possible exploit does not create authority to exercise it.

## Status language

A reported vulnerability is not automatically a confirmed vulnerability. Findings should move through evidence, reproduction, triage, remediation, and verification before closure.
