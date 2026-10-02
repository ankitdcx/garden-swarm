"""Console fallback cannot admit native inference through ambient configuration."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "garden-console"))
SPEC = importlib.util.spec_from_file_location("rule_fallback_controller", ROOT / "garden-console/server.py")
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)

REQUEST = {"task": "Multiply 17 by 23", "tool": "calculator", "args": {"op": "multiply", "a": 17, "b": 23}}
NATIVE_ENV = {
    "GARDEN_MODEL_NAME": "SmolLM2-marker-fixture",
    "GARDEN_MODEL_URL": "http://127.0.0.1:11434",
    "GARDEN_LLAMA_BINARY": "/not-selected/native-model",
    "GARDEN_MODEL_PATH": "/not-selected/model.gguf",
}


class ConsoleRuleFallbackTests(unittest.TestCase):
    def test_real_shim_ignores_operable_native_binary_and_model(self):
        with tempfile.TemporaryDirectory(prefix="garden-rule-fallback-") as directory:
            path = Path(directory)
            marker = path / "native-launched.txt"
            binary = path / "harmless-inference"
            binary.write_text("#!" + sys.executable + "\nfrom pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('launched')\nprint('Native model fixture answered.')\n")
            binary.chmod(0o755)
            model = path / "model.gguf"
            model.write_bytes(b"harmless test model fixture")
            # Positive control: the selected executable is genuinely operable.
            subprocess.run([str(binary)], check=True, capture_output=True, timeout=5)
            self.assertEqual(marker.read_text(), "launched")
            marker.unlink()
            # Exercise the old non-root native branch even on hosts where UID
            # changes are blocked. This test-only startup customization grants
            # no tool authority and does not enter the production launch lane.
            (path / "sitecustomize.py").write_text("import os\nos.geteuid = lambda: 1000\n")
            env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(path),
                   **NATIVE_ENV, "GARDEN_LLAMA_BINARY": str(binary), "GARDEN_MODEL_PATH": str(model)}
            result = subprocess.run([sys.executable, str(ROOT / "garden-agents/worker.py")],
                                    input=json.dumps(REQUEST), text=True, capture_output=True,
                                    check=True, timeout=10, env=env)
            bundle = json.loads(result.stdout)
            self.assertFalse(marker.exists(), "controller-facing shim launched native inference")
            self.assertEqual(bundle["cognition"], "RULE_BASED")
            self.assertEqual(bundle["cognition_status"], "IMPLEMENTATION")
            self.assertTrue(all(report["cognition"] == "RULE_BASED" for report in bundle["advisory_reports"]))
            self.assertFalse(bundle["execution_authority"])

    def test_console_child_environment_excludes_native_settings_and_credentials(self):
        ambient = {**NATIVE_ENV, "PATH": "/ambient/bin", "GARDEN_CONTROL_TOKEN": "test-control-secret",
                   "GARDEN_RECEIPT_KEY": "test-receipt-secret", "PYTHONPATH": "/ambient/customization", "LD_PRELOAD": "/ambient/library"}
        calls = []

        def child(command, payload, **options):
            calls.append((command, json.loads(payload), options))
            return 0, json.dumps({"cognition": "RULE_BASED", "roles": []}), ""

        with mock.patch.dict(os.environ, ambient, clear=True), mock.patch.object(controller, "bounded_run", side_effect=child):
            result = controller.agent_work(REQUEST["task"], REQUEST["tool"], REQUEST["args"])
        self.assertEqual(result["cognition"], "RULE_BASED")
        self.assertEqual(len(calls), 1)
        command, request, options = calls[0]
        self.assertEqual(command, [sys.executable, str(ROOT / "garden-agents/worker.py")])
        self.assertEqual(request, REQUEST)
        self.assertEqual(options["env"], {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertNotIn("test-control-secret", json.dumps({"command": command, "request": request, "env": options["env"]}))
        self.assertNotIn("test-receipt-secret", json.dumps({"command": command, "request": request, "env": options["env"]}))

    def test_unavailable_wasm_stays_rule_only_with_native_settings_present(self):
        ambient = {**NATIVE_ENV, "GARDEN_NODE_BINARY": "/unavailable/node", "GARDEN_WASM_DEPENDENCIES": "/unavailable/deps",
                   "GARDEN_WASM_MODEL_DIR": "/unavailable/models"}
        with mock.patch.dict(os.environ, ambient, clear=True), mock.patch.object(controller, "bounded_run", return_value=(0, '{"cognition":"RULE_BASED"}', "")) as child:
            result = controller.agent_work(REQUEST["task"], REQUEST["tool"], REQUEST["args"])
        self.assertEqual(result["cognition"], "RULE_BASED")
        self.assertEqual(child.call_count, 1)
        self.assertEqual(child.call_args.args[0][-1], str(ROOT / "garden-agents/worker.py"))
        self.assertEqual(set(child.call_args.kwargs["env"]), {"PATH", "LANG", "PYTHONDONTWRITEBYTECODE"})


if __name__ == "__main__":
    unittest.main()
