"""A serialized transport to the external Rust gate, never an agent tool runner.

The gate process owns its policy, effect adapters and receipt state. Untrusted
agent providers receive neither this object nor its environment/credentials.
"""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


class GateBroker:
    def __init__(self, command: list[str], *, control_token: str, receipt_key: str,
                 cwd: Path, extra_env: dict[str, str] | None = None):
        self._lock = threading.Lock()
        self._control_token = control_token
        clean_env = {k: os.environ[k] for k in ("PATH", "LANG", "TZ") if k in os.environ}
        clean_env.update(extra_env or {})
        clean_env.update(GARDEN_CONTROL_TOKEN=control_token, GARDEN_RECEIPT_KEY=receipt_key)
        self.process = subprocess.Popen(command, cwd=cwd, env=clean_env,
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, bufsize=0)
        os.set_blocking(self.process.stdin.fileno(), False)
        self._buffer = bytearray()

    def request(self, payload: dict[str, Any], *, trusted: bool = False, timeout: float = 10) -> dict[str, Any]:
        """Only controller code calls trusted=True; HTTP body cannot select it."""
        request = dict(payload)
        if trusted:
            request["control_token"] = self._control_token
        wire = json.dumps(request, allow_nan=False, separators=(",", ":")).encode() + b"\n"
        if len(wire) > 65536:
            raise ValueError("request exceeds gate transport limit")
        with self._lock:
            if self.process.poll() is not None:
                raise RuntimeError("gate process stopped; authority unavailable")
            selector = selectors.DefaultSelector()
            selector.register(self.process.stdout, selectors.EVENT_READ)
            selector.register(self.process.stdin, selectors.EVENT_WRITE)
            sent = 0
            deadline = time.monotonic() + timeout
            try:
                while sent < len(wire) or b"\n" not in self._buffer:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self.close()
                        raise TimeoutError("gate response timed out; session closed")
                    events = selector.select(remaining)
                    if not events:
                        self.close()
                        raise TimeoutError("gate response timed out; session closed")
                    for key, _ in events:
                        if key.fileobj is self.process.stdin:
                            try:
                                sent += os.write(self.process.stdin.fileno(), wire[sent:sent + 4096])
                            except BlockingIOError:
                                continue
                            except BrokenPipeError as error:
                                self.close()
                                raise RuntimeError("gate request stream unavailable") from error
                            if sent == len(wire):
                                selector.unregister(self.process.stdin)
                            continue
                        chunk = os.read(self.process.stdout.fileno(), 65536)
                        if not chunk:
                            self.close()
                            raise RuntimeError("gate response unavailable")
                        self._buffer.extend(chunk)
                        if len(self._buffer) > 262144:
                            self.close()
                            raise RuntimeError("gate response exceeds transport limit")
                line, _, tail = self._buffer.partition(b"\n")
                self._buffer = bytearray(tail)
                answer = json.loads(line)
                if not isinstance(answer, dict):
                    raise RuntimeError("invalid gate response")
                return answer
            finally:
                selector.close()

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout):
            if stream is not None and not stream.closed:
                stream.close()
