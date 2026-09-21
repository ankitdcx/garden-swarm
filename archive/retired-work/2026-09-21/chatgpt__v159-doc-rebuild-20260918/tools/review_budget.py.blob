"""Select an already-authorized spending mode without changing lifetime pools."""
import copy
from datetime import datetime, timezone
from decimal import Decimal


def effective_policy(policy, directive, now):
    result = copy.deepcopy(policy)
    mode = directive.get('spending_mode', 'DEFAULT')
    if mode not in ('DEFAULT', 'AUDIT'):
        raise ValueError('unknown review spending mode')
    if Decimal(str(policy['routine_model_call_cost_ceiling_usd'])) != Decimal('0.1'):
        raise ValueError('review call ceiling must be $0.10')
    daily = Decimal(str(policy['spending_modes'][mode]['daily_ceiling_usd']))
    expected = Decimal('10')
    if daily != expected:
        raise ValueError('spending mode ceiling mismatch')
    day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    if mode == 'AUDIT':
        grant = directive.get('audit_window') or {}
        if (grant.get('utc_day') != day or grant.get('target_id') != directive.get('target_id') or
                not isinstance(grant.get('audit_id'), str) or not grant['audit_id'].strip() or
                not isinstance(grant.get('purpose'), str) or not grant['purpose'].strip()):
            raise ValueError('AUDIT requires a current UTC-day, target-bound audit plan')
    result['daily_openrouter_cost_ceiling_usd'] = float(daily)
    return result, {'mode': mode, 'utc_day': day, 'per_call_usd': '0.10',
                    'daily_ceiling_usd': str(daily), 'pool': 'routine',
                    'pool_lifetime_allocation_usd': str(policy['budget_pools_usd']['routine']),
                    'audit_id': (directive.get('audit_window') or {}).get('audit_id')}
