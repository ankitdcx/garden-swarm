from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.free_model_rotation import choose
from tools.review_quorum import load_target


ROOT = Path(__file__).resolve().parents[1]


def test_review_quorum_cli_loads_without_provider_call():
    proc = subprocess.run(
        [sys.executable, "-m", "tools.review_quorum", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--lane" in proc.stdout
    assert "--output" in proc.stdout


def test_repo_bootstrap_target_is_exact_and_locally_resolvable():
    target, evidence, trace = load_target(ROOT, "repo", 0)
    assert target["target_id"] == "REVIEW-QUORUM-INFRASTRUCTURE"
    assert target["target_hash"]
    assert evidence
    assert trace
    assert all(row["coverage"] != "MISSING" for row in trace), trace


def test_design_matrix_is_bound_to_v15_5_source_root_and_resolves_a_target():
    target, evidence, trace = load_target(ROOT, "design", 0)
    assert target["target_id"] == "GSL-KR"
    assert evidence
    assert trace


def test_free_rotation_can_select_three_distinct_families():
    models = [
        {"id": "deepseek/example:free", "context_length": 128000},
        {"id": "qwen/example:free", "context_length": 128000},
        {"id": "meta-llama/example:free", "context_length": 128000},
        {"id": "mistralai/example:free", "context_length": 128000},
    ]
    picked = choose(models, slot=0, count=3)
    assert len(picked) == 3
    assert len({row["family"] for row in picked}) == 3
    assert all(row["model"].endswith(":free") for row in picked)
