"""Source-bound campaign funding; explicit abandonment never fabricates billing.

Campaign policy is loaded from the checked-out protected main tree, not a model
response or state-branch directive. A directive can select an authorized campaign,
but cannot grant a new exception or increase its limits.
"""
from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

POLICY_PATH = Path('agents/v159-review-campaign.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()


def amount(value):
    if value is None or isinstance(value, bool):
        raise ValueError('unknown campaign amount')
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError('invalid campaign amount') from exc
    if not number.is_finite() or number < 0:
        raise ValueError('invalid campaign amount')
    return number


def load_campaign(root=Path('.')):
    path = root / POLICY_PATH
    if not path.is_file():
        return None
    policy = json.loads(path.read_text(encoding='utf-8'))
    if (policy.get('schema') != 'GardenReviewCampaign/v1' or
            policy.get('campaign_id') != 'GARDEN-V159-20260917' or
            policy.get('status') != 'AUTHORIZED' or policy.get('renewable') is not False):
        raise ValueError('unrecognized or inactive campaign')
    for field, ceiling in [('total_ceiling_usd', '10'), ('daily_ceiling_usd', '10'),
                           ('per_call_ceiling_usd', '.10')]:
        if not Decimal('0') < amount(policy.get(field)) <= Decimal(ceiling):
            raise ValueError('campaign ceiling exceeds authorization')
    return policy


def abandonment_charge(attempt, campaign):
    """Return a financial allowance, never a claimed actual provider charge."""
    if not campaign or attempt.get('status') != 'UNKNOWN':
        return None
    matches = [r for r in campaign.get('abandoned_attempts', [])
               if r.get('attempt_sha256') == digest(attempt)]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError('ambiguous abandonment authorization')
    rule = matches[0]
    admin = attempt.get('administrative_disposition') or {}
    if (str(attempt.get('run_id')) != rule.get('run_id') or
            attempt.get('model') != rule.get('model') or
            attempt.get('cost') is not None or
            admin.get('status') != 'CLOSED_ABANDONED_BY_USER' or
            rule.get('billing_status') != 'UNKNOWN' or
            rule.get('retry_allowed') is not False or
            rule.get('review_evidence_admissible') is not False):
        raise ValueError('abandonment authorization mismatch')
    reserved = amount(attempt.get('reserved'))
    allowance = amount(rule.get('accounting_allowance_usd'))
    if not Decimal('0') < reserved <= allowance:
        raise ValueError('abandonment allowance does not preserve reservation')
    return allowance


def rate_limit_recovery(attempt, campaign):
    """Financial-risk allowance for a received 429, never proof of zero billing.

    Only this source-bound campaign may opt in. A retry still needs an exact
    attempt-bound directive and the existing per-slot call limit in the worker.
    """
    rule = (campaign or {}).get('http_429_recovery') or {}
    if rule.get('enabled') is not True:
        return None
    spending = attempt.get('spending') or {}
    if (attempt.get('status') != 'UNKNOWN' or attempt.get('http_status') != 429 or
            attempt.get('error_type') != 'HTTPError' or attempt.get('response_id') or
            attempt.get('cost') is not None or attempt.get('inference_reserved') is not True or
            attempt.get('semantic_delta_admitted') is not False or
            attempt.get('full_review_complete') is not False or
            spending.get('campaign_id') != campaign.get('campaign_id') or
            spending.get('source_sha256') != campaign.get('source_sha256')):
        return None
    if (rule.get('max_attempts_per_slot') != 2 or
            rule.get('billing_status') != 'UNKNOWN' or
            rule.get('review_evidence_admissible') is not False):
        raise ValueError('invalid rate-limit recovery policy')
    reserve = amount(attempt.get('reserved'))
    if not Decimal('0') < reserve <= amount(campaign['per_call_ceiling_usd']):
        raise ValueError('rate-limit reservation is not covered')
    observation = attempt.get('http_rate_limit')
    if observation is None:
        # Earlier workers discarded Retry-After. Only an exact protected-policy
        # receipt may provide the conservative, externally observed completion.
        matches = [r for r in rule.get('legacy_receipts', [])
                   if r.get('attempt_sha256') == digest(attempt)]
        if len(matches) != 1:
            return None
        observation = matches[0]
        if (observation.get('header_evidence') != 'NOT_CAPTURED_BY_OLD_WORKER' or
                not isinstance(observation.get('reason'), str) or not observation['reason'].strip()):
            raise ValueError('legacy rate-limit recovery requires honest header evidence')
        approved_not_before = amount(observation.get('approved_not_before'))
        observed = amount(observation.get('observed_at'))
        if observed < amount(attempt.get('started')):
            raise ValueError('rate-limit observation precedes call')
        delay = max(Decimal('60'), amount(rule.get('minimum_backoff_seconds')))
        return {'accounting_allowance_usd': reserve,
                'retry_not_before': max(observed + delay, approved_not_before),
                'review_evidence_admissible': False, 'billing_status': 'UNKNOWN'}
    if observation.get('retry_after_valid') is not True:
        return None
    observed = amount(observation.get('observed_at'))
    if observed < amount(attempt.get('started')):
        raise ValueError('rate-limit observation precedes call')
    delay = max(Decimal('60'), amount(rule.get('minimum_backoff_seconds')),
                amount(observation.get('retry_after_seconds')))
    return {'accounting_allowance_usd': reserve, 'retry_not_before': observed + delay,
            'review_evidence_admissible': False, 'billing_status': 'UNKNOWN'}


def unknown_allowance(attempt, campaign):
    abandoned = abandonment_charge(attempt, campaign)
    if abandoned is not None:
        return abandoned
    recovery = rate_limit_recovery(attempt, campaign)
    return recovery['accounting_allowance_usd'] if recovery else None


def blocking_attempts(state, campaign=None):
    return [a for a in state.get('attempts', [])
            if a.get('status') in ('UNKNOWN', 'RESERVED') and
            unknown_allowance(a, campaign) is None]


def accounting_charge(attempt, campaign=None):
    allowance = unknown_allowance(attempt, campaign)
    return allowance if allowance is not None else amount(attempt.get('cost'))


def bind_campaign(directive, source_sha256, root=Path('.')):
    if not directive.get('campaign_id'):
        return None
    campaign = load_campaign(root)
    approved_sources = {campaign['source_sha256']} if campaign else set()
    if campaign:
        approved_sources.update(row['sha256'] for row in campaign.get('source_slices', [])
                                if row.get('master_sha256') == campaign['source_sha256'])
    if (not campaign or directive['campaign_id'] != campaign['campaign_id'] or
            source_sha256 not in approved_sources):
        raise ValueError('campaign is not authorized for this exact source')
    return campaign


def spending_policy(policy, campaign):
    result = copy.deepcopy(policy)
    result['daily_openrouter_cost_ceiling_usd'] = str(amount(campaign['daily_ceiling_usd']))
    result['routine_model_call_cost_ceiling_usd'] = str(min(
        amount(policy['routine_model_call_cost_ceiling_usd']), amount(campaign['per_call_ceiling_usd'])))
    # This explicit total campaign authorization supersedes the old $9 routine
    # allocation only for this exact source. No other pool is borrowed or reset.
    result['budget_pools_usd']['routine'] = str(amount(campaign['total_ceiling_usd']))
    return result


def check_total(state, campaign, reserve):
    # Count ALL retained ledger attempts, including earlier known costs and the
    # abandoned allowance. Changing day/target/cycle cannot reset the ceiling.
    spent = sum((accounting_charge(a, campaign) for a in state.get('attempts', [])), Decimal(0))
    if spent + amount(reserve) > amount(campaign['total_ceiling_usd']):
        raise ValueError('campaign total reservation exhausted')
    return {'campaign_id': campaign['campaign_id'], 'campaign_policy_sha256': digest(campaign),
            'source_sha256': campaign['source_sha256'],
            'total_ceiling_usd': str(amount(campaign['total_ceiling_usd'])),
            'accounted_before_usd': str(spent),
            'abandoned_allowance_is_actual_billing': False}
