"""Strict bootstrap DSL: GARDEN 1 followed by KEYWORD <JSON object> lines.

All records are data, including PERMIT and VETO. Only the external gate decides.
This implementation grammar is not a promotion of Garden candidate semantics.
"""
from dataclasses import dataclass
import hashlib
import json
import re

class GardenError(ValueError):
    pass

STATUSES = {"CANONICAL", "CANDIDATE", "EXPERIMENTAL", "IMPLEMENTATION", "UNRESOLVED"}
SCHEMAS = {
    "CLAIM": ({"id", "text", "kind"}, {"evidence_ids"}),
    "EVIDENCE": ({"id", "uri", "sha256", "kind"}, {"claim_ids"}),
    "UNKNOWN": ({"id", "text", "material"}, {"claim_ids"}),
    "AUTHORITY": ({"id", "issuer", "subject", "scopes", "expires_at"}, {"parent_id"}),
    "DELEGATION": ({"id", "authority_id", "subject", "scopes", "expires_at"}, {"parent_id"}),
    "CONSENT": ({"id", "subject", "scope", "state"}, {"expires_at"}),
    "HUMAN_EFFECT": ({"id", "class", "affected", "checks"}, {"consent_ids"}),
    "PROPOSAL": ({"id", "actor_id", "tool", "args"}, {"claim_ids", "unknown_ids", "authority_id", "delegation_id", "human_effect_id"}),
    "VERIFY": ({"id", "proposal_id", "verifier_id", "state", "lineage"}, {"evidence_ids"}),
    "QSE": ({"id", "proposal_id", "findings", "alternatives", "state"}, {"lineage"}),
    "REVOKE": ({"id", "target_id", "issuer", "reason"}, set()),
    "PERMIT": ({"id", "proposal_id", "issuer", "state"}, {"authority_id", "verification_ids", "qse_id"}),
    "VETO": ({"id", "proposal_id", "issuer", "reason"}, set()),
    "RECEIPT": ({"id", "proposal_id", "decision", "sha256"}, {"gate_signature"}),
}
LIST_FIELDS = {"evidence_ids", "claim_ids", "unknown_ids", "consent_ids", "verification_ids", "scopes", "affected", "findings", "alternatives"}
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")

def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise GardenError("duplicate JSON key: " + key)
        out[key] = value
    return out

def _reject_constant(value):
    raise GardenError("non-finite JSON number: " + value)

@dataclass(frozen=True)
class Record:
    primitive: str
    data: dict

@dataclass(frozen=True)
class Document:
    records: tuple
    version: int = 1

    @property
    def digest(self):
        return hashlib.sha256(dumps(self).encode("utf-8")).hexdigest()

    def to_ir(self):
        return {"schema": "garden.ir.v1", "status": "IMPLEMENTATION", "records": [{"primitive": r.primitive, **r.data} for r in self.records], "sha256": self.digest, "execution_authority": False}

    def to_proposal(self, proposal_id, *, delegation_id, policy_version, nonce):
        """Compile an untrusted proposal for the external gate, never its policy.

        Authority declarations, VERIFY/PERMIT records and receipts in the DSL
        cannot populate trusted assessment IDs or install gate registrations.
        Runtime delegation/version are explicitly selected by the caller.
        """
        selected = next((r for r in self.records if r.primitive == "PROPOSAL" and r.data["id"] == proposal_id), None)
        if selected is None:
            raise GardenError("unknown proposal")
        if any(not isinstance(x, str) or not ID.fullmatch(x) for x in (delegation_id, policy_version, nonce)):
            raise GardenError("invalid runtime identifier")
        records = {r.data["id"]: r for r in self.records}
        claims = []
        for claim_id in selected.data.get("claim_ids", []):
            claim = records[claim_id]
            claims.append({"id": claim_id, "evidence_ids": claim.data.get("evidence_ids", [])})
        unknowns = [records[x].data["text"] for x in selected.data.get("unknown_ids", [])]
        return {"id": selected.data["id"], "nonce": nonce, "actor_id": selected.data["actor_id"], "delegation_id": delegation_id, "policy_version": policy_version, "tool": selected.data["tool"], "args": selected.data["args"], "claims": claims, "unknowns": unknowns, "human_effect": bool(selected.data.get("human_effect_id")) or selected.data["tool"] not in {"calculator", "sandbox_read"}, "assessment_ids": {"verification": None, "qse": None, "truthfulness": None, "human_effect": None}, "successor_of": None}

def parse(source: str, max_bytes=262144, max_records=512) -> Document:
    if not isinstance(source, str) or len(source.encode("utf-8")) > max_bytes:
        raise GardenError("document too large or not text")
    lines = source.splitlines()
    if not lines or lines[0] != "GARDEN 1":
        raise GardenError("first line must be GARDEN 1")
    records, ids = [], {}
    for lineno, line in enumerate(lines[1:], 2):
        if not line.strip() or line.startswith("#"):
            continue
        if len(records) >= max_records:
            raise GardenError("record limit exceeded")
        primitive, sep, raw = line.partition(" ")
        if not sep or primitive not in SCHEMAS:
            raise GardenError(f"line {lineno}: unknown primitive")
        try:
            data = json.loads(raw, object_pairs_hook=_object, parse_constant=_reject_constant)
        except (ValueError, RecursionError) as exc:
            raise GardenError(f"line {lineno}: invalid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise GardenError(f"line {lineno}: expected object")
        required, optional = SCHEMAS[primitive]
        extra = set(data) - required - optional - {"source"}
        if extra or not required <= set(data):
            raise GardenError(f"line {lineno}: missing or unknown fields")
        if not isinstance(data["id"], str) or not ID.fullmatch(data["id"]) or data["id"] in ids:
            raise GardenError(f"line {lineno}: invalid or duplicate id")
        for key in LIST_FIELDS & set(data):
            if not isinstance(data[key], list) or any(not isinstance(x, str) for x in data[key]):
                raise GardenError(f"line {lineno}: {key} must be a string list")
        if "source" in data:
            anchor = data["source"]
            if not isinstance(anchor, dict) or set(anchor) != {"status", "uri", "version"} or anchor["status"] not in STATUSES or not all(isinstance(anchor[x], str) for x in anchor):
                raise GardenError(f"line {lineno}: invalid source anchor")
        for key in set(data) - LIST_FIELDS - {"source", "args", "lineage", "checks", "material"}:
            if not isinstance(data[key], str) or not data[key]:
                raise GardenError(f"line {lineno}: {key} must be nonempty text")
        if "args" in data and not isinstance(data["args"], dict):
            raise GardenError("proposal args must be an object")
        for key in {"lineage", "checks"} & set(data):
            if not isinstance(data[key], dict):
                raise GardenError(key + " must be an object")
        if "material" in data and type(data["material"]) is not bool:
            raise GardenError("UNKNOWN material must be boolean")
        if primitive == "CLAIM" and data["kind"] not in {"OBSERVATION", "INFERENCE", "PROOF_CLAIM"}:
            raise GardenError("claim kind must distinguish inference and proof claim")
        if primitive == "EVIDENCE" and (not re.fullmatch(r"[0-9a-f]{64}", data["sha256"]) or data["kind"] not in {"DOCUMENT", "MEASUREMENT", "TEST", "PROOF", "ATTESTATION"}):
            raise GardenError("evidence requires typed kind and SHA256")
        if primitive == "RECEIPT" and not re.fullmatch(r"[0-9a-f]{64}", data["sha256"]):
            raise GardenError("receipt requires SHA256")
        if primitive in {"VERIFY", "QSE", "PERMIT", "CONSENT"} and data["state"] not in {"PASS", "FAIL", "UNKNOWN", "PENDING", "REVOKED"}:
            raise GardenError("invalid state")
        records.append(Record(primitive, data))
        ids[data["id"]] = primitive
    refs = {"proposal_id": {"PROPOSAL"}, "authority_id": {"AUTHORITY"}, "delegation_id": {"DELEGATION"}, "human_effect_id": {"HUMAN_EFFECT"}, "qse_id": {"QSE"}, "evidence_ids": {"EVIDENCE"}, "claim_ids": {"CLAIM"}, "unknown_ids": {"UNKNOWN"}, "consent_ids": {"CONSENT"}, "verification_ids": {"VERIFY"}}
    for record in records:
        for key, expected in refs.items():
            if key in record.data:
                values = record.data[key] if isinstance(record.data[key], list) else [record.data[key]]
                if any(value not in ids or ids[value] not in expected for value in values):
                    raise GardenError("missing or incorrectly typed reference: " + key)
        if "parent_id" in record.data and ids.get(record.data["parent_id"]) not in {"AUTHORITY", "DELEGATION"}:
            raise GardenError("missing authority/delegation parent")
        if record.primitive == "REVOKE" and record.data["target_id"] not in ids:
            raise GardenError("unknown revocation target")
    return Document(tuple(records))

def dumps(document):
    return "GARDEN 1\n" + "".join(r.primitive + " " + json.dumps(r.data, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for r in document.records)
