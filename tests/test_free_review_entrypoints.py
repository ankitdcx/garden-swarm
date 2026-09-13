from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FreeReviewEntrypointTests(unittest.TestCase):
    def test_review_modules_load_without_provider_call(self):
        for module in ("tools.free_design_review", "tools.free_repo_review"):
            with self.subTest(module=module):
                proc = subprocess.run(
                    [sys.executable, "-m", module, "--help"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("--selection", proc.stdout)
                self.assertIn("--output", proc.stdout)


if __name__ == "__main__":
    unittest.main()
