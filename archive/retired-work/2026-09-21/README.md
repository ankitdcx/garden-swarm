# Retired Garden work recovery — 2026-09-21

This directory preserves exact bytes from branches explicitly retired by the user.

Historical source files are stored at paths ending in **.blob**. The Git blob SHA is unchanged from the retired branch, so the archived bytes are exact. The added .blob suffix is only a repository-path wrapper that keeps historical content outside active Garden source/reference interpretation.

Batch manifests record:
- retired branch head SHA;
- comparison base;
- PR number where available;
- exact original blob SHA;
- non-resolving garden:// source/archive identifiers.

These files are archival evidence only. They are not active implementation, current Garden semantics, authority, proof, certification, or canonical source.

Canonical effect: NONE.
Authority effect: NONE.
