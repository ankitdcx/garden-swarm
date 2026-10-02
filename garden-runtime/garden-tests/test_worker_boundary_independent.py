"""Independent pipe-deadlock regression for a compromised inference child."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("independent_bounded_process", ROOT / "garden-console/bounded_process.py")
bounded = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bounded)


class IndependentWorkerBoundaryTests(unittest.TestCase):
    def test_child_ignoring_large_stdin_cannot_escape_timeout(self):
        started = time.monotonic()
        with self.assertRaisesRegex(TimeoutError, "time limit"):
            bounded.bounded_run([sys.executable, "-c", "import time;time.sleep(0.8)"],
                                b"x" * 100000, cwd=ROOT,
                                env={"PATH": os.environ.get("PATH", "")}, timeout=.1)
        self.assertLess(time.monotonic() - started, .6)

    def test_json_expansion_can_exceed_pipe_capacity_under_http_body_limit(self):
        # A legitimate UTF-8 HTTP size cap does not bound ensure_ascii=True
        # reserialization sent to a child pipe. The pipe writer must be bounded.
        request = {"task": "😀" * 2000, "tool": "mock_email",
                   "args": {"to": "user@invalid.test", "subject": "😀" * 2000, "body": "😀" * 2000},
                   "consent": True}
        self.assertLess(len(json.dumps(request, ensure_ascii=False).encode()), 32768)
        self.assertGreater(len(json.dumps(request).encode()), 65536)

    def test_bidirectional_pipe_progress_does_not_deadlock(self):
        script = "import os,sys;os.write(1,b'y'*200000);data=sys.stdin.buffer.read();os.write(1,('READ'+str(len(data))).encode())"
        code, output, error = bounded.bounded_run([sys.executable, "-c", script], b"x" * 100000,
                                                  cwd=ROOT, env={"PATH": os.environ.get("PATH", "")},
                                                  timeout=2, stdout_limit=300000)
        self.assertEqual(code, 0)
        self.assertTrue(output.endswith(b"READ100000"))
        self.assertEqual(error, b"")


if __name__ == "__main__":
    unittest.main()
