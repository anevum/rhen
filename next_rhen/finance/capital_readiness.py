"""Private, pure 2027 finance envelope for RHEN research, never trading authority.

The owner-supplied balances here are declarations, not bank verification.
Caller must not send household/business numeric details into public RHEN
surfaces, LLM prompts, market-data logs, or brokerage code paths.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
import re
from typing import Any

SCHEMA = "anevum.rhen.capital-readiness-declaration.v1"
OUTPUT = "anevum.rhen.capital-readiness-research.v1"
_WORKSPACE = re.compile(r"^wrk_[A-Za-z0-9_-]{8,64}$")
_AMOUNT = Decimal("0.01")
_MAX = Decimal("1000000000000")
_REQUIRED = frozenset({
    "schema_version", "workspace_id", "reviewed_at", "source_domain", "currency",
    "liquid_balance_usd", "next_90d_obligations_usd", "reserve_floor_usd",
    "tax_holdback_usd", "debt_commitments_usd", "restricted_cash_usd",
})


class ReadinessContractError(ValueError):
    """A money declaration is incomplete or crosses privacy/authority boundaries."""


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReadinessContractError(f"{field} must be canonical UTC")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReadinessContractError(f"{field} invalid timestamp") from exc
    if dt.utcoffset() != timedelta(0) or dt.isoformat().replace("+00:00", "Z") != value:
        raise ReadinessContractError(f"{field} noncanonical UTC")
    return dt


def _usd(value: Any, field: str) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,2})?", value):
        raise ReadinessContractError(f"{field} must be a nonnegative USD decimal string")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise ReadinessContractError(f"{field} invalid") from exc
    if not d.is_finite() or d > _MAX:
        raise ReadinessContractError(f"{field} excessive")
    return d


def _print(d: Decimal) -> str:
    return str(d.quantize(_AMOUNT, rounding=ROUND_HALF_UP))


def project_capital_readiness(intake: dict[str, Any], *, evaluated_at: str) -> dict[str, Any]:
    """Project the surplus of ONE named funding domain for owner review.

    The input liquid balance includes restricted cash. Reserve floor is additional
    to next-90-day obligations, earmarked taxes and debt commitments.
    Financial 'surplus' is NOT bank-verified or authorization to transfer/trade.
    """
    if not isinstance(intake, dict) or set(intake) != _REQUIRED:
        raise ReadinessContractError("exact declaration fields required; reject secret fields")
    if intake["schema_version"] != SCHEMA or not isinstance(intake["workspace_id"], str) or not _WORKSPACE.fullmatch(intake["workspace_id"]):
        raise ReadinessContractError("invalid version or private workspace")
    if intake["source_domain"] not in {"HOUSEHOLD", "ANEVUM_BUSINESS"}:
        raise ReadinessContractError("one isolated funding domain required")
    if intake["currency"] != "USD":
        raise ReadinessContractError("USD only")
    reviewed = _utc(intake["reviewed_at"], "reviewed_at")
    evaluated = _utc(evaluated_at, "evaluated_at")
    if reviewed > evaluated:
        raise ReadinessContractError("future financial review invalid")
    values = {key: _usd(intake[key], key) for key in _REQUIRED if key.endswith("_usd")}
    commitments = sum((values[k] for k in (
        "next_90d_obligations_usd", "reserve_floor_usd", "tax_holdback_usd",
        "debt_commitments_usd", "restricted_cash_usd",
    )), Decimal(0))
    difference = values["liquid_balance_usd"] - commitments
    surplus = max(Decimal(0), difference)
    deficit = max(Decimal(0), -difference)
    stale = evaluated - reviewed > timedelta(days=30)
    out = {
        "schema_version": OUTPUT, "workspace_id": intake["workspace_id"],
        "source_domain": intake["source_domain"], "reviewed_at": intake["reviewed_at"],
        "evaluated_at": evaluated_at,
        "source_state": "OWNER_DECLARED_NOT_BANK_VERIFIED",
        "readiness": "STALE_REVIEW" if stale else (
            "DECLARED_SURPLUS_REVIEW_ONLY" if surplus > 0 else "NO_DECLARED_SURPLUS"),
        "declared_commitments_usd": _print(commitments),
        "declared_surplus_for_review_usd": _print(surplus),
        "declared_shortfall_usd": _print(deficit),
        "next_step": "REFRESH_AND_VERIFY" if stale else "INDEPENDENT_FINANCE_REVIEW",
        "broker_cash_counted_as_household_cash": False,
        "cross_domain_cash_pooling": False,
        "bank_or_broker_verified": False,
        "authorized_investment_amount_usd": None,
        "broker_order_authority": False,
        "transfer_authority": False,
    }
    out["content_sha256"] = sha256(json.dumps(out, sort_keys=True, separators=(",", ":"),
                                            allow_nan=False).encode("utf-8")).hexdigest()
    return out
