import json
import os
from unittest.mock import patch

from swarm.orchestrator import Role, WorkItem, call_openrouter


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps({
            "model": "example/free-model",
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"cost": 0},
        }).encode("utf-8")


def _role():
    return Role(
        id="zdr-test",
        name="ZDR test",
        model="example/free-model",
        objective="test",
        lenses=[],
    )


def _item():
    return WorkItem(
        id="test:chunk-001",
        source_file="Garden_User_v15.5_FULL_2026-09-12.txt",
        source_sha256="0" * 64,
        chunk_index=1,
        chunk_count=1,
        text="test",
    )


def test_non_public_free_route_requests_zdr():
    captured = {}

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response()

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        with patch("swarm.orchestrator.request.urlopen", side_effect=fake_urlopen):
            result = call_openrouter(_role(), _item(), 100, public_free=False)

    assert result.status == "OK"
    assert captured["payload"]["provider"]["zdr"] is True


def test_public_free_exception_does_not_claim_zdr():
    captured = {}

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _Response()

    with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=False):
        with patch("swarm.orchestrator.request.urlopen", side_effect=fake_urlopen):
            result = call_openrouter(_role(), _item(), 100, public_free=True)

    assert result.status == "OK"
    assert "provider" not in captured["payload"]
