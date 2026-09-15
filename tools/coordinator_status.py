"""Evaluate externally published Coordinator status without inventing liveness."""
from datetime import datetime, timezone


def evaluate(receipt: dict, *, now: datetime | None = None) -> str:
    if receipt.get('schema') != 'CoordinatorStatusReceipt/v1':
        return 'UNKNOWN'
    if receipt.get('scheduler_state') == 'PAUSED':
        return 'PAUSED'
    if receipt.get('scheduler_state') != 'RUNNING':
        return 'UNKNOWN'
    try:
        stamp = datetime.fromisoformat(receipt['last_successful_dispatch_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            return 'UNKNOWN'
        age = ((now or datetime.now(timezone.utc)) - stamp).total_seconds()
        limit = receipt['active_heartbeat_max_age_seconds']
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or not 0 < limit <= 86400:
            return 'UNKNOWN'
        if age < 0:
            return 'UNKNOWN'
        return 'OBSERVED_RECENT_DISPATCH' if age <= limit else 'STALE'
    except (KeyError, TypeError, ValueError):
        return 'UNKNOWN'
