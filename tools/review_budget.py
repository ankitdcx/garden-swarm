"""Apply the single human-authorized paid OpenRouter budget rule.

The active monetary rule is intentionally simple:
- maximum USD 2 total OpenRouter spend per UTC day;
- maximum USD 0.01 per paid call.

Review modes/campaigns may constrain evidence, targets, call counts, privacy or
assurance, but they do not create separate monetary pools or higher/lower spend
authority.
"""
import copy
from datetime import datetime, timezone
from decimal import Decimal


DAILY_CEILING = Decimal("2")
PER_CALL_CEILING = Decimal("0.01")


def effective_policy(policy, directive, now):
    result = copy.deepcopy(policy)
    mode = directive.get("spending_mode", "DEFAULT")
    if mode not in ("DEFAULT", "AUDIT"):
        raise ValueError("unknown review spending mode")

    if Decimal(str(policy["routine_model_call_cost_ceiling_usd"])) != PER_CALL_CEILING:
        raise ValueError("review call ceiling must be $0.01")
    if Decimal(str(policy["daily_openrouter_cost_ceiling_usd"])) != DAILY_CEILING:
        raise ValueError("review daily ceiling must be $2")

    day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
    audit_id = None
    if mode == "AUDIT":
        # AUDIT remains a target/time-scoped review mode, not extra spending authority.
        grant = directive.get("audit_window") or {}
        if (
            grant.get("utc_day") != day
            or grant.get("target_id") != directive.get("target_id")
            or not isinstance(grant.get("audit_id"), str)
            or not grant["audit_id"].strip()
            or not isinstance(grant.get("purpose"), str)
            or not grant["purpose"].strip()
        ):
            raise ValueError("AUDIT requires a current UTC-day, target-bound audit plan")
        audit_id = grant["audit_id"]

    result["daily_openrouter_cost_ceiling_usd"] = float(DAILY_CEILING)
    result["routine_model_call_cost_ceiling_usd"] = float(PER_CALL_CEILING)
    return result, {
        "mode": mode,
        "utc_day": day,
        "per_call_usd": str(PER_CALL_CEILING),
        "daily_ceiling_usd": str(DAILY_CEILING),
        "budget_rule": "OPENROUTER_2_USD_DAY_0_01_CALL",
        "audit_id": audit_id,
    }
