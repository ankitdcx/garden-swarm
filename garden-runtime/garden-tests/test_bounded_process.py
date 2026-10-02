import importlib.util
import os
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bounded_process", root / "garden-console/bounded_process.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class BoundedWorkerTests(unittest.TestCase):
    def test_compromised_worker_output_flood_is_killed(self):
        with self.assertRaisesRegex(ValueError, "output limit"):
            module.bounded_run([sys.executable, "-c", "import os;os.write(1,b'x'*2000000)"], b"", cwd=root,
                               env={"PATH": os.environ.get("PATH", "")}, timeout=2, stdout_limit=1024)

    def test_compromised_worker_stall_is_killed(self):
        with self.assertRaisesRegex(TimeoutError, "time limit"):
            module.bounded_run([sys.executable, "-c", "while True: pass"], b"", cwd=root,
                               env={"PATH": os.environ.get("PATH", "")}, timeout=.2)


if __name__ == "__main__": unittest.main()
