#!/usr/bin/env python3
"""Run exactly one OpenRouter :free independent review for the active matrix target.

The matrix admission threshold remains unchanged (>=3 families). This runner is
quota-bounded execution infrastructure: it deliberately emits an insufficient
bundle when one hourly OpenRouter review is all that is available, allowing
Gemini and the separate ChatGPT blind/cross-exam lanes to add independent
same-target evidence without exhausting OpenRouter's free daily allowance.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.matrix_design_review import (
    BUNDLE,
    OUT_DIR,
    SELECTION,
    build_bundle,
    call_openrouter,
    extract_target,
    independent_prompt,
    load_matrix,
    validate_independent,
)


def main() -> int:
    root = Path('.').resolve()
    matrix, target = load_matrix(root)
    source, trace = extract_target(root, target)
    selection = json.loads((root / SELECTION).read_text(encoding='utf-8'))
    selected = list(selection.get('selected') or [])
    if not selected:
        raise SystemExit('free-model selection is empty')

    model = selected[0]
    model_id = str(model.get('model', ''))
    family = str(model.get('family', ''))
    if not model_id.endswith(':free'):
        raise SystemExit(f'non-free OpenRouter route refused: {model_id}')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    attempts = []
    independent = []
    raw, attempt = call_openrouter(
        model=model,
        prompt=independent_prompt(target=target, source=source, trace=trace, model=model),
    )
    attempt.update({'phase': 'INDEPENDENT', 'family': family, 'quota_policy': 'ONE_OPENROUTER_CALL_PER_HOUR'})
    attempts.append(attempt)
    if raw is not None:
        try:
            finding = validate_independent(raw, target_id=target['target_id'], family=family, model_id=model_id)
        except Exception as exc:
            attempts.append({
                'phase': 'INDEPENDENT_PARSE', 'family': family, 'model': model_id,
                'status': 'INVALID_OUTPUT', 'cost': 0, 'detail': str(exc),
            })
        else:
            independent.append(finding)
            (OUT_DIR / f'{family}-independent.json').write_text(
                json.dumps(finding, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
            )

    bundle = build_bundle(
        matrix=matrix,
        target=target,
        trace=trace,
        independent=independent,
        finals=[],
        attempts=attempts,
    )
    bundle['execution_policy'] = {
        'openrouter_max_calls_this_run': 1,
        'reason': 'Preserve zero-cost daily quota; additional independent evidence comes from direct Gemini and ChatGPT lanes.',
        'matrix_admission_threshold_unchanged': True,
    }
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    BUNDLE.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({
        'target_id': target['target_id'],
        'openrouter_family': family,
        'independent_families': bundle['independent_reviewer_family_count'],
        'status': bundle['status'],
        'semantic_delta_admitted': False,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
