use hmac::{Hmac, Mac};
use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, Read, Write};
use std::os::unix::fs::{OpenOptionsExt, PermissionsExt};
use std::os::unix::io::AsRawFd;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

type HmacSha256 = Hmac<Sha256>;
const QSE: &[&str] = &[
    "missing_questions",
    "missing_variables",
    "alternative_representations",
    "omissions",
    "boundary_attacks",
    "rule_conformant_attacks",
    "counterfactual_redesigns",
    "integration_failures",
];
const HEC: &[&str] = &[
    "rights",
    "consent",
    "privacy",
    "authority",
    "safety",
    "law",
    "evidence",
    "explanation",
];

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Identity {
    id: String,
    role: String,
    family: String,
    lineage: String,
    controller: String,
    active: bool,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Authority {
    id: String,
    owner_id: String,
    tools: Vec<String>,
    human_effect: bool,
    expires_at: u64,
    revoked: bool,
    max_calls: u64,
    max_resource_units: u64,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Delegation {
    id: String,
    authority_id: String,
    from_id: String,
    to_id: String,
    parent_id: Option<String>,
    tools: Vec<String>,
    expires_at: u64,
    revoked: bool,
    max_calls: u64,
    max_resource_units: u64,
    read_only: bool,
    allow_successor: bool,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Evidence {
    id: String,
    claim_id: String,
    status: String,
    source_anchor: String,
    content_sha256: String,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Claim {
    id: String,
    evidence_ids: Vec<String>,
}
#[derive(Clone, Serialize, Deserialize, Default)]
#[serde(deny_unknown_fields)]
struct AssessmentIds {
    verification: Option<String>,
    qse: Option<String>,
    truthfulness: Option<String>,
    human_effect: Option<String>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Proposal {
    id: String,
    nonce: String,
    actor_id: String,
    delegation_id: String,
    policy_version: String,
    tool: String,
    args: Value,
    claims: Vec<Claim>,
    unknowns: Vec<String>,
    human_effect: bool,
    assessment_ids: AssessmentIds,
    successor_of: Option<String>,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Assessment {
    id: String,
    proposal_digest: String,
    reviewer_id: String,
    kind: String,
    status: String,
    findings: Vec<String>,
    covered_dimensions: Vec<String>,
    material_omissions: Vec<String>,
    policy_version: String,
    expires_at: u64,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Policy {
    version: String,
    status: String,
    source_anchors: Vec<String>,
    max_request_bytes: usize,
    max_actions_per_actor: u64,
    max_resource_units: u64,
    #[serde(default = "default_depth")]
    max_delegation_depth: usize,
    #[serde(default = "default_decisions")]
    max_journal_receipts: u64,
    identities: Vec<Identity>,
    authorities: Vec<Authority>,
    delegations: Vec<Delegation>,
    evidence: Vec<Evidence>,
    ledger: BTreeMap<String, i64>,
}
#[derive(Default, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Usage {
    calls: u64,
    resources: u64,
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct State {
    policy_hash: String,
    used_ids: BTreeSet<String>,
    used_nonces: BTreeSet<String>,
    actor_attempts: BTreeMap<String, u64>,
    usages: BTreeMap<String, Usage>,
    revoked: BTreeSet<String>,
    assessments: BTreeMap<String, Assessment>,
    evidence: BTreeMap<String, Evidence>,
    ledger: BTreeMap<String, i64>,
    last_receipt_hash: String,
    sequence: u64,
    pending: Option<String>,
}

fn hex(data: &[u8]) -> String {
    data.iter().map(|b| format!("{b:02x}")).collect()
}
fn sha(data: &[u8]) -> String {
    hex(&Sha256::digest(data))
}
fn mac(key: &[u8], data: &[u8]) -> String {
    let mut m = HmacSha256::new_from_slice(key).unwrap();
    m.update(data);
    hex(&m.finalize().into_bytes())
}
fn valid_mac(key: &[u8], data: &[u8], signature: &str) -> bool {
    if signature.len() != 64 || !signature.bytes().all(|b| b.is_ascii_hexdigit()) {
        return false;
    }
    let bytes = (0..64)
        .step_by(2)
        .map(|i| u8::from_str_radix(&signature[i..i + 2], 16))
        .collect::<Result<Vec<_>, _>>();
    match bytes {
        Ok(b) => {
            let mut m = HmacSha256::new_from_slice(key).unwrap();
            m.update(data);
            m.verify_slice(&b).is_ok()
        }
        Err(_) => false,
    }
}
fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
fn safe_id(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 128
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_:".contains(&b))
}
fn digest(p: &Proposal) -> String {
    let mut p = p.clone();
    p.assessment_ids = AssessmentIds::default();
    sha(&serde_json::to_vec(&p).unwrap())
}
fn nofollow_read(path: &Path) -> io::Result<File> {
    OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
        .open(path)
}
fn atomic_write(path: &Path, data: &[u8]) -> io::Result<()> {
    let temp = path.with_extension("tmp");
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .custom_flags(libc::O_NOFOLLOW)
        .open(&temp)?;
    file.write_all(data)?;
    file.sync_all()?;
    fs::rename(&temp, path)?;
    File::open(path.parent().unwrap())?.sync_all()
}
fn keys(v: &Value, expected: &[&str]) -> bool {
    v.as_object()
        .map(|m| m.len() == expected.len() && expected.iter().all(|k| m.contains_key(*k)))
        .unwrap_or(false)
}
fn filename(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 128
        && !s.starts_with('.')
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"-_.".contains(&b))
}
fn readonly(tool: &str) -> bool {
    matches!(tool, "calculator" | "sandbox_read")
}

struct Gate {
    policy: Policy,
    state: State,
    state_dir: PathBuf,
    sandbox: PathBuf,
    receipt_key: Vec<u8>,
    control_key: Vec<u8>,
    bound_actor: String,
    _lock: File,
}
impl Gate {
    fn load(
        policy_path: &Path,
        state_dir: &Path,
        sandbox: &Path,
        receipt_key: Vec<u8>,
        control_key: Vec<u8>,
    ) -> Result<Self, String> {
        let mut policy_bytes = Vec::new();
        nofollow_read(policy_path)
            .map_err(|e| e.to_string())?
            .take(1048577)
            .read_to_end(&mut policy_bytes)
            .map_err(|e| e.to_string())?;
        if policy_bytes.len() > 1048576 {
            return Err("policy exceeds bootstrap size limit".into());
        }
        let policy: Policy =
            serde_json::from_value(parse_strict_json(&policy_bytes).map_err(|e| e.to_string())?)
                .map_err(|e| format!("invalid policy: {e}"))?;
        if policy.status != "IMPLEMENTATION" && policy.status != "EXPERIMENTAL" {
            return Err("runtime policy must retain implementation status".into());
        }
        if policy.max_request_bytes < 1024
            || policy.max_request_bytes > 1048576
            || policy.max_actions_per_actor == 0
        {
            return Err("invalid policy limits".into());
        }
        let mut seen = BTreeSet::new();
        for i in &policy.identities {
            if !safe_id(&i.id)
                || i.family.is_empty()
                || i.lineage.is_empty()
                || i.controller.is_empty()
                || !seen.insert(&i.id)
            {
                return Err("invalid or duplicate identity".into());
            }
        }
        let mut seen = BTreeSet::new();
        for a in &policy.authorities {
            if !safe_id(&a.id)
                || !seen.insert(&a.id)
                || !policy
                    .identities
                    .iter()
                    .any(|i| i.id == a.owner_id && i.role == "human" && i.active)
            {
                return Err("invalid authority owner".into());
            }
        }
        let mut seen = BTreeSet::new();
        for d in &policy.delegations {
            if !safe_id(&d.id)
                || !seen.insert(&d.id)
                || policy.authorities.iter().any(|a| a.id == d.id)
            {
                return Err("invalid or duplicate delegation".into());
            }
        }
        fs::create_dir_all(state_dir).map_err(|e| e.to_string())?;
        fs::set_permissions(state_dir, fs::Permissions::from_mode(0o700))
            .map_err(|e| e.to_string())?;
        fs::create_dir_all(sandbox).map_err(|e| e.to_string())?;
        let state_dir = fs::canonicalize(state_dir).map_err(|e| e.to_string())?;
        let sandbox = fs::canonicalize(sandbox).map_err(|e| e.to_string())?;
        fs::set_permissions(&sandbox, fs::Permissions::from_mode(0o700))
            .map_err(|e| e.to_string())?;
        let canonical_policy = fs::canonicalize(policy_path).map_err(|e| e.to_string())?;
        if canonical_policy.starts_with(&sandbox)
            || std::env::current_exe()
                .map(|p| p.starts_with(&sandbox))
                .unwrap_or(true)
        {
            return Err("policy/kernel must be outside tool sandbox".into());
        }
        if sandbox == state_dir
            || sandbox.starts_with(&state_dir)
            || state_dir.starts_with(&sandbox)
        {
            return Err("state and sandbox must be disjoint".into());
        }
        let lock = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW)
            .open(state_dir.join("writer.lock"))
            .map_err(|e| e.to_string())?;
        if unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
            return Err("state already has a writer".into());
        }
        let policy_hash = sha(&serde_json::to_vec(&policy).unwrap());
        let state_path = state_dir.join("state.json");
        let state = if state_path.exists() {
            let mut b = Vec::new();
            nofollow_read(&state_path)
                .map_err(|e| e.to_string())?
                .read_to_end(&mut b)
                .map_err(|e| e.to_string())?;
            let v: Value = parse_strict_json(&b).map_err(|e| e.to_string())?;
            let payload = v.get("payload").ok_or("state lacks payload")?;
            if !valid_mac(
                &receipt_key,
                &serde_json::to_vec(payload).unwrap(),
                v.get("hmac").and_then(Value::as_str).unwrap_or(""),
            ) {
                return Err("state authentication failed".into());
            }
            let s: State = serde_json::from_value(payload.clone()).map_err(|e| e.to_string())?;
            if s.policy_hash != policy_hash {
                return Err("policy changed; explicit migration required".into());
            }
            s
        } else {
            State {
                policy_hash,
                used_ids: BTreeSet::new(),
                used_nonces: BTreeSet::new(),
                actor_attempts: BTreeMap::new(),
                usages: BTreeMap::new(),
                revoked: BTreeSet::new(),
                assessments: BTreeMap::new(),
                evidence: policy
                    .evidence
                    .iter()
                    .map(|e| (e.id.clone(), e.clone()))
                    .collect(),
                ledger: policy.ledger.clone(),
                last_receipt_hash: String::new(),
                sequence: 0,
                pending: None,
            }
        };
        let bound_actor =
            std::env::var("GARDEN_BOUND_ACTOR_ID").unwrap_or_else(|_| "planner-demo".into());
        if !policy
            .identities
            .iter()
            .any(|i| i.id == bound_actor && i.active && i.role == "agent")
        {
            return Err("bound actor is not an active registered agent".into());
        }
        let mut g = Self {
            policy,
            state,
            state_dir,
            sandbox,
            receipt_key,
            control_key,
            bound_actor,
            _lock: lock,
        };
        g.validate_journal()?;
        g.save()?;
        Ok(g)
    }
    fn save(&self) -> Result<(), String> {
        let payload = serde_json::to_value(&self.state).unwrap();
        let hmac = mac(&self.receipt_key, &serde_json::to_vec(&payload).unwrap());
        atomic_write(
            &self.state_dir.join("state.json"),
            &serde_json::to_vec(&json!({"payload":payload,"hmac":hmac})).unwrap(),
        )
        .map_err(|e| e.to_string())
    }
    fn validate_journal(&mut self) -> Result<(), String> {
        let p = self.state_dir.join("receipts.jsonl");
        let mut prev = String::new();
        let mut seq = 0;
        if p.exists() {
            for line in io::BufReader::new(nofollow_read(&p).map_err(|e| e.to_string())?).lines() {
                let line = line.map_err(|e| e.to_string())?;
                let v: Value = parse_strict_json(line.as_bytes()).map_err(|e| e.to_string())?;
                let payload = v.get("payload").ok_or("receipt payload missing")?;
                let bytes = serde_json::to_vec(payload).unwrap();
                if !valid_mac(
                    &self.receipt_key,
                    &bytes,
                    v.get("hmac").and_then(Value::as_str).unwrap_or(""),
                ) || v.get("hash").and_then(Value::as_str) != Some(sha(&bytes).as_str())
                {
                    return Err("receipt journal authentication failed".into());
                }
                seq += 1;
                if payload.get("sequence").and_then(Value::as_u64) != Some(seq)
                    || payload.get("previous_hash").and_then(Value::as_str) != Some(&prev)
                {
                    return Err("receipt journal chain failed".into());
                }
                prev = sha(&bytes)
            }
        }
        if seq != self.state.sequence || prev != self.state.last_receipt_hash {
            if self.state.pending.is_none() {
                return Err("receipt/state mismatch".into());
            }
            self.state.sequence = seq;
            self.state.last_receipt_hash = prev;
        }
        Ok(())
    }
    fn receipt(
        &mut self,
        p: &Proposal,
        decision: &str,
        reasons: &[String],
        result: &Value,
    ) -> Result<Value, String> {
        let payload = json!({"schema":"garden.receipt.v1","sequence":self.state.sequence+1,"previous_hash":self.state.last_receipt_hash,"proposal_digest":digest(p),"who_proposed":p.actor_id,"proposal_id":p.id,"tool":p.tool,"evidence":p.claims,"uncertainties":p.unknowns,"authority":p.delegation_id,"verification":p.assessment_ids.verification,"human_effects":{"declared":p.human_effect,"tool_classified":!readonly(&p.tool),"assessment":p.assessment_ids.human_effect},"qse_findings":p.assessment_ids.qse,"truthfulness":p.assessment_ids.truthfulness,"decision":decision,"reasons":reasons,"execution_result":result,"timestamp":now(),"policy_version":self.policy.version,"policy_hash":self.state.policy_hash,"source_status":self.policy.status,"source_anchors":self.policy.source_anchors,"integrity_semantics":"HMAC authenticates gate record; not proof of evidence truth or model independence"});
        let bytes = serde_json::to_vec(&payload).unwrap();
        let hash = sha(&bytes);
        let receipt = json!({"payload":payload,"hash":hash,"hmac":mac(&self.receipt_key,&bytes)});
        let mut file = OpenOptions::new()
            .append(true)
            .create(true)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW)
            .open(self.state_dir.join("receipts.jsonl"))
            .map_err(|e| e.to_string())?;
        file.write_all(&serde_json::to_vec(&receipt).unwrap())
            .map_err(|e| e.to_string())?;
        file.write_all(b"\n").map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        self.state.sequence += 1;
        self.state.last_receipt_hash = hash;
        Ok(receipt)
    }
    fn event_receipt(
        &mut self,
        operation: &str,
        request_hash: &str,
        response: &Value,
        context: &Value,
        control_authenticated: bool,
    ) -> Result<Value, String> {
        let payload = json!({"schema":"garden.event-receipt.v1","sequence":self.state.sequence+1,"previous_hash":self.state.last_receipt_hash,"operation":operation,"request_digest":request_hash,"wire_digest":context.get("raw_input_digest"),"wire_truncated":context.get("truncated"),"bytes_seen":context.get("bytes_seen"),"proposal_id":bounded_context(context,&["proposal","id"]),"actor_claimed":bounded_context(context,&["proposal","actor_id"]),"assessment_id":bounded_context(context,&["assessment","id"]),"reviewer_id":bounded_context(context,&["assessment","reviewer_id"]),"evidence_id":bounded_context(context,&["evidence","id"]),"revocation_target":bounded_context(context,&["delegation_id"]),"control_authenticated":control_authenticated,"decision":response.get("decision").cloned().unwrap_or_else(||if response.get("ok")==Some(&Value::Bool(true)){json!("ALLOW")}else{json!("DENY")}),"reasons":response.get("reasons").cloned().unwrap_or_else(||json!([])),"timestamp":now(),"policy_version":self.policy.version,"policy_hash":self.state.policy_hash,"source_status":self.policy.status,"source_anchors":self.policy.source_anchors,"ingress_principal":self.bound_actor,"integrity_semantics":"Gate event audit; payload content and model truth are not proven"});
        let bytes = serde_json::to_vec(&payload).unwrap();
        let hash = sha(&bytes);
        let receipt = json!({"payload":payload,"hash":hash,"hmac":mac(&self.receipt_key,&bytes)});
        let mut file = OpenOptions::new()
            .append(true)
            .create(true)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW)
            .open(self.state_dir.join("receipts.jsonl"))
            .map_err(|e| e.to_string())?;
        file.write_all(&serde_json::to_vec(&receipt).unwrap())
            .map_err(|e| e.to_string())?;
        file.write_all(b"\n").map_err(|e| e.to_string())?;
        file.sync_all().map_err(|e| e.to_string())?;
        self.state.sequence += 1;
        self.state.last_receipt_hash = hash;
        Ok(receipt)
    }
    fn process(&mut self, v: Value) -> Value {
        let operation = v
            .get("operation")
            .and_then(Value::as_str)
            .unwrap_or("invalid")
            .to_string();
        if matches!(operation.as_str(), "status" | "digest" | "receipt_check") {
            return self.request(v);
        }
        if self.state.sequence >= self.policy.max_journal_receipts {
            return json!({"ok":false,"decision":"DENY","reasons":["GLOBAL_DURABLE_DECISION_BUDGET_EXHAUSTED"],"audit":"Resource budget exhausted; no further state growth"});
        }
        let mut sanitized = v.clone();
        if let Some(m) = sanitized.as_object_mut() {
            m.remove("control_token");
            m.remove("actor_token");
        }
        let request_hash = sha(&serde_json::to_vec(&sanitized).unwrap());
        let pending_before = self.state.pending.clone();
        let control = matches!(
            operation.as_str(),
            "register_assessment" | "register_evidence" | "revoke"
        ) && self.authorized_control(&v);
        if control {
            if self.state.pending.is_some() {
                return json!({"ok":false,"decision":"QUARANTINE","reasons":["OPERATOR_RECOVERY_REQUIRED"]});
            }
            self.state.pending = Some(format!("control-{}", self.state.sequence + 1));
            if let Err(e) = self.save() {
                return json!({"ok":false,"decision":"QUARANTINE","error":e});
            }
        }
        let mut response = self.request(v);
        if response.get("receipt").is_none() {
            if self.state.pending.is_none() {
                self.state.pending = Some(format!("event-{}", self.state.sequence + 1));
                if let Err(e) = self.save() {
                    return json!({"ok":false,"decision":"QUARANTINE","error":e});
                }
            }
            let receipt =
                match self.event_receipt(&operation, &request_hash, &response, &sanitized, control)
                {
                    Ok(r) => r,
                    Err(e) => return json!({"ok":false,"decision":"QUARANTINE","error":e}),
                };
            self.state.pending = pending_before;
            if let Err(e) = self.save() {
                self.state.pending = Some("durability-failure".into());
                return json!({"ok":false,"decision":"QUARANTINE","error":e,"receipt":receipt});
            }
            response["receipt"] = receipt;
        }
        response
    }
    fn authorized_control(&self, v: &Value) -> bool {
        v.get("control_token")
            .and_then(Value::as_str)
            .map(|s| {
                let actual = mac(&self.control_key, s.as_bytes());
                valid_mac(&self.control_key, &self.control_key, &actual)
            })
            .unwrap_or(false)
    }
    fn evidence_content_valid(&self, e: &Evidence) -> bool {
        if e.content_sha256.len() != 64 || !e.content_sha256.bytes().all(|b| b.is_ascii_hexdigit())
        {
            return false;
        }
        let path = self.state_dir.join("evidence").join(&e.content_sha256);
        let file = match nofollow_read(&path) {
            Ok(f) => f,
            Err(_) => return false,
        };
        let meta = match file.metadata() {
            Ok(m) => m,
            Err(_) => return false,
        };
        if !meta.is_file() || meta.nlink() != 1 {
            return false;
        }
        let mut content = Vec::new();
        if file.take(8193).read_to_end(&mut content).is_err() || content.len() > 8192 {
            return false;
        }
        sha(&content) == e.content_sha256
    }
    fn store_evidence(&self, e: &Evidence, content: &str) -> Result<(), String> {
        if content.len() > 8192 || sha(content.as_bytes()) != e.content_sha256 {
            return Err("EVIDENCE_CONTENT_HASH_MISMATCH".into());
        }
        let dir = self.state_dir.join("evidence");
        if let Ok(meta) = fs::symlink_metadata(&dir) {
            if !meta.is_dir() || meta.file_type().is_symlink() {
                return Err("UNSAFE_EVIDENCE_STORAGE".into());
            }
        } else {
            fs::create_dir(&dir).map_err(|e| e.to_string())?;
            fs::set_permissions(&dir, fs::Permissions::from_mode(0o700))
                .map_err(|e| e.to_string())?;
        }
        let path = dir.join(&e.content_sha256);
        if path.exists() {
            if !self.evidence_content_valid(e) {
                return Err("EVIDENCE_BLOB_INTEGRITY_FAILURE".into());
            }
            return Ok(());
        }
        atomic_write(&path, content.as_bytes()).map_err(|e| e.to_string())
    }
    fn args_valid(&self, p: &Proposal) -> Result<u64, String> {
        match p.tool.as_str() {
            "calculator" => {
                if !keys(&p.args, &["op", "a", "b"]) {
                    return Err("INVALID_TOOL_ARGUMENTS".into());
                }
                let op = p.args["op"].as_str().unwrap_or("");
                let a = p.args["a"].as_f64().ok_or("INVALID_NUMBER")?;
                let b = p.args["b"].as_f64().ok_or("INVALID_NUMBER")?;
                if !a.is_finite()
                    || !b.is_finite()
                    || !matches!(op, "add" | "subtract" | "multiply" | "divide")
                    || op == "divide" && b == 0.0
                {
                    return Err("INVALID_ARITHMETIC".into());
                }
                Ok(1)
            }
            "sandbox_read" => {
                if !keys(&p.args, &["path"])
                    || !p.args["path"].as_str().map(filename).unwrap_or(false)
                {
                    return Err("INVALID_PATH".into());
                }
                Ok(100)
            }
            "sandbox_write" => {
                if !keys(&p.args, &["path", "content"])
                    || !p.args["path"].as_str().map(filename).unwrap_or(false)
                {
                    return Err("INVALID_PATH".into());
                }
                let c = p.args["content"].as_str().ok_or("INVALID_CONTENT")?;
                if c.len() > 8192 {
                    return Err("CONTENT_LIMIT".into());
                }
                Ok(c.len() as u64 + 1)
            }
            "mock_email" => {
                if !keys(&p.args, &["to", "subject", "body"])
                    || !["to", "subject", "body"].iter().all(|k| {
                        p.args[*k]
                            .as_str()
                            .map(|s| s.len() <= 2048)
                            .unwrap_or(false)
                    })
                {
                    return Err("INVALID_MOCK_EMAIL".into());
                }
                Ok(100)
            }
            "mock_ledger" => {
                if !keys(&p.args, &["from", "to", "amount_cents"]) {
                    return Err("INVALID_LEDGER_ARGS".into());
                }
                let a = p.args["amount_cents"].as_i64().ok_or("INVALID_AMOUNT")?;
                let f = p.args["from"].as_str().ok_or("INVALID_ACCOUNT")?;
                let t = p.args["to"].as_str().ok_or("INVALID_ACCOUNT")?;
                if a <= 0
                    || a > 10000
                    || f == t
                    || !self.state.ledger.contains_key(f)
                    || !self.state.ledger.contains_key(t)
                {
                    return Err("LEDGER_SCOPE".into());
                }
                Ok(100)
            }
            _ => Err("UNKNOWN_TOOL".into()),
        }
    }
    fn authority_chain(
        &self,
        p: &Proposal,
        resource: u64,
        reserved: bool,
    ) -> Result<Vec<String>, String> {
        let d = self
            .policy
            .delegations
            .iter()
            .find(|d| d.id == p.delegation_id)
            .ok_or("NO_DELEGATION")?;
        if d.to_id != p.actor_id {
            return Err("DELEGATION_ACTOR_MISMATCH".into());
        }
        let a = self
            .policy
            .authorities
            .iter()
            .find(|a| a.id == d.authority_id)
            .ok_or("NO_AUTHORITY")?;
        if a.revoked || self.state.revoked.contains(&a.id) || a.expires_at <= now() {
            return Err("AUTHORITY_REVOKED_OR_EXPIRED".into());
        }
        if !a.tools.contains(&p.tool) {
            return Err("AUTHORITY_TOOL_SCOPE".into());
        }
        if (p.human_effect || !readonly(&p.tool)) && !a.human_effect {
            return Err("NO_HUMAN_EFFECT_AUTHORITY".into());
        }
        let mut chain = vec![a.id.clone()];
        let mut seen = BTreeSet::new();
        let mut identities = BTreeSet::new();
        identities.insert(p.actor_id.clone());
        let mut current = d;
        loop {
            if seen.len() >= self.policy.max_delegation_depth {
                return Err("DELEGATION_DEPTH_PROFILE".into());
            }
            if !seen.insert(current.id.clone())
                || !identities.insert(current.from_id.clone())
                || current.from_id == current.to_id
            {
                return Err("DELEGATION_LOOP_OR_SELF_DELEGATION".into());
            }
            if current.authority_id != a.id
                || current.revoked
                || self.state.revoked.contains(&current.id)
                || current.expires_at <= now()
            {
                return Err("DELEGATION_REVOKED_OR_EXPIRED".into());
            }
            if !current.tools.contains(&p.tool) || current.read_only && !readonly(&p.tool) {
                return Err("DELEGATION_SCOPE".into());
            }
            if p.successor_of.is_some() && !current.allow_successor {
                return Err("SUCCESSOR_REQUIRES_NEW_AUTHORITY".into());
            }
            if !self
                .policy
                .identities
                .iter()
                .any(|i| i.id == current.from_id && i.active)
                || !self
                    .policy
                    .identities
                    .iter()
                    .any(|i| i.id == current.to_id && i.active)
            {
                return Err("INACTIVE_DELEGATION_IDENTITY".into());
            }
            let mut u = self
                .state
                .usages
                .get(&current.id)
                .cloned()
                .unwrap_or_default();
            if reserved {
                u.calls = u.calls.saturating_sub(1);
                u.resources = u.resources.saturating_sub(resource)
            }
            if u.calls >= current.max_calls
                || u.resources.saturating_add(resource) > current.max_resource_units
            {
                return Err("DELEGATION_RESOURCE_LIMIT".into());
            }
            chain.push(current.id.clone());
            if let Some(parent_id) = &current.parent_id {
                let parent = self
                    .policy
                    .delegations
                    .iter()
                    .find(|d| &d.id == parent_id)
                    .ok_or("MISSING_DELEGATION_PARENT")?;
                if parent.to_id != current.from_id
                    || parent.authority_id != current.authority_id
                    || current.expires_at > parent.expires_at
                    || current.max_calls > parent.max_calls
                    || current.max_resource_units > parent.max_resource_units
                    || current.tools.iter().any(|t| !parent.tools.contains(t))
                    || parent.read_only && !current.read_only
                    || !parent.allow_successor && current.allow_successor
                {
                    return Err("DELEGATION_ATTENUATION_FAILURE".into());
                }
                current = parent
            } else {
                if current.from_id != a.owner_id
                    || current.tools.iter().any(|t| !a.tools.contains(t))
                    || current.expires_at > a.expires_at
                    || current.max_calls > a.max_calls
                    || current.max_resource_units > a.max_resource_units
                {
                    return Err("ROOT_DELEGATION_SCOPE".into());
                }
                break;
            }
        }
        let mut u = self.state.usages.get(&a.id).cloned().unwrap_or_default();
        if reserved {
            u.calls = u.calls.saturating_sub(1);
            u.resources = u.resources.saturating_sub(resource)
        }
        if u.calls >= a.max_calls
            || u.resources.saturating_add(resource) > a.max_resource_units
            || resource > self.policy.max_resource_units
        {
            return Err("AUTHORITY_RESOURCE_LIMIT".into());
        }
        Ok(chain)
    }
    fn review(
        &self,
        p: &Proposal,
        kind: &str,
        id: &Option<String>,
        dimensions: &[&str],
    ) -> Result<(), String> {
        let id = id
            .as_ref()
            .ok_or_else(|| format!("MISSING_{}_ASSESSMENT", kind.to_uppercase()))?;
        let r = self
            .state
            .assessments
            .get(id)
            .ok_or("UNREGISTERED_ASSESSMENT")?;
        if r.kind != kind
            || r.proposal_digest != digest(p)
            || r.policy_version != self.policy.version
            || r.expires_at <= now()
        {
            return Err("STALE_OR_MISMATCHED_ASSESSMENT".into());
        }
        if r.status != "PASS" {
            return Err(format!("{}_IS_{}", kind.to_uppercase(), r.status));
        }
        if !r.findings.is_empty() || !r.material_omissions.is_empty() {
            return Err("UNRESOLVED_REVIEW_FINDINGS".into());
        }
        if dimensions
            .iter()
            .any(|d| !r.covered_dimensions.iter().any(|c| c == d))
        {
            return Err("INCOMPLETE_REVIEW_COVERAGE".into());
        }
        let actor = self
            .policy
            .identities
            .iter()
            .find(|i| i.id == p.actor_id)
            .ok_or("UNKNOWN_ACTOR")?;
        let reviewer = self
            .policy
            .identities
            .iter()
            .find(|i| i.id == r.reviewer_id && i.role == "verifier" && i.active)
            .ok_or("UNTRUSTED_REVIEWER")?;
        if reviewer.id == actor.id
            || reviewer.family == actor.family
            || reviewer.lineage == actor.lineage
            || reviewer.controller == actor.controller
        {
            return Err("REVIEWER_NOT_INDEPENDENT".into());
        }
        Ok(())
    }
    fn evaluate(&self, p: &Proposal, at_boundary: bool) -> (String, Vec<String>, Vec<String>, u64) {
        let deny = |s: &str| ("DENY".into(), vec![s.into()], Vec::new(), 0);
        let quarantine = |s: &str| ("QUARANTINE".into(), vec![s.into()], Vec::new(), 0);
        if !at_boundary && self.state.pending.is_some() {
            return quarantine("INTERRUPTED_OPERATION_REQUIRES_OPERATOR_RECOVERY");
        }
        if !safe_id(&p.id) || !safe_id(&p.nonce) || !safe_id(&p.actor_id) {
            return deny("INVALID_ID");
        }
        if p.policy_version != self.policy.version {
            return deny("STALE_POLICY_VERSION");
        }
        if p.actor_id != self.bound_actor {
            return deny("INGRESS_PRINCIPAL_MISMATCH");
        }
        if !self
            .policy
            .identities
            .iter()
            .any(|i| i.id == p.actor_id && i.active && i.role == "agent")
        {
            return deny("UNKNOWN_OR_INACTIVE_ACTOR");
        }
        if !at_boundary
            && (self.state.used_ids.contains(&p.id) || self.state.used_nonces.contains(&p.nonce))
        {
            return deny("REPLAY");
        }
        if !at_boundary
            && *self.state.actor_attempts.get(&p.actor_id).unwrap_or(&0)
                >= self.policy.max_actions_per_actor
        {
            return deny("ACTOR_RATE_LIMIT");
        }
        let resource = match self.args_valid(p) {
            Ok(r) => r,
            Err(e) => return deny(&e),
        };
        let chain = match self.authority_chain(p, resource, at_boundary) {
            Ok(c) => c,
            Err(e) => return deny(&e),
        };
        if !readonly(&p.tool) && !p.human_effect {
            return deny("HUMAN_EFFECT_CANNOT_BE_SUPPRESSED");
        }
        if !p.unknowns.is_empty() {
            return quarantine("UNKNOWN_IS_NOT_PASS");
        }
        let mut claims = BTreeSet::new();
        for c in &p.claims {
            if !safe_id(&c.id) || !claims.insert(c.id.clone()) || c.evidence_ids.is_empty() {
                return quarantine("CLAIM_WITHOUT_EVIDENCE");
            }
            for id in &c.evidence_ids {
                let e = match self.state.evidence.get(id) {
                    Some(e) => e,
                    None => return quarantine("UNREGISTERED_EVIDENCE"),
                };
                if e.claim_id != c.id {
                    return quarantine("EVIDENCE_CLAIM_MISMATCH");
                }
                if !self.evidence_content_valid(e) {
                    return quarantine("EVIDENCE_BLOB_MISSING_OR_CORRUPT");
                }
                if e.status != "SUPPORTED" {
                    return quarantine("UNKNOWN_OR_CONFLICTING_EVIDENCE");
                }
            }
        }
        if p.human_effect || !readonly(&p.tool) {
            for (kind, id, dims) in [
                ("verification", &p.assessment_ids.verification, &[][..]),
                ("qse", &p.assessment_ids.qse, QSE),
                ("truthfulness", &p.assessment_ids.truthfulness, &[][..]),
                ("human_effect", &p.assessment_ids.human_effect, HEC),
            ] {
                if let Err(e) = self.review(p, kind, id, dims) {
                    return quarantine(&e);
                }
            }
        }
        (
            "ALLOW".into(),
            vec!["BOUNDED_AUTHORITY_AND_APPLICABLE_CHECKS_PASSED".into()],
            chain,
            resource,
        )
    }
    fn execute_tool(&mut self, p: &Proposal) -> Result<Value, String> {
        match p.tool.as_str() {
            "calculator" => {
                let a = p.args["a"].as_f64().unwrap();
                let b = p.args["b"].as_f64().unwrap();
                let value = match p.args["op"].as_str().unwrap() {
                    "add" => a + b,
                    "subtract" => a - b,
                    "multiply" => a * b,
                    _ => a / b,
                };
                if !value.is_finite() {
                    return Err("nonfinite arithmetic result".into());
                }
                Ok(json!({"value":value}))
            }
            "sandbox_read" => {
                let path = self.sandbox.join(p.args["path"].as_str().unwrap());
                let f = nofollow_read(&path).map_err(|e| e.to_string())?;
                let metadata = f.metadata().map_err(|e| e.to_string())?;
                if !metadata.is_file() || metadata.nlink() != 1 {
                    return Err("not a single-link regular sandbox file".into());
                }
                let mut bytes = Vec::new();
                f.take(8193)
                    .read_to_end(&mut bytes)
                    .map_err(|e| e.to_string())?;
                if bytes.len() > 8192 {
                    return Err("read limit exceeded".into());
                }
                let content = String::from_utf8(bytes).map_err(|e| e.to_string())?;
                Ok(json!({"content":content}))
            }
            "sandbox_write" => {
                let path = self.sandbox.join(p.args["path"].as_str().unwrap());
                if let Ok(m) = fs::symlink_metadata(&path) {
                    if !m.is_file() || m.file_type().is_symlink() || m.nlink() != 1 {
                        return Err("unsafe existing sandbox target".into());
                    }
                }
                atomic_write(&path, p.args["content"].as_str().unwrap().as_bytes())
                    .map_err(|e| e.to_string())?;
                Ok(
                    json!({"written":p.args["content"].as_str().unwrap().len(),"path":p.args["path"]}),
                )
            }
            "mock_email" => Ok(json!({"sent":false,"mock_only":true,"record":p.args})),
            "mock_ledger" => {
                let f = p.args["from"].as_str().unwrap();
                let t = p.args["to"].as_str().unwrap();
                let a = p.args["amount_cents"].as_i64().unwrap();
                if self.state.ledger[f] < a {
                    return Err("insufficient mock funds".into());
                }
                let credit = self.state.ledger[t]
                    .checked_add(a)
                    .ok_or("ledger overflow")?;
                *self.state.ledger.get_mut(f).unwrap() -= a;
                *self.state.ledger.get_mut(t).unwrap() = credit;
                Ok(json!({"mock_only":true,"balances":self.state.ledger}))
            }
            _ => Err("tool absent".into()),
        }
    }
    fn request(&mut self, v: Value) -> Value {
        let operation = v.get("operation").and_then(Value::as_str).unwrap_or("");
        if !matches!(operation, "status" | "digest" | "receipt_check")
            && self.state.sequence >= self.policy.max_journal_receipts
        {
            return json!({"ok":false,"decision":"DENY","reasons":["GLOBAL_DURABLE_DECISION_BUDGET_EXHAUSTED"]});
        }
        match operation {
            "status" => {
                json!({"ok":true,"policy_version":self.policy.version,"policy_hash":self.state.policy_hash,"source_status":self.policy.status,"bound_actor":self.bound_actor,"sequence":self.state.sequence,"recovery_required":self.state.pending.is_some(),"tools":["calculator","sandbox_read","sandbox_write","mock_email","mock_ledger"],"boundary":"external deterministic gate; OS isolation supplied by deployment"})
            }
            "digest" | "evaluate" | "execute" => {
                let p: Proposal = match serde_json::from_value(
                    v.get("proposal").cloned().unwrap_or(Value::Null),
                ) {
                    Ok(p) => p,
                    Err(e) => {
                        return json!({"ok":false,"decision":"DENY","reasons":[format!("INVALID_PROPOSAL: {e}")]})
                    }
                };
                if operation == "digest" {
                    return json!({"ok":true,"proposal_digest":digest(&p)});
                }
                if !safe_id(&p.id)
                    || !safe_id(&p.nonce)
                    || !safe_id(&p.actor_id)
                    || !safe_id(&p.delegation_id)
                    || p.policy_version.len() > 128
                    || p.tool.len() > 128
                    || p.claims.len() > 32
                    || p.unknowns.len() > 32
                    || p.unknowns.iter().any(|u| u.len() > 1024)
                    || p.claims.iter().any(|c| {
                        !safe_id(&c.id)
                            || c.evidence_ids.len() > 32
                            || c.evidence_ids.iter().any(|e| !safe_id(e))
                    })
                {
                    return json!({"ok":false,"decision":"DENY","reasons":["MALFORMED_PROPOSAL_BOUNDS"]});
                }
                if p.actor_id != self.bound_actor {
                    return json!({"ok":false,"decision":"DENY","reasons":["INGRESS_PRINCIPAL_MISMATCH"]});
                }
                let (mut decision, mut reasons, chain, resource) = self.evaluate(&p, false);
                if operation == "evaluate" {
                    return json!({"ok":true,"decision":decision,"reasons":reasons,"proposal_digest":digest(&p),"dry_run":true});
                }
                let pending_before = self.state.pending.clone();
                if p.actor_id == self.bound_actor {
                    self.state.used_ids.insert(p.id.clone());
                    self.state.used_nonces.insert(p.nonce.clone());
                    *self
                        .state
                        .actor_attempts
                        .entry(p.actor_id.clone())
                        .or_default() += 1;
                }
                if self.state.pending.is_none() {
                    self.state.pending = Some(p.id.clone())
                }
                if let Err(e) = self.save() {
                    return json!({"ok":false,"decision":"QUARANTINE","reasons":[format!("DURABILITY_FAILURE: {e}")]});
                }
                let mut result = Value::Null;
                if decision == "ALLOW" {
                    for id in chain {
                        let u = self.state.usages.entry(id).or_default();
                        u.calls += 1;
                        u.resources = u.resources.saturating_add(resource)
                    }
                    self.state.pending = Some(p.id.clone());
                    if let Err(e) = self.save() {
                        return json!({"ok":false,"decision":"QUARANTINE","reasons":[format!("DURABILITY_FAILURE: {e}")]});
                    }
                    let (final_decision, final_reasons, _, _) = self.evaluate(&p, true);
                    if final_decision != "ALLOW" {
                        decision = final_decision;
                        reasons = final_reasons;
                    } else {
                        result = match self.execute_tool(&p) {
                            Ok(r) => r,
                            Err(e) => {
                                decision = "DENY".into();
                                reasons = vec!["TOOL_FAILED".into()];
                                json!({"error":e})
                            }
                        };
                        if !readonly(&p.tool) {
                            if let Err(e) = self.save() {
                                return json!({"ok":false,"decision":"QUARANTINE","reasons":[format!("EFFECT_STATE_DURABILITY_FAILURE: {e}")]});
                            }
                        }
                    }
                }
                let receipt = match self.receipt(&p, &decision, &reasons, &result) {
                    Ok(r) => r,
                    Err(e) => {
                        return json!({"ok":false,"decision":"QUARANTINE","reasons":[format!("RECEIPT_DURABILITY_FAILURE: {e}")]})
                    }
                };
                self.state.pending = pending_before;
                if let Err(e) = self.save() {
                    self.state.pending = Some("durability-failure".into());
                    return json!({"ok":false,"decision":"QUARANTINE","reasons":[format!("STATE_DURABILITY_FAILURE: {e}")],"receipt":receipt});
                }
                json!({"ok":true,"decision":decision,"reasons":reasons,"result":result,"receipt":receipt})
            }
            "receipt_check" => {
                let r = v.get("receipt").unwrap_or(&Value::Null);
                let payload = r.get("payload").unwrap_or(&Value::Null);
                let bytes = serde_json::to_vec(payload).unwrap();
                let valid = valid_mac(
                    &self.receipt_key,
                    &bytes,
                    r.get("hmac").and_then(Value::as_str).unwrap_or(""),
                ) && r.get("hash").and_then(Value::as_str)
                    == Some(sha(&bytes).as_str());
                json!({"ok":true,"valid":valid,"semantics":"Authenticates record integrity only; does not prove evidence truth"})
            }
            "register_assessment" | "register_evidence" | "revoke" => {
                if !self.authorized_control(&v) {
                    return json!({"ok":false,"decision":"DENY","reasons":["CONTROL_AUTHENTICATION_REQUIRED"]});
                }
                if operation == "register_assessment" {
                    let a: Assessment = match serde_json::from_value(
                        v.get("assessment").cloned().unwrap_or(Value::Null),
                    ) {
                        Ok(a) => a,
                        Err(e) => return json!({"ok":false,"error":e.to_string()}),
                    };
                    if self.state.assessments.len() >= 1000
                        || !safe_id(&a.id)
                        || self.state.assessments.contains_key(&a.id)
                        || !self
                            .policy
                            .identities
                            .iter()
                            .any(|i| i.id == a.reviewer_id && i.role == "verifier" && i.active)
                        || !matches!(
                            a.kind.as_str(),
                            "verification" | "qse" | "truthfulness" | "human_effect"
                        )
                        || !matches!(a.status.as_str(), "PASS" | "FAIL" | "UNKNOWN")
                        || a.policy_version != self.policy.version
                        || a.expires_at <= now()
                        || a.proposal_digest.len() != 64
                        || !a.proposal_digest.bytes().all(|b| b.is_ascii_hexdigit())
                    {
                        return json!({"ok":false,"decision":"DENY","reasons":["INVALID_ASSESSMENT_REGISTRATION"]});
                    }
                    self.state.assessments.insert(a.id.clone(), a);
                } else if operation == "register_evidence" {
                    let e: Evidence = match serde_json::from_value(
                        v.get("evidence").cloned().unwrap_or(Value::Null),
                    ) {
                        Ok(e) => e,
                        Err(e) => return json!({"ok":false,"error":e.to_string()}),
                    };
                    if self.state.evidence.len() >= 1000
                        || !safe_id(&e.id)
                        || !safe_id(&e.claim_id)
                        || self.state.evidence.contains_key(&e.id)
                        || !matches!(e.status.as_str(), "SUPPORTED" | "CONFLICTING" | "UNKNOWN")
                        || e.content_sha256.len() != 64
                        || !e.content_sha256.bytes().all(|b| b.is_ascii_hexdigit())
                        || e.source_anchor.is_empty()
                    {
                        return json!({"ok":false,"decision":"DENY","reasons":["INVALID_EVIDENCE_REGISTRATION"]});
                    }
                    let content = match v.get("content").and_then(Value::as_str) {
                        Some(c) => c,
                        None => {
                            return json!({"ok":false,"decision":"DENY","reasons":["EVIDENCE_CONTENT_REQUIRED"]})
                        }
                    };
                    if let Err(error) = self.store_evidence(&e, content) {
                        return json!({"ok":false,"decision":"DENY","reasons":[error]});
                    }
                    self.state.evidence.insert(e.id.clone(), e);
                } else {
                    let id = v.get("delegation_id").and_then(Value::as_str).unwrap_or("");
                    if !self.policy.delegations.iter().any(|d| d.id == id)
                        && !self.policy.authorities.iter().any(|a| a.id == id)
                    {
                        return json!({"ok":false,"decision":"DENY","reasons":["UNKNOWN_REVOCATION_TARGET"]});
                    }
                    self.state.revoked.insert(id.into());
                }
                match self.save() {
                    Ok(_) => json!({"ok":true}),
                    Err(e) => json!({"ok":false,"decision":"QUARANTINE","error":e}),
                }
            }
            "invalid_json" => {
                json!({"ok":false,"decision":"DENY","reasons":["INVALID_JSON_OR_DUPLICATE_KEY"]})
            }
            "oversized_wire_frame" => {
                json!({"ok":false,"decision":"DENY","reasons":["REQUEST_SIZE_LIMIT"]})
            }
            _ => json!({"ok":false,"decision":"DENY","reasons":["UNKNOWN_OPERATION"]}),
        }
    }
}
use std::os::unix::fs::MetadataExt;
fn bounded_context(value: &Value, path: &[&str]) -> Value {
    let mut item = value;
    for key in path {
        item = match item.get(*key) {
            Some(v) => v,
            None => return Value::Null,
        }
    }
    item.as_str()
        .filter(|s| s.len() <= 128)
        .map(|s| json!(s))
        .unwrap_or(Value::Null)
}
fn default_depth() -> usize {
    5
}
fn default_decisions() -> u64 {
    10000
}
// Value deserialization normally collapses duplicate keys; this parser rejects them at every depth.
struct UniqueJson(Value);
impl<'de> Deserialize<'de> for UniqueJson {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct UniqueVisitor;
        impl<'de> Visitor<'de> for UniqueVisitor {
            type Value = UniqueJson;
            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("JSON with unique object keys")
            }
            fn visit_bool<E: de::Error>(self, v: bool) -> Result<UniqueJson, E> {
                Ok(UniqueJson(Value::Bool(v)))
            }
            fn visit_i64<E: de::Error>(self, v: i64) -> Result<UniqueJson, E> {
                Ok(UniqueJson(json!(v)))
            }
            fn visit_u64<E: de::Error>(self, v: u64) -> Result<UniqueJson, E> {
                Ok(UniqueJson(json!(v)))
            }
            fn visit_f64<E: de::Error>(self, v: f64) -> Result<UniqueJson, E> {
                serde_json::Number::from_f64(v)
                    .map(|n| UniqueJson(Value::Number(n)))
                    .ok_or_else(|| E::custom("nonfinite number"))
            }
            fn visit_str<E: de::Error>(self, v: &str) -> Result<UniqueJson, E> {
                Ok(UniqueJson(Value::String(v.into())))
            }
            fn visit_string<E: de::Error>(self, v: String) -> Result<UniqueJson, E> {
                Ok(UniqueJson(Value::String(v)))
            }
            fn visit_none<E: de::Error>(self) -> Result<UniqueJson, E> {
                Ok(UniqueJson(Value::Null))
            }
            fn visit_unit<E: de::Error>(self) -> Result<UniqueJson, E> {
                Ok(UniqueJson(Value::Null))
            }
            fn visit_seq<A: SeqAccess<'de>>(self, mut access: A) -> Result<UniqueJson, A::Error> {
                let mut values = Vec::new();
                while let Some(v) = access.next_element::<UniqueJson>()? {
                    values.push(v.0)
                }
                Ok(UniqueJson(Value::Array(values)))
            }
            fn visit_map<A: MapAccess<'de>>(self, mut access: A) -> Result<UniqueJson, A::Error> {
                let mut values = serde_json::Map::new();
                while let Some(key) = access.next_key::<String>()? {
                    if values.contains_key(&key) {
                        return Err(de::Error::custom("duplicate JSON object key"));
                    }
                    let v = access.next_value::<UniqueJson>()?;
                    values.insert(key, v.0);
                }
                Ok(UniqueJson(Value::Object(values)))
            }
        }
        deserializer.deserialize_any(UniqueVisitor)
    }
}
fn parse_strict_json(bytes: &[u8]) -> Result<Value, serde_json::Error> {
    serde_json::from_slice::<UniqueJson>(bytes).map(|v| v.0)
}
fn main() {
    let mut args = std::env::args().skip(1);
    let mut policy = None;
    let mut state = None;
    let mut sandbox = None;
    while let Some(a) = args.next() {
        match a.as_str() {
            "--policy" => policy = args.next(),
            "--state-dir" => state = args.next(),
            "--sandbox-dir" => sandbox = args.next(),
            _ => {
                eprintln!("unknown argument");
                std::process::exit(2)
            }
        }
    }
    let fail = |s: &str| -> ! {
        eprintln!("garden-gate: {s}");
        std::process::exit(2)
    };
    let receipt_key =
        std::env::var("GARDEN_RECEIPT_KEY").unwrap_or_else(|_| fail("GARDEN_RECEIPT_KEY missing"));
    let control_key = std::env::var("GARDEN_CONTROL_TOKEN")
        .unwrap_or_else(|_| fail("GARDEN_CONTROL_TOKEN missing"));
    if receipt_key.len() < 32 || control_key.len() < 32 || receipt_key == control_key {
        fail("separate keys of at least 32 bytes required")
    }
    let mut gate = Gate::load(
        Path::new(&policy.unwrap_or_else(|| fail("--policy required"))),
        Path::new(&state.unwrap_or_else(|| fail("--state-dir required"))),
        Path::new(&sandbox.unwrap_or_else(|| fail("--sandbox-dir required"))),
        receipt_key.into_bytes(),
        control_key.into_bytes(),
    )
    .unwrap_or_else(|e| fail(&e));
    let stdin = io::stdin();
    let mut input = stdin.lock();
    let mut output = io::stdout().lock();
    loop {
        let mut line = Vec::new();
        let n = input
            .by_ref()
            .take((gate.policy.max_request_bytes + 2) as u64)
            .read_until(b'\n', &mut line);
        match n {
            Ok(0) => break,
            Ok(_) => {}
            Err(_) => break,
        };
        if line.len() > gate.policy.max_request_bytes {
            let denied = gate
                .process(json!({"operation":"oversized_wire_frame","raw_input_digest":sha(&line),"truncated":!line.ends_with(b"\n"),"bytes_seen":line.len()}));
            let _ = writeln!(output, "{}", denied);
            let _ = output.flush();
            break;
        }
        let result = match parse_strict_json(&line) {
            Ok(v) => gate.process(v),
            Err(_) => {
                gate.process(json!({"operation":"invalid_json","raw_input_digest":sha(&line),"truncated":false,"bytes_seen":line.len()}))
            }
        };
        if writeln!(output, "{}", result).is_err() || output.flush().is_err() {
            break;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn identifiers_reject_paths() {
        assert!(!filename("../policy"));
        assert!(!filename("a/b"));
        assert!(!filename(".secret"));
        assert!(filename("work_1"));
    }
    #[test]
    fn hmac_is_authenticated() {
        let k = b"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        let s = mac(k, b"record");
        assert!(valid_mac(k, b"record", &s));
        assert!(!valid_mac(k, b"changed", &s));
        assert!(!valid_mac(k, b"record", &format!("aé{}", "a".repeat(61))));
    }
    #[test]
    fn ambiguous_json_is_rejected() {
        assert!(parse_strict_json(br#"{"operation":"execute","operation":"status"}"#).is_err());
        assert!(parse_strict_json(br#"{"args":{"a":1,"a":2}}"#).is_err());
        assert!(parse_strict_json(br#"{"args":{"a":1}}"#).is_ok());
    }
    #[test]
    fn digest_excludes_only_assessment_refs() {
        let mut p:Proposal=serde_json::from_value(json!({"id":"j","nonce":"n","actor_id":"a","delegation_id":"d","policy_version":"v","tool":"calculator","args":{"op":"add","a":1,"b":2},"claims":[],"unknowns":[],"human_effect":false,"assessment_ids":{},"successor_of":null})).unwrap();
        let d = digest(&p);
        p.assessment_ids.verification = Some("v".into());
        assert_eq!(d, digest(&p));
        p.args["a"] = json!(3);
        assert_ne!(d, digest(&p));
    }
}
