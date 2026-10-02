"""Independent persistent gate-transport regressions; no mocked policy checks."""
import importlib.util
import os
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("independent_gate_broker", ROOT / "garden-console/broker.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fake_broker(script):
    return module.GateBroker([sys.executable, "-c", script], control_token="test-control-" + "a" * 32,
                             receipt_key="test-receipt-" + "b" * 32, cwd=ROOT)


class IndependentBrokerBoundaryTests(unittest.TestCase):
    def test_stalled_stdin_has_same_deadline_as_response(self):
        broker = fake_broker("import time;time.sleep(0.8)")
        try:
            if sys.platform.startswith("linux"):
                import fcntl
                fcntl.fcntl(broker.process.stdin.fileno(), fcntl.F_SETPIPE_SZ, 4096)
            started = time.monotonic()
            with self.assertRaisesRegex(TimeoutError, "timed out"):
                broker.request({"operation": "status", "untrusted": "x" * 65000}, timeout=.1)
            self.assertLess(time.monotonic() - started, .6)
            self.assertIsNotNone(broker.process.poll())
        finally:
            broker.close()

    def test_large_frame_and_repeated_responses_progress(self):
        script = "import sys,json\nfor line in sys.stdin:\n print(json.dumps({'ok':True,'received':len(line),'data':'y'*10000}),flush=True)"
        broker = fake_broker(script)
        try:
            for size in (65000, 1, 65000):
                result = broker.request({"operation": "status", "untrusted": "x" * size}, timeout=2)
                self.assertTrue(result["ok"])
                self.assertGreater(result["received"], size)
                self.assertEqual(len(result["data"]), 10000)
        finally:
            broker.close()

    def test_gate_output_flood_closes_session(self):
        broker = fake_broker("import os,sys;sys.stdin.readline();os.write(1,b'x'*1000000)")
        try:
            with self.assertRaisesRegex(RuntimeError, "exceeds transport"):
                broker.request({"operation": "status"}, timeout=2)
            self.assertIsNotNone(broker.process.poll())
        finally:
            broker.close()


if __name__ == "__main__":
    unittest.main()
