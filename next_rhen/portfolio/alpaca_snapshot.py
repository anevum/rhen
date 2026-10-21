"""Pure, fail-closed RHEN V5 Alpaca account/position read projections.

Does not import credentials, the legacy write-capable client, network libraries,
orders, or transfers. The injected GET port is for independently reviewed
read-only infrastructure only. No external account was accessed by this module.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
import re
from typing import Any

SCHEMA = "anevum.rhen.alpaca-read-snapshot.v1"
_WORKSPACE = re.compile(r"^wrk_[A-Za-z0-9_-]{8,64}$")
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9./-]{0,30}$")
_ACCOUNT_ID = re.compile(r"^[A-Za-z0-9_-]{8,128}$")
_MAX_MONEY = Decimal("1000000000000")
_MAX_POSITIONS = 500
_AMOUNT = Decimal("0.01")
_GET_PATHS = ("/v2/account", "/v2/positions")
_SENSITIVE_KEYS = frozenset({"api_key", "api_secret", "apca-api-key-id", "apca-api-secret-key",
                             "authorization", "access_token", "refresh_token", "password"})


class AlpacaSnapshotError(ValueError):
    """Untrusted or incomplete broker read cannot be projected."""


def _utc(value: Any, key: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AlpacaSnapshotError(f"{key} must be canonical UTC Z")
    try:
        at = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise AlpacaSnapshotError(f"{key} is not an ISO timestamp") from exc
    if at.tzinfo is None or at.utcoffset() != timedelta(0) or at.isoformat().replace("+00:00", "Z") != value:
        raise AlpacaSnapshotError(f"{key} must be canonical UTC")
    return at


def _money(value: Any, key: str, *, allow_negative: bool = True) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise AlpacaSnapshotError(f"{key} must be a number or numeric string")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise AlpacaSnapshotError(f"{key} is invalid") from exc
    if not amount.is_finite() or abs(amount) > _MAX_MONEY or (not allow_negative and amount < 0):
        raise AlpacaSnapshotError(f"{key} is nonfinite, negative, or excessive")
    return amount


def _str_money(amount: Decimal) -> str:
    return str(amount.quantize(_AMOUNT, rounding=ROUND_HALF_UP))


def _no_credentials(record: dict[str, Any], name: str) -> None:
    if any(key.lower() in _SENSITIVE_KEYS for key in record):
        raise AlpacaSnapshotError(f"{name} contains credential-shaped data")


def _digest(payload: dict[str, Any]) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def normalize_alpaca_snapshot(
    account: dict[str, Any], positions: list[dict[str, Any]], *,
    workspace_id: str, expected_account_id: str, environment: str,
    observed_at: str, evaluated_at: str,
) -> dict[str, Any]:
    """Interpret supplied GET /v2/account and GET /v2/positions payloads.

    These independently timed API reads are NOT an atomic brokerage audit.
    The expected account ID is provided by a private owner-controlled binding,
    and is never copied into the output, logs, or public source.
    """
    if not isinstance(workspace_id, str) or not _WORKSPACE.fullmatch(workspace_id):
        raise AlpacaSnapshotError("invalid private RHEN workspace scope")
    if not isinstance(expected_account_id, str) or not _ACCOUNT_ID.fullmatch(expected_account_id):
        raise AlpacaSnapshotError("invalid private account binding")
    if environment not in {"PAPER", "LIVE"}:
        raise AlpacaSnapshotError("environment must be explicitly PAPER or LIVE")
    observed, evaluated = _utc(observed_at, "observed_at"), _utc(evaluated_at, "evaluated_at")
    if observed > evaluated:
        raise AlpacaSnapshotError("broker read may not be from the future")
    if not isinstance(account, dict) or not isinstance(positions, list):
        raise AlpacaSnapshotError("broker account and positions must be complete JSON containers")
    if len(positions) > _MAX_POSITIONS:
        raise AlpacaSnapshotError("bounded positions response exceeded")
    _no_credentials(account, "account")
    if account.get("id") != expected_account_id:
        raise AlpacaSnapshotError("account binding mismatch: cross-workspace data blocked")
    currency = account.get("currency")
    if currency != "USD":
        raise AlpacaSnapshotError("only explicitly USD-denominated accounts supported")
    equity = _money(account.get("equity"), "account.equity", allow_negative=False)
    cash = _money(account.get("cash"), "account.cash")
    buying_power = _money(account.get("buying_power"), "account.buying_power", allow_negative=False)
    status = account.get("status")
    if not isinstance(status, str) or not status or len(status) > 48:
        raise AlpacaSnapshotError("account status missing or invalid")
    flags = {}
    for k in ("trading_blocked", "account_blocked"):
        v = account.get(k)
        if type(v) is not bool:
            raise AlpacaSnapshotError(f"account.{k} must be explicit bool")
        flags[k] = v
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    long_value, short_value, other_value = Decimal(0), Decimal(0), Decimal(0)
    for i, row in enumerate(positions):
        if not isinstance(row, dict):
            raise AlpacaSnapshotError(f"position[{i}] must be a record")
        _no_credentials(row, "position")
        symbol = row.get("symbol")
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol) or symbol in seen:
            raise AlpacaSnapshotError("duplicate or invalid position symbol")
        seen.add(symbol)
        side = row.get("side")
        if side not in {"long", "short"}:
            raise AlpacaSnapshotError("position side missing or unexpected")
        asset_class = row.get("asset_class")
        if not isinstance(asset_class, str) or not asset_class or len(asset_class) > 64:
            raise AlpacaSnapshotError("position asset class invalid")
        qty = _money(row.get("qty"), "position.qty")
        mv = _money(row.get("market_value"), "position.market_value")
        if qty == 0 or mv == 0:
            raise AlpacaSnapshotError("open position has missing quantity or market value")
        if side == "long" and qty < 0 or side == "short" and qty > 0:
            raise AlpacaSnapshotError("position side/quantity inconsistent")
        signed_mv = abs(mv) if side == "long" else -abs(mv)
        if side == "long":
            long_value += signed_mv
        else:
            short_value += -signed_mv
        if asset_class != "us_equity":
            other_value += abs(signed_mv)
        results.append({
            "symbol": symbol, "asset_class": asset_class, "side": side,
            "quantity": str(qty), "signed_market_value_usd": _str_money(signed_mv),
            "theme_exposure": "UNKNOWN_NO_VERIFIED_CLASSIFICATION",
        })
    stale = evaluated - observed > timedelta(minutes=15)
    snapshot = {
        "schema_version": SCHEMA, "workspace_id": workspace_id,
        "provider": "ALPACA", "environment": environment,
        "observed_at": observed_at, "evaluated_at": evaluated_at,
        "source_state": "PROVIDER_PAYLOAD_NOT_INDEPENDENTLY_ATTESTED",
        "read_consistency": "NONATOMIC_SEPARATE_ACCOUNT_AND_POSITIONS_READS",
        "freshness": "STALE" if stale else "RECENT_UNATTESTED",
        "account_status": status,
        "account_trading_blocked": flags["trading_blocked"],
        "account_blocked": flags["account_blocked"],
        "currency": "USD", "equity_usd": _str_money(equity),
        "cash_usd": _str_money(cash), "buying_power_usd": _str_money(buying_power),
        "long_market_value_usd": _str_money(long_value),
        "short_market_value_usd": _str_money(short_value),
        "non_equity_gross_usd": _str_money(other_value),
        "holdings_count": len(results), "positions": sorted(results, key=lambda r: r["symbol"]),
        "account_equity_reconciled": False,
        "investment_amount_approved_usd": None,
        "broker_order_authority": False, "transfer_authority": False,
    }
    snapshot["content_sha256"] = _digest(snapshot)
    return snapshot


async def read_alpaca_snapshot(
    get_port: Any, *, workspace_id: str, expected_account_id: str,
    environment: str, observed_at: str, evaluated_at: str,
) -> dict[str, Any]:
    """Fetch only two GET projections via an injected, separately approved port.

    This code has NO network transport, credentials or trading methods. Its
    caller must bind a least-privilege read-only OAuth authorization and check
    the owner/workspace binding independently at the API service boundary.
    """
    if not hasattr(get_port, "get_json") or not callable(get_port.get_json):
        raise AlpacaSnapshotError("reviewed read-only GET port not provided")
    if environment not in {"PAPER", "LIVE"}:
        raise AlpacaSnapshotError("account environment unspecified")
    account = await get_port.get_json(_GET_PATHS[0])
    if not isinstance(account, dict) or account.get("id") != expected_account_id:
        raise AlpacaSnapshotError("account binding mismatch")
    positions = await get_port.get_json(_GET_PATHS[1])
    return normalize_alpaca_snapshot(
        account, positions, workspace_id=workspace_id,
        expected_account_id=expected_account_id, environment=environment,
        observed_at=observed_at, evaluated_at=evaluated_at,
    )
