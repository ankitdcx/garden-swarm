# Garden v15.10 Independent Standalone — Final Materialization

Date: 2026-09-21
Status: COMPLETE STANDALONE WORKING DESIGN / CANONICAL ADMISSION SEPARATE

This supersedes the earlier archive-style standalone materialization. The final Catalogue no longer contains predecessor SOURCE_BLOB records and does not require old documents to resolve current meaning.

Final package hashes:
- Book: fcad4d0d3c21374c03142885312de31d078638e68ca42659c1446799c247f634 — 26,440 bytes
- Technical: 3f983ffb8b5033a32f2ee9f52b70987267c2eb4355bb866e51b8bfb71c9de754 — 53,139 bytes
- Catalogue: 007a272a854477ab9f26f12cb12d133a200a78a4d3f40a270a45065e57f6d419 — 26,821,634 bytes
- ZIP: cceba91381ef7f6b66a458b8b42a13ec2a71586e5d5d4d27a51e903cc54fb24c

Deterministic closure:
- 26,332 Catalogue records.
- 6,310 v15.9 paragraphs materialized inline as current semantic records.
- 106 exact v15.8 paragraphs absent from v15.9 retained inline as anti-loss residuals requiring disposition, not silently deleted or promoted.
- 1,935 identity indexes; zero without inline resolved occurrences.
- 55 family indexes; zero without internal semantic resolution.
- zero SOURCE_BLOB records.
- zero source_blob_ref fields.
- zero occurrences of INDEX_ONLY_NOT_SEMANTIC_OWNER, REFERENCED_PREDECESSOR_SOURCE, or PREDECESSOR_SOURCE_CONTROLS_UNTIL_VALID_SUPERSESSION.

Historical document/version/line/hash fields may remain as provenance metadata. They are not semantic lookup requirements.

This establishes standalone representation and anti-loss retention. It does not manufacture executable proof, empirical validation, external certification, canonical admission or deployment authority.
