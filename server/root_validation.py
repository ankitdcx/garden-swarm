from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_RELEASE_RE = re.compile(r"^Garden-v(?P<version>\d+(?:\.\d+)+)-(?P<date>\d{4}-\d{2}-\d{2})$")


def validate_garden_root(root: Path) -> tuple[Path, dict[str, Any]]:
    """Validate that *root* is a self-consistent Garden public release snapshot."""
    resolved = root.resolve()
    manifest = resolved / "SOURCE_MANIFEST.json"
    version_file = resolved / "VERSION"
    if not manifest.is_file() or not version_file.is_file():
        raise RuntimeError("GARDEN_REPO_ROOT must contain SOURCE_MANIFEST.json and VERSION")

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("GARDEN_REPO_ROOT has an unreadable source manifest") from exc

    release = data.get("release")
    gsl = data.get("gsl")
    canonical_files = data.get("canonical_files")
    if not isinstance(release, str) or not isinstance(gsl, str) or not isinstance(canonical_files, list):
        raise RuntimeError("GARDEN_REPO_ROOT source manifest is not a recognized Garden release manifest")

    match = _RELEASE_RE.fullmatch(release)
    if match is None:
        raise RuntimeError("GARDEN_REPO_ROOT source manifest release identifier is not recognized")

    try:
        version_lines = {
            line.strip()
            for line in version_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except OSError as exc:
        raise RuntimeError("GARDEN_REPO_ROOT has an unreadable VERSION file") from exc

    required_lines = {
        f"Garden v{match.group('version')}",
        f"GSL {gsl}",
        f"Release date: {match.group('date')}",
    }
    if not required_lines.issubset(version_lines):
        raise RuntimeError("GARDEN_REPO_ROOT VERSION does not match SOURCE_MANIFEST.json")

    return resolved, data
