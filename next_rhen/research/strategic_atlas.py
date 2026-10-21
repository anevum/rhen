"""Offline, research-only 2027 strategic thesis and exposure projections.

Untrusted supplied sources are NOT independently verified. No broker, network,
account, order, model, database or deployment dependencies are imported here.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Any
from urllib.parse import urlsplit

ATLAS_INPUT = "anevum.rhen.strategic-theses-intake.v1"
ATLAS_OUTPUT = "anevum.rhen.strategic-atlas.v1"
PORTFOLIO_INPUT = "anevum.rhen.declared-exposure-intake.v1"
PORTFOLIO_OUTPUT = "anevum.rhen.declared-exposure.v1"
THEMES = frozenset({
    "SEMICONDUCTOR_DESIGN", "SEMICONDUCTOR_FOUNDRY", "CHIP_EQUIPMENT",
    "ADVANCED_PACKAGING", "MEMORY", "POWER_SEMICONDUCTORS",
    "PHOTONIC_INTERCONNECTS", "NEUROMORPHIC_COMPUTING", "BIOCOMPUTING",
    "GRID_AND_COOLING", "NUCLEAR_FISSION", "NUCLEAR_FUSION",
    "NUCLEAR_MICROPOWER", "NUCLEAR_MICROREACTORS", "GEOTHERMAL",
    "ENERGY_STORAGE",
})
KINDS = frozenset({"PUBLIC_EQUITY", "ETF", "PRIVATE_COMPANY", "RESEARCH_ORGANIZATION"})
_SYM = re.compile(r"^[A-Z][A-Z0-9.]{0,14}$")
_ID = re.compile(r"^[A-Za-z0-9._:-]{1,80}$")
_WRK = re.compile(r"^wrk_[A-Za-z0-9_-]{8,64}$")
_THESIS = frozenset({
    "id", "name", "symbol", "kind", "themes", "hypothesis", "disconfirmation",
    "next_review_date", "sources",
})
_SOURCE = frozenset({"url", "observed_at", "claim"})
_POSITION = frozenset({"symbol", "kind", "weight_bps", "theme_attribution_bps"})


class StrategicContractError(ValueError):
    """An input is incomplete, ambiguous or unsuitable for research projection."""


def _timestamp(value: Any, key: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise StrategicContractError(f"{key} must be ISO UTC ending in Z")
    try:
        stamp = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise StrategicContractError(f"{key} is not a timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
        raise StrategicContractError(f"{key} must be UTC")
    if stamp.isoformat().replace("+00:00", "Z") != value:
        raise StrategicContractError(f"{key} must be canonical")
    return stamp


def _date(value: Any, key: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise StrategicContractError(f"{key} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise StrategicContractError(f"{key} is not a real date") from exc


def _record(value: Any, keys: frozenset[str], key: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise StrategicContractError(f"{key} must contain its exact documented fields")
    return value


def _text(value: Any, key: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise StrategicContractError(f"{key} must be nonblank text within bounds")
    return value


def _identity(payload: dict, version: str, evaluated_at: str) -> tuple[str, datetime, datetime]:
    if payload["schema_version"] != version:
        raise StrategicContractError("unsupported schema version")
    workspace = payload["workspace_id"]
    if not isinstance(workspace, str) or not _WRK.fullmatch(workspace):
        raise StrategicContractError("invalid workspace scope")
    asof = _timestamp(payload["as_of"], "as_of")
    evaluation = _timestamp(evaluated_at, "evaluated_at")
    if asof > evaluation:
        raise StrategicContractError("as_of may not exceed evaluation time")
    return workspace, asof, evaluation


def _digest(payload: dict) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")).hexdigest()


def _url(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise StrategicContractError("source URL invalid")
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment:
        raise StrategicContractError("source requires a clean HTTPS URL")
    return value


def compile_strategic_atlas(intake: dict, *, evaluated_at: str) -> dict:
    """Build a deterministic thesis docket, never a rank or recommendation.

    Submitted HTTPS links are unverified assertions, not provenance proof.
    Names and classifications are analyst claims; no market data is fetched.
    """
    _record(intake, frozenset({"schema_version", "workspace_id", "as_of", "theses"}), "intake")
    workspace, asof, evaluation = _identity(intake, ATLAS_INPUT, evaluated_at)
    items = intake["theses"]
    if not isinstance(items, list) or len(items) > 200:
        raise StrategicContractError("thesis list must be bounded to 200")
    names: set[str] = set()
    entries = []
    counts = {theme: 0 for theme in sorted(THEMES)}
    source_links, overdue = 0, 0
    for index, item in enumerate(items):
        item = _record(item, _THESIS, f"theses[{index}]")
        key = item["id"]
        if not isinstance(key, str) or not _ID.fullmatch(key) or key in names:
            raise StrategicContractError("thesis ID malformed or repeated")
        names.add(key)
        name = _text(item["name"], "name", 160)
        kind = item["kind"]
        symbol = item["symbol"]
        if kind not in KINDS:
            raise StrategicContractError("unknown research entity kind")
        if kind in {"PUBLIC_EQUITY", "ETF"}:
            if not isinstance(symbol, str) or not _SYM.fullmatch(symbol):
                raise StrategicContractError("public security requires a canonical symbol")
        elif symbol is not None:
            raise StrategicContractError("private entity/research organization cannot claim a ticker")
        themes = item["themes"]
        if (not isinstance(themes, list) or not 1 <= len(themes) <= 6 or
                any(not isinstance(x, str) or x not in THEMES for x in themes) or
                len(set(themes)) != len(themes)):
            raise StrategicContractError("themes must be distinct recognized classifications")
        hypothesis = _text(item["hypothesis"], "hypothesis", 1000)
        disconfirmation = _text(item["disconfirmation"], "disconfirmation", 1000)
        review_date = _date(item["next_review_date"], "next_review_date")
        sources = item["sources"]
        if not isinstance(sources, list) or len(sources) > 12:
            raise StrategicContractError("sources must be a bounded list")
        source_urls = set()
        for j, source in enumerate(sources):
            source = _record(source, _SOURCE, f"source[{j}]")
            u = _url(source["url"])
            if u in source_urls:
                raise StrategicContractError("source URL duplicated")
            source_urls.add(u)
            at = _timestamp(source["observed_at"], "source.observed_at")
            if at > asof:
                raise StrategicContractError("source observed after thesis snapshot")
            _text(source["claim"], "source.claim", 600)
        for theme in themes:
            counts[theme] += 1
        source_links += len(sources)
        overdue += int(review_date < evaluation.date())
        entries.append({
            "id": key, "name": name, "symbol": symbol, "kind": kind,
            "themes": sorted(themes), "hypothesis": hypothesis,
            "disconfirmation": disconfirmation,
            "next_review_date": review_date.isoformat(),
            "unverified_source_count": len(sources),
            "sources_unverified": [{"url": source["url"],
                                    "observed_at": source["observed_at"],
                                    "claim": source["claim"]} for source in sources],
            "evidence_state": "LINKS_NOT_INDEPENDENTLY_VERIFIED" if sources else "MISSING_SOURCES",
            "review_state": "OVERDUE" if review_date < evaluation.date() else "SCHEDULED",
        })
    result = {
        "schema_version": ATLAS_OUTPUT,
        "workspace_id": workspace,
        "as_of": intake["as_of"],
        "evaluation_mode": "RESEARCH_ONLY",
        "source_verification": "NOT_PERFORMED",
        "stale_snapshot": (evaluation - asof).days > 120,
        "thesis_count": len(entries),
        "links_supplied_unverified": source_links,
        "overdue_reviews": overdue,
        "theme_mention_counts_not_investment_weights": counts,
        "theses": sorted(entries, key=lambda entry: entry["id"]),
        "broker_order_authority": False,
        "transfer_authority": False,
        "financial_advice_or_alpha_validated": False,
    }
    result["content_sha256"] = _digest(result)
    return result


def summarize_declared_exposure(intake: dict, *, evaluated_at: str) -> dict:
    """Sum declared holdings and ETF look-through WITHOUT claiming broker verification.

    Theme attribution for each security must be an exclusive distribution;
    unknown remainder and missing portfolio weights are never treated as 0.
    The caller must verify holdings and ETF constituent data separately.
    """
    _record(intake, frozenset({"schema_version", "workspace_id", "as_of", "positions"}), "exposure")
    workspace, asof, evaluation = _identity(intake, PORTFOLIO_INPUT, evaluated_at)
    positions = intake["positions"]
    if not isinstance(positions, list) or len(positions) > 300:
        raise StrategicContractError("positions must be a bounded list")
    if not positions:
        return {
            "schema_version": PORTFOLIO_OUTPUT,
            "workspace_id": workspace,
            "as_of": intake["as_of"],
            "evaluation_mode": "DECLARED_READ_ONLY_PROJECTION",
            "coverage_state": "NO_HOLDINGS_DATA",
            "portfolio_weight_declared_bps": 0,
            "unattributed_bps": None,
            "theme_exposure_bps": None,
            "stale_snapshot": (evaluation-asof).days > 30,
            "broker_account_verified": False,
            "broker_order_authority": False,
            "transfer_authority": False,
        }
    seen: set[str] = set()
    weight_sum = 0
    unknown = Decimal(0)
    themes = {theme: Decimal(0) for theme in sorted(THEMES)}
    for position in positions:
        position = _record(position, _POSITION, "position")
        symbol = position["symbol"]
        kind = position["kind"]
        weight = position["weight_bps"]
        splits = position["theme_attribution_bps"]
        if (not isinstance(symbol, str) or not _SYM.fullmatch(symbol) or symbol in seen
                or kind not in {"EQUITY", "ETF", "CASH"} or type(weight) is not int
                or not 0 < weight <= 10000 or not isinstance(splits, dict)):
            raise StrategicContractError("position symbol, type, or weight invalid")
        seen.add(symbol)
        weight_sum += weight
        if weight_sum > 10000:
            raise StrategicContractError("portfolio weights exceed 100 percent")
        split_sum = 0
        for theme, portion in splits.items():
            if theme not in THEMES or type(portion) is not int or not 0 <= portion <= 10000:
                raise StrategicContractError("invalid theme attribution")
            split_sum += portion
            if split_sum > 10000:
                raise StrategicContractError("theme look-through double counted")
            themes[theme] += Decimal(weight) * Decimal(portion) / Decimal(10000)
        if kind == "CASH" and split_sum:
            raise StrategicContractError("cash cannot have thematic equity exposure")
        if kind != "CASH":
            unknown += Decimal(weight) * Decimal(10000 - split_sum) / Decimal(10000)
    unknown += Decimal(10000 - weight_sum)
    result = {
        "schema_version": PORTFOLIO_OUTPUT,
        "workspace_id": workspace,
        "as_of": intake["as_of"],
        "evaluation_mode": "DECLARED_READ_ONLY_PROJECTION",
        "coverage_state": "INCOMPLETE" if unknown or weight_sum < 10000 else "DECLARED_COMPLETE_NOT_VERIFIED",
        "portfolio_weight_declared_bps": weight_sum,
        "unattributed_bps": float(round(unknown, 2)),
        "theme_exposure_bps": {k: float(round(v, 2)) for k, v in themes.items() if v},
        "stale_snapshot": (evaluation-asof).days > 30,
        "broker_account_verified": False,
        "broker_order_authority": False,
        "transfer_authority": False,
    }
    result["content_sha256"] = _digest(result)
    return result