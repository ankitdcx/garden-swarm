from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tools.free_model_rotation import choose
from tools.review_quorum import load_target


ROOT = Path(__file__).resolve().parents[1]


class ReviewQuorumOfflineTests(unittest.TestCase):
    def test_review_quorum_cli_loads_without_provider_call(self):
        proc = subprocess.run(
            [sys.executable, "-m", "tools.review_quorum", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--lane", proc.stdout)
        self.assertIn("--output", proc.stdout)

    def test_repo_bootstrap_target_is_exact_and_locally_resolvable(self):
        target, evidence, trace = load_target(ROOT, "repo", 0)
        self.assertEqual(target["target_id"], "REVIEW-QUORUM-INFRASTRUCTURE")
        self.assertTrue(target["target_hash"])
        self.assertTrue(evidence)
        self.assertTrue(trace)
        self.assertTrue(all(row["coverage"] != "MISSING" for row in trace), trace)

    def test_design_matrix_resolves_a_v15_5_target(self):
        target, evidence, trace = load_target(ROOT, "design", 0)
        self.assertEqual(target["target_id"], "GSL-KR")
        self.assertTrue(evidence)
        self.assertTrue(trace)

    def test_free_rotation_can_select_three_distinct_families(self):
        models = [
            {"id": "deepseek/example:free", "context_length": 128000},
            {"id": "qwen/example:free", "context_length": 128000},
            {"id": "meta-llama/example:free", "context_length": 128000},
            {"id": "mistralai/example:free", "context_length": 128000},
        ]
        picked = choose(models, slot=0, count=3)
        self.assertEqual(len(picked), 3)
        self.assertEqual(len({row["family"] for row in picked}), 3)
        self.assertTrue(all(row["model"].endswith(":free") for row in picked))


if __name__ == "__main__":
    unittest.main()
