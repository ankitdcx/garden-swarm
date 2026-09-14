import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DirectContractRequirementTests(unittest.TestCase):
    def test_required_semantic_callables_have_direct_contracts(self):
        requirements = json.loads(
            (ROOT / "gsl" / "DIRECT_CONTRACT_REQUIREMENTS.json").read_text(encoding="utf-8")
        )
        required = set(requirements["required_owner_qualified_names"])
        direct = set()
        for path in sorted((ROOT / "gsl").glob("FUNCTION_CONTRACTS*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema") != "GardenFunctionContractRegistry/v1":
                continue
            direct.update(
                str(row.get("owner_qualified_name"))
                for row in payload.get("contracts", [])
                if row.get("owner_qualified_name")
            )
        self.assertEqual(required - direct, set(), f"missing direct contracts: {sorted(required - direct)}")

    def test_requirements_are_bound_to_current_design_epoch(self):
        requirements = json.loads(
            (ROOT / "gsl" / "DIRECT_CONTRACT_REQUIREMENTS.json").read_text(encoding="utf-8")
        )
        epoch = json.loads((ROOT / "gsl" / "DESIGN_EPOCH.json").read_text(encoding="utf-8"))
        self.assertEqual(requirements["design_epoch_ref"], epoch["design_epoch_ref"])


if __name__ == "__main__":
    unittest.main()
