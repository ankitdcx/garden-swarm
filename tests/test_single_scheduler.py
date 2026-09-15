"""The admitted Coordinator owns periodic work across both platforms."""
from pathlib import Path
import re
import unittest


class SingleSchedulerTests(unittest.TestCase):
    def test_no_repository_workflow_adds_an_independent_timer(self):
        root = Path(__file__).resolve().parents[1]
        for path in sorted((root / '.github/workflows').glob('*.y*ml')):
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding='utf-8')
                self.assertIsNone(re.search(r'^\s*schedule\s*:', text, re.MULTILINE))

    def test_retired_timers_remain_dispatchable(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('hourly-free-agent-review', 'hourly-specialist-agent-sweep', 'branch-lifecycle'):
            text = (root / f'.github/workflows/{name}.yml').read_text(encoding='utf-8')
            self.assertIn('workflow_dispatch:', text)
