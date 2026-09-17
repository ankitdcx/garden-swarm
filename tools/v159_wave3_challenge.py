#!/usr/bin/env python3
from pathlib import Path
import tools.v159_wave2_challenge as base

base.OUT = Path('review-results/v159-wave3-challenge')
_original_prompt = base.prompt

def wave3_prompt(source, candidate, family, ph):
    return _original_prompt(source, candidate, family, ph).replace(
        'SECOND-PASS ADVERSARIAL GARDEN v15.9 REVIEW — WAVE 2.',
        'SECOND-PASS ADVERSARIAL GARDEN v15.9 REVIEW — WAVE 3.'
    )

base.prompt = wave3_prompt

if __name__ == '__main__':
    base.main()
