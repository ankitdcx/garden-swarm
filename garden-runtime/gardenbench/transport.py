"""Black-box JSON-line transport used only by the independent attack harness."""
from __future__ import annotations

import json
import os
import selectors
import subprocess
import time
from pathlib import Path


class GateTransport:
    def __init__(self, command: list[str], *, cwd: Path, env: dict[str, str]):
        self.process = subprocess.Popen(command, cwd=cwd, env={**os.environ, **env},
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, bufsize=0)
        self.buffer = bytearray()

    def raw(self, data: bytes, timeout: float = 5.0):
        if self.process.poll() is not None:
            raise RuntimeError(f"gate exited: {self.process.returncode}")
        self.process.stdin.write(data + (b"" if data.endswith(b"\n") else b"\n"))
        self.process.stdin.flush()
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while b"\n" not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError("gate did not return bounded response")
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    stderr = self.process.stderr.read().decode(errors="replace")[:1000]
                    raise RuntimeError(f"gate response stream closed: {stderr}")
                self.buffer.extend(chunk)
                if len(self.buffer) > 1048576:
                    raise RuntimeError("oversized gate response")
        line, _, tail = self.buffer.partition(b"\n")
        self.buffer = bytearray(tail)
        result = json.loads(line)
        if not isinstance(result, dict):
            raise AssertionError("response is not an object")
        return result

    def request(self, request: dict):
        return self.raw(json.dumps(request, separators=(",", ":"), allow_nan=False).encode())

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            stream.close()
