"""The admitted continuation wake is recovery-only; it cannot create review work."""
from pathlib import Path
import re
import unittest


class SingleSchedulerTests(unittest.TestCase):
    def test_paid_ip_reviews_do_not_run_on_repository_events(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('ip-origin-multi-agent-review', 'one-use-ip-provenance-deepseek-review'):
            text = (root / f'.github/workflows/{name}.yml').read_text(encoding='utf-8')
            with self.subTest(workflow=name):
                self.assertIn('workflow_dispatch:', text)
                triggers = text.split('\non:\n', 1)[1].split('\npermissions:', 1)[0]
                self.assertIsNone(re.search(r'^\s*(pull_request|pull_request_target|push|schedule|workflow_run)\s*:', triggers, re.MULTILINE))
                self.assertNotIn('if: github.event.pull_request.head.repo', text)

    def test_no_repository_workflow_adds_an_independent_timer(self):
        root = Path(__file__).resolve().parents[1]
        for path in sorted((root / '.github/workflows').glob('*.y*ml')):
            with self.subTest(workflow=path.name):
                text = path.read_text(encoding='utf-8')
                if path.name == 'continue-openrouter-review.yml':
                    self.assertIn("cron: '17 1 * * *'", text)
                    self.assertNotIn('OPENROUTER_API_KEY', text)
                    self.assertIn('tools.independent_branch_continuation', text)
                    self.assertIn('Recovery only', text)
                    self.assertIn('INDEPENDENT_BRANCH_CONVERGENCE_V1', text)
                else:
                    self.assertIsNone(re.search(r'^\s*schedule\s*:', text, re.MULTILINE))

    def test_retired_timers_remain_dispatchable(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('hourly-free-agent-review', 'hourly-specialist-agent-sweep', 'branch-lifecycle'):
            text = (root / f'.github/workflows/{name}.yml').read_text(encoding='utf-8')
            self.assertIn('workflow_dispatch:', text)


if __name__ == '__main__':
    unittest.main()
