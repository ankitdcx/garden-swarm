import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from swarm.orchestrator import build_work_items, chunk_text, load_roles


class SwarmPlannerTests(unittest.TestCase):
    def test_chunking_is_deterministic_and_bounded(self):
        text = "a" * 30 + "\n\n" + "b" * 30 + "\n\n" + "c" * 30
        a = chunk_text(text, 50)
        b = chunk_text(text, 50)
        self.assertEqual(a, b)
        self.assertTrue(all(len(x) <= 50 for x in a))

    def test_source_hash_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "x.txt").write_text("alpha\n\nbeta", encoding="utf-8")
            items = build_work_items(root, ["x.txt"], 100)
            self.assertEqual(len(items), 1)
            self.assertEqual(len(items[0].source_sha256), 64)

    def test_roles_unique(self):
        roles_path = Path(__file__).resolve().parents[1] / "roles.json"
        roles = load_roles(roles_path, "all")
        self.assertEqual(len({r.id for r in roles}), len(roles))


if __name__ == "__main__":
    unittest.main()
