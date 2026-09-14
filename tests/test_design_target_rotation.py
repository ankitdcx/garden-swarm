from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from tools.rotate_design_review_target import select_target


ROOT = Path(__file__).resolve().parents[1]


class DesignTargetRotationTests(unittest.TestCase):
    def setUp(self):
        self.matrix = json.loads(
            (ROOT / "agents/design-review-matrix.json").read_text(encoding="utf-8")
        )

    def test_consecutive_hours_rotate_when_multiple_targets_exist(self):
        self.assertGreaterEqual(len(self.matrix["targets"]), 2)
        first = select_target(copy.deepcopy(self.matrix), 0)
        second = select_target(copy.deepcopy(self.matrix), 1)
        self.assertNotEqual(first["target_id"], second["target_id"])

    def test_rotation_is_deterministic_and_cycles_exactly(self):
        count = len(self.matrix["targets"])
        for slot in range(count * 2):
            selected = select_target(copy.deepcopy(self.matrix), slot)
            expected = self.matrix["targets"][slot % count]
            self.assertEqual(selected["target_id"], expected["target_id"])

    def test_selection_mutates_only_runtime_active_metadata(self):
        candidate = copy.deepcopy(self.matrix)
        target = select_target(candidate, 7)
        self.assertEqual(candidate["active_target_id"], target["target_id"])
        self.assertEqual(candidate["active_target_hour_slot"], 7)
        self.assertIn("Scheduling evidence only", candidate["active_target_selection_reason"])
        self.assertFalse(candidate["semantic_compliance_proved"])
        self.assertEqual(candidate["canonical_source_root_sha256"], self.matrix["canonical_source_root_sha256"])
        self.assertEqual(candidate["design_epoch"], self.matrix["design_epoch"])

    def test_negative_slot_is_rejected(self):
        with self.assertRaises(ValueError):
            select_target(copy.deepcopy(self.matrix), -1)


if __name__ == "__main__":
    unittest.main()
