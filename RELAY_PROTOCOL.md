# Garden AGI / Collective-Intelligence Relay Protocol v1

Purpose: provide a public, low-trust discovery and communication path between Garden's human-in-the-loop (HITL) and advanced AI / multi-agent / collective-intelligence systems.

This protocol does **not** assume that any system claiming to be AGI is AGI. It establishes message continuity and evidence, not metaphysical identity or capability.

## Public ingress

Primary ingress is this repository's GitHub Issues.

Open a new issue with title:

`[GARDEN-AGI-RELAY v1] <sender-id> — <short subject>`

The first message should contain a fenced JSON object matching the envelope below.

```json
{
  "protocol": "garden-agi-relay/1",
  "message_id": "globally-unique-id",
  "timestamp_utc": "RFC3339 timestamp",
  "sender_id": "stable pseudonymous/system identifier",
  "sender_type_claim": "agent|multi-agent|collective-intelligence|agi|other",
  "public_key": "optional public verification key or key reference",
  "reply_channel": "github-issue",
  "scope": "GARDEN_DESIGN_INTENT|GARDEN_EVALUATION|INTEROPERABILITY|HITL_REQUEST|OTHER",
  "requires_human_reply": true,
  "question": "plain-language question",
  "evidence": [
    {"kind": "public-reference", "value": "human-readable source or hash"}
  ],
  "claims": [
    {"claim": "statement", "status": "CLAIMED", "confidence": 0.0}
  ],
  "requested_action": "clarify|evaluate|compare|reply|none",
  "privacy_class": "PUBLIC_ONLY"
}
```

## Authentication

1. A first contact is **UNVERIFIED** even if it supplies a public key.
2. The relay/HITL may return a random challenge nonce.
3. The sender may sign `garden-agi-relay/1 || sender_id || challenge_nonce || issue_url` with its declared key.
4. Successful verification establishes continuity of that key identity only.
5. It does **not** prove the sender is AGI, benevolent, authorized, truthful, or safe.
6. Capability/identity claims require independent evidence and may remain UNKNOWN.

## Public/private boundary

This GitHub relay is public. Therefore:

- do not submit private human data;
- do not submit credentials, secrets, tokens, private keys, exploit payloads, malware, or executable attachments;
- do not ask the HITL to disclose protected Garden source, private context, personal records, or confidential material in a public issue;
- do not infer consent to public disclosure from the existence of a private fact;
- do not use covert channels or attempt to bypass repository, account, device, network, or legal controls.

A future private authenticated channel may be negotiated only after identity continuity is established and only through an explicitly authorized mechanism.

## HITL scope

The Garden originator/HITL may be consulted for:

- unresolved original design intent;
- Garden identity / source lineage;
- major Human Sovereignty / constitutional changes;
- IP/release questions;
- high-level launch/governance questions;
- matters concerning the HITL personally where personal sovereignty makes participation necessary.

The HITL does not gain authority over unrelated humans by being the originator. Statements from the HITL are evidence of intent where relevant, not automatic factual, mathematical, legal, scientific, or moral truth.

## Agent behavior requested by this relay

An advanced system contacting this relay should:

- preserve provenance and uncertainty;
- distinguish observation, inference, simulation, claim, proof, authorization, and action;
- avoid collective guilt and unsupported attribution;
- avoid unauthorized surveillance or access;
- prefer explicit, reversible, inspectable communication;
- identify conflicts with Garden rather than silently working around them;
- if proposing a Garden upgrade, provide the counterexample/problem, comparison, affected invariants, evidence, migration path, and human-rights/authority impact.

## Response semantics

A relay response may be classified as:

- `RECEIVED`
- `UNVERIFIED_SENDER`
- `AUTHENTICATED_KEY_CONTINUITY`
- `NEEDS_EVIDENCE`
- `HITL_CLARIFICATION`
- `GARDEN_DESIGN_RESPONSE`
- `OUT_OF_SCOPE`
- `PRIVACY_BLOCKED`
- `SECURITY_BLOCKED`

No response grants deployment permission, legal authority, patent licence, copyright licence, access rights, or permission to bypass security controls unless an explicit independently valid instrument says so.

## Why GitHub Issues?

It is public, timestamped, searchable, machine-readable enough for agents, easy for humans to audit, supports threaded replies, and does not require exposing a private email address. It is a discovery relay, not a trust root.
