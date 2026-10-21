"""Join unverified Alpaca long holdings with analyst-declared technology tags.

Exposure denominator is the gross LONG US-equity book, NOT account equity,
buying power, household wealth or a verified ETF holdings look-through.
No broker orders, market feeds, customer/account identifiers or data writes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
import json
import re
from typing import Any
from urllib.parse import urlsplit

from next_rhen.portfolio.alpaca_snapshot import SCHEMA as SNAPSHOT_SCHEMA
from next_rhen.research.strategic_atlas import THEMES

SCHEMA = "anevum.rhen.alpaca-theme-projection.v1"
_INPUT_KEYS = frozenset({"workspace_id", "classifications"})
_CLASS_KEYS = frozenset({"symbol", "security_kind", "theme_attribution_bps", "source_url", "source_observed_at"})
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9./-]{0,30}$")
_MAX = Decimal("1000000000000")


class ThemeProjectionError(ValueError):
    """Refuse a misleading or cross-workspace portfolio attribution."""


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ThemeProjectionError(f"{field} requires UTC Z")
    try:
        at = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ThemeProjectionError(f"{field} invalid") from exc
    if at.utcoffset() != timedelta(0) or at.isoformat().replace("+00:00", "Z") != value:
        raise ThemeProjectionError(f"{field} requires canonical UTC")
    return at


def _usd(value: Any, field: str) -> Decimal:
    if not isinstance(value, str):
        raise ThemeProjectionError(f"{field} must be a USD decimal string")
    try:
        amt = Decimal(value)
    except InvalidOperation as exc:
        raise ThemeProjectionError(f"{field} invalid amount") from exc
    if not amt.is_finite() or not -_MAX <= amt <= _MAX:
        raise ThemeProjectionError(f"{field} out of bounds")
    return amt


def _number(x: Decimal) -> str:
    return str(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def project_long_book_themes(snapshot: dict[str, Any], intake: dict[str, Any], *, evaluated_at: str) -> dict[str, Any]:
    """Research-only breakdown; a supplied URL is never source verification."""
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != SNAPSHOT_SCHEMA:
        raise ThemeProjectionError("canonical read-only Alpaca snapshot required")
    proof = snapshot.get("content_sha256")
    fields = {k: v for k, v in snapshot.items() if k != "content_sha256"}
    if proof != sha256(json.dumps(fields, sort_keys=True, separators=(",", ":"),
                                  allow_nan=False).encode("utf-8")).hexdigest():
        raise ThemeProjectionError("snapshot content changed since digest")
    if (snapshot.get("provider") != "ALPACA" or snapshot.get("currency") != "USD" or
            snapshot.get("broker_order_authority") is not False or
            snapshot.get("transfer_authority") is not False):
        raise ThemeProjectionError("non-read-only broker scope")
    if not isinstance(intake, dict) or set(intake) != _INPUT_KEYS:
        raise ThemeProjectionError("exact analyst classification envelope required")
    if intake["workspace_id"] != snapshot.get("workspace_id"):
        raise ThemeProjectionError("classification workspace differs from brokerage workspace")
    evaluated = _utc(evaluated_at, "evaluated_at")
    observed = _utc(snapshot.get("observed_at"), "snapshot.observed_at")
    if observed > evaluated:
        raise ThemeProjectionError("broker snapshot from future")
    classification = intake["classifications"]
    if not isinstance(classification, list) or len(classification) > 500:
        raise ThemeProjectionError("bounded classification list required")
    entries = {}
    for raw in classification:
        if not isinstance(raw, dict) or set(raw) != _CLASS_KEYS:
            raise ThemeProjectionError("classification has unknown fields")
        symbol = raw["symbol"]
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol) or symbol in entries:
            raise ThemeProjectionError("classification symbol malformed or repeated")
        if raw["security_kind"] not in {"EQUITY", "ETF"}:
            raise ThemeProjectionError("only explicit long equity/ETF classes supported")
        parts = raw["theme_attribution_bps"]
        if (not isinstance(parts, dict) or len(parts) > 16 or
                any(k not in THEMES or type(v) is not int or v < 0 or v > 10000 for k, v in parts.items()) or
                sum(parts.values()) > 10000):
            raise ThemeProjectionError("theme portions must be exclusive and bounded")
        source_url = raw["source_url"]
        if source_url is not None:
            if not isinstance(source_url, str) or len(source_url) > 2048:
                raise ThemeProjectionError("unverified source URL invalid")
            url = urlsplit(source_url)
            if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
                raise ThemeProjectionError("source must be HTTPS without credentials")
        if parts and not source_url:
            raise ThemeProjectionError("positive attribution needs an unverified source reference")
        if raw["source_observed_at"] is not None:
            checked = _utc(raw["source_observed_at"], "source_observed_at")
            if checked > evaluated:
                raise ThemeProjectionError("future analyst observation")
        elif parts:
            raise ThemeProjectionError("positive attribution needs a recorded source observation time")
        entries[symbol] = raw
    observed_symbols: set[str] = set()
    positions = snapshot.get("positions")
    if not isinstance(positions, list) or snapshot.get("holdings_count") != len(positions):
        raise ThemeProjectionError("snapshot holdings count invalid")
    long_book = Decimal(0)
    theme_usd = {k: Decimal(0) for k in sorted(THEMES)}
    unknown = Decimal(0)
    stale_links = 0
    for p in positions:
        if not isinstance(p, dict):
            raise ThemeProjectionError("invalid position record")
        symbol = p.get("symbol")
        if not isinstance(symbol, str) or not _SYMBOL.fullmatch(symbol) or symbol in observed_symbols:
            raise ThemeProjectionError("position symbols invalid")
        observed_symbols.add(symbol)
        side, cls = p.get("side"), p.get("asset_class")
        amount = _usd(p.get("signed_market_value_usd"), "signed_market_value_usd")
        if side != "long" or amount <= 0 or cls != "us_equity":
            # This bridge refuses silently omitting short, crypto or other assets.
            raise ThemeProjectionError("complex or non-US-equity holdings need a distinct model")
        long_book += amount
        tags = entries.get(symbol)
        portions = tags["theme_attribution_bps"] if tags else {}
        allocated = Decimal(0)
        for theme, bps in portions.items():
            part = amount * Decimal(bps) / Decimal(10000)
            theme_usd[theme] += part
            allocated += part
        unknown += amount - allocated
        if tags and portions:
            stale_links += int(evaluated - _utc(tags["source_observed_at"], "source_observed_at") > timedelta(days=90))
    if set(entries) - observed_symbols:
        raise ThemeProjectionError("classification contains absent brokerage symbols")
    if long_book > _MAX:
        raise ThemeProjectionError("long securities amount exceeds bounded analysis")
    coverage = "NO_LONG_HOLDINGS" if not long_book else (
        "PARTIAL_UNVERIFIED_ATTRIBUTION" if unknown else "DECLARED_COMPLETE_UNVERIFIED")
    out = {
        "schema_version": SCHEMA, "workspace_id": snapshot["workspace_id"],
        "snapshot_digest": proof, "evaluated_at": evaluated_at,
        "source_state": "ANALYST_DECLARED_NOT_VERIFIED",
        "read_freshness": snapshot.get("freshness"),
        "coverage_state": coverage,
        "denominator": "GROSS_LONG_US_EQUITY_HOLDINGS_NOT_ACCOUNT_EQUITY",
        "long_us_equity_book_usd": _number(long_book),
        "unattributed_long_us_equity_usd": _number(unknown),
        "theme_exposure_usd": {k: _number(v) for k, v in theme_usd.items() if v},
        "theme_share_of_long_book_bps": ({k: float(round(v / long_book * 10000, 2))
                                         for k, v in theme_usd.items() if v} if long_book else None),
        "stale_analyst_classifications": stale_links,
        "broker_account_verified": False,
        "broker_order_authority": False,
        "transfer_authority": False,
    }
    out["content_sha256"] = sha256(json.dumps(out, sort_keys=True, separators=(",", ":"),
                                            allow_nan=False).encode("utf-8")).hexdigest()
    return out
