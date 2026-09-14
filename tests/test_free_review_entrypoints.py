from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


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

    def test_matrix_selector_allows_one_execution_budget_family_without_changing_quorum(self):
        from tools import select_matrix_reviewers

        selected = [{"family": "example", "model": "example/model:free"}]
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False), \
             mock.patch.object(sys, "argv", ["select_matrix_reviewers", "--count", "1", "--slot", "7", "--output", str(Path(tmp) / "selection.json")]), \
             mock.patch.object(select_matrix_reviewers, "catalog", return_value=selected), \
             mock.patch.object(select_matrix_reviewers, "choose", return_value=selected):
            self.assertEqual(select_matrix_reviewers.main(), 0)
            payload = json.loads((Path(tmp) / "selection.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["required_family_count"], 1)
        self.assertEqual(payload["selection_scope"], "EXECUTION_BUDGET_ONLY_NOT_ADMISSION_QUORUM")
        self.assertEqual(len(payload["selected"]), 1)


if __name__ == "__main__":
    unittest.main()
