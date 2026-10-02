import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('reference_closure', Path(__file__).resolve().parents[1] / 'scripts/build_reference_closure.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReferenceClosureTests(unittest.TestCase):
    def test_nested_document_link_resolves_to_tracked_target(self):
        target = 'garden-runtime/gardenbench/run.py'
        result = module.resolve_reference('../gardenbench/run.py', source='garden-runtime/docs/comparison.md',
                                          tracked={target}, basenames={}, generated={})
        self.assertEqual(result[:2], (target, 'TRACKED_SOURCE_RELATIVE'))

    def test_escape_missing_target_and_missing_generated_owner_remain_failures(self):
        for reference in ('../../../../outside.py', '../missing.py'):
            result = module.resolve_reference(reference, source='garden-runtime/docs/comparison.md',
                                              tracked={'outside.py'}, basenames={}, generated={})
            self.assertEqual(result[1], 'UNRESOLVED')
        result = module.resolve_reference('future.json', source='document.md', tracked=set(), basenames={},
                                          generated={'future.json': {'owner': 'missing.py'}})
        self.assertEqual(result[1], 'GENERATED_OWNER_MISSING')


if __name__ == '__main__': unittest.main()
