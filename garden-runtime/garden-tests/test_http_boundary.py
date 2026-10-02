import importlib.util
from pathlib import Path
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("http_boundary", root / "garden-console/http_boundary.py")
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)


class HTTPBoundaryTests(unittest.TestCase):
    def test_ambiguous_identity_and_nonfinite_rejected(self):
        for body in (b'{"actor_id":"human","actor_id":"agent"}',
                     b'{"amount":NaN}', b'{"amount":1e309}', b'[]'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                boundary.strict_object(body)

    def test_large_or_deep_request_bounded(self):
        for body in (b'{"x":"' + b'x' * 33000 + b'"}',
                     b'{"x":' + b'[' * 20 + b'0' + b']' * 20 + b'}'):
            with self.assertRaises(ValueError):
                boundary.strict_object(body)

    def test_admin_injection_is_not_a_run_field(self):
        with self.assertRaises(ValueError):
            boundary.validate_fields({"task": "do work", "control_token": "stolen"}, {"task"})

    def test_cross_origin_rejected(self):
        boundary.check_origin("https://garden.test", "garden.test")
        with self.assertRaises(ValueError):
            boundary.check_origin("https://evil.test", "garden.test")


if __name__ == "__main__":
    unittest.main()
