import unittest

from tools.check_branch_lifecycle import classify_snapshot


class BranchLifecycleCheckTests(unittest.TestCase):
    def base(self, **kwargs):
        data = {
            "repository": "o/r",
            "default_branch": "main",
            "head_sha": "m1",
            "branches": [
                {"name": "main", "commit": {"sha": "m1"}},
                {"name": "feature", "commit": {"sha": "f1"}},
            ],
            "pull_requests": [],
            "retention_exceptions": {},
            "active_branch_budget": 9,
            "observed_at": "2026-09-14T18:00:00Z",
        }
        data.update(kwargs)
        return classify_snapshot(**data)

    def test_open_pr_is_active(self):
        receipt = self.base(pull_requests=[{"number": 7, "state": "open", "merged_at": None, "head": {"ref": "feature"}}])
        self.assertEqual(receipt["dispositions"][0]["disposition"], "ACTIVE")
        self.assertFalse(receipt["dispositions"][0]["destructive_action_authorized"])
        self.assertEqual(receipt["counts"]["active"], 1)

    def test_merged_pr_is_delete_eligible(self):
        receipt = self.base(pull_requests=[{"number": 7, "state": "closed", "merged_at": "2026-09-14T12:00:00Z", "head": {"ref": "feature"}}])
        self.assertEqual(receipt["dispositions"][0]["disposition"], "MERGED_DELETE_ELIGIBLE")
        self.assertTrue(receipt["dispositions"][0]["destructive_action_authorized"])

    def test_closed_unmerged_fails_closed(self):
        receipt = self.base(pull_requests=[{"number": 7, "state": "closed", "merged_at": None, "head": {"ref": "feature"}}])
        self.assertEqual(receipt["dispositions"][0]["disposition"], "CLOSED_UNRESOLVED")
        self.assertFalse(receipt["dispositions"][0]["destructive_action_authorized"])
        self.assertEqual(receipt["status"], "REVIEW_REQUIRED")

    def test_retention_exception_precedes_pr_state(self):
        receipt = self.base(
            pull_requests=[{"number": 7, "state": "closed", "merged_at": "2026-09-14T12:00:00Z", "head": {"ref": "feature"}}],
            retention_exceptions={"feature": {"disposition": "FROZEN", "reason": "freeze"}},
        )
        self.assertEqual(receipt["dispositions"][0]["disposition"], "FROZEN")
        self.assertFalse(receipt["dispositions"][0]["destructive_action_authorized"])

    def test_active_budget_is_enforced(self):
        branches = [{"name": "main", "commit": {"sha": "m1"}}]
        pulls = []
        for i in range(10):
            name = f"b{i}"
            branches.append({"name": name, "commit": {"sha": f"s{i}"}})
            pulls.append({"number": i + 1, "state": "open", "merged_at": None, "head": {"ref": name}})
        receipt = self.base(branches=branches, pull_requests=pulls, active_branch_budget=9)
        self.assertEqual(receipt["budget_check"]["result"], "FAIL")
        self.assertEqual(receipt["status"], "REVIEW_REQUIRED")

    def test_duplicate_commit_is_evidence_not_auto_delete(self):
        receipt = self.base(branches=[
            {"name": "main", "commit": {"sha": "m1"}},
            {"name": "a", "commit": {"sha": "same"}},
            {"name": "b", "commit": {"sha": "same"}},
        ])
        self.assertTrue(any("same_commit_as:b" in x for x in receipt["dispositions"][0]["evidence"]))
        self.assertFalse(receipt["dispositions"][0]["destructive_action_authorized"])


if __name__ == "__main__":
    unittest.main()
