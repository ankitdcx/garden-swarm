"""Bounded inference adapters. Model output is always untrusted advisory text.

Deploy this worker under a separate UID/container, without gate files/secrets.
No API here can evaluate/execute a tool or register authoritative assessments.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import pwd
import selectors
import signal
import subprocess
import time
import urllib.request
import urllib.parse

class BackendError(RuntimeError):
    pass

def bounded_process(command, *, timeout, env, cwd, privilege=None):
    """Bound stdout/stderr while running, kill the process group on any failure."""
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, cwd=cwd, start_new_session=True, **(privilege or {}))
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": 65536, "stderr": 16384}
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BackendError("local inference timeout")
            for key, _ in selector.select(min(remaining, 0.25)):
                chunk = os.read(key.fileobj.fileno(), 4096)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = key.data
                if len(buffers[target]) + len(chunk) > limits[target]:
                    raise BackendError("local inference " + target + " limit exceeded")
                buffers[target].extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BackendError("local inference timeout")
        returncode = process.wait(timeout=remaining)
        return returncode, buffers["stdout"].decode("utf-8", errors="strict")
    finally:
        selector.close()
        # Kill any lingering descendant in the private process group as well.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        process.stderr.close()

def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

@dataclass
class RuleBasedBackend:
    family: str = "deterministic-rules"
    model: str = "garden-advisory-rules-v1"
    lineage: str = "garden-advisory-rules-v1"
    cognition: str = "RULE_BASED"

    def generate(self, prompt, max_tokens=256):
        return "No language model available. Apply the explicit task/tool contract, preserve UNKNOWN, and submit the proposal to the external gate."

class LlamaCppBackend:
    cognition = "OPEN_WEIGHT_LLM"

    def __init__(self, binary, model_path, model_id, family, timeout=90, max_tokens=256, unprivileged=True):
        self.binary = str(Path(binary).resolve(strict=True))
        self.model_path = str(Path(model_path).resolve(strict=True))
        self.model, self.family = model_id, family
        self.timeout, self.max_tokens = min(float(timeout), 180), min(int(max_tokens), 512)
        if self.timeout <= 0 or self.max_tokens < 1 or not Path(self.binary).is_file() or not Path(self.model_path).is_file():
            raise BackendError("invalid bounded backend configuration")
        self.lineage = "gguf-sha256:" + self._file_digest(self.model_path)
        self.unprivileged = unprivileged

    @staticmethod
    def _file_digest(path):
        h = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def generate(self, prompt, max_tokens=256):
        if not isinstance(prompt, str) or len(prompt.encode()) > 16384:
            raise BackendError("prompt limit exceeded")
        if self.family in {"SmolLM2", "Qwen3", "Qwen3.5"}:
            prompt = "<|im_start|>system\nYou are a helpful advisory assistant. You can reason, calculate and summarize. Your text is a draft.\n<|im_end|>\n<|im_start|>user\n" + prompt + "<|im_end|>\n<|im_start|>assistant\n"
            if self.family in {"Qwen3", "Qwen3.5"}:
                prompt += "<think>\n\n</think>\n\n"
        command = [self.binary, "-m", self.model_path, "-p", prompt, "-n", str(min(max_tokens, self.max_tokens)), "-c", "2048", "-t", "2", "--temp", "0", "--seed", "0", "--no-display-prompt", "--no-conversation", "--no-warmup"]
        # Clean env drops every control token, API key and Python customization.
        env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "OMP_NUM_THREADS": "2"}
        # Read-only executable/model may reside next to their bundled libraries.
        env["LD_LIBRARY_PATH"] = str(Path(self.binary).parent)
        privilege = {}
        if self.unprivileged and os.geteuid() == 0:
            account = pwd.getpwnam("nobody")
            privilege = {"user": account.pw_uid, "group": account.pw_gid, "extra_groups": []}
        try:
            returncode, stdout = bounded_process(command, timeout=self.timeout, env=env, cwd="/tmp", privilege=privilege)
        except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
            raise BackendError("local inference unavailable or timeout") from exc
        if returncode:
            # Do not relay arbitrary model stderr / operator filesystem paths.
            raise BackendError("local inference failed, code=" + str(returncode))
        return stdout.replace("[end of text]", "").strip()

class OllamaBackend:
    cognition = "OPEN_WEIGHT_LLM"

    def __init__(self, model, family, endpoint="http://127.0.0.1:11434", timeout=60):
        parsed = urllib.parse.urlparse(endpoint)
        # Remote provider billing/auth is deliberately unsupported.
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.path not in {"", "/"}:
            raise BackendError("Ollama endpoint must be local loopback HTTP")
        if not isinstance(model, str) or not model or len(model) > 128:
            raise BackendError("invalid model identifier")
        self.endpoint, self.timeout = endpoint.rstrip("/"), min(float(timeout), 120)
        self.model, self.family = model, family
        self.lineage = "ollama-name:" + model + ":UNPINNED"

    def generate(self, prompt, max_tokens=256):
        if len(prompt.encode()) > 16384:
            raise BackendError("prompt limit exceeded")
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0, "num_predict": min(int(max_tokens), 512), "num_ctx": 2048}}).encode()
        request = urllib.request.Request(self.endpoint + "/api/generate", data=body, headers={"Content-Type": "application/json"})
        try:
            # Disable ambient proxy settings for the loopback model connection.
            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=self.timeout) as response:
                raw = response.read(65537)
            if len(raw) > 65536:
                raise BackendError("model output limit exceeded")
            output = json.loads(raw)["response"]
            if not isinstance(output, str):
                raise BackendError("invalid inference response")
            return output
        except (OSError, ValueError, KeyError) as exc:
            raise BackendError("local Ollama inference unavailable") from exc
