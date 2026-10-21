"""Sector attribution is explicitly unverified; ETF exposure never double-valued."""
from copy import deepcopy
import pytest

from next_rhen.portfolio.alpaca_snapshot import normalize_alpaca_snapshot
from next_rhen.portfolio.theme_projection import project_long_book_themes, ThemeProjectionError

AT = "2026-10-21T22:00:00Z"
NOW = "2026-10-21T22:05:00Z"
W = "wrk_sectorresearch01"
ACCOUNT = "00000000-1111-4222-8333-123456789001"


def snapshot():
    return normalize_alpaca_snapshot(
        {"id": ACCOUNT, "currency": "USD", "status": "ACTIVE", "equity": "1200",
         "cash": "200", "buying_power": "200", "trading_blocked": False, "account_blocked": False},
        [
            {"symbol": "SMH", "asset_class": "us_equity", "side": "long", "qty": "1", "market_value": "700"},
            {"symbol": "ASML", "asset_class": "us_equity", "side": "long", "qty": "1", "market_value": "300"},
        ], workspace_id=W, expected_account_id=ACCOUNT, environment="PAPER",
        observed_at=AT, evaluated_at=NOW,
    )


def meta(symbol, kind, parts):
    return {"symbol": symbol, "security_kind": kind, "theme_attribution_bps": parts,
            "source_url": "https://example.org/holdings" if parts else None,
            "source_observed_at": AT if parts else None}


def intake():
    return {"workspace_id": W, "classifications": [
        meta("SMH", "ETF", {"SEMICONDUCTOR_DESIGN": 6000, "CHIP_EQUIPMENT": 4000}),
        meta("ASML", "EQUITY", {"CHIP_EQUIPMENT": 10000}),
    ]}


def test_etf_plus_individual_overlap_does_not_double_count_value():
    x = project_long_book_themes(snapshot(), intake(), evaluated_at=NOW)
    assert x["long_us_equity_book_usd"] == "1000.00"
    assert x["theme_exposure_usd"]["SEMICONDUCTOR_DESIGN"] == "420.00"
    assert x["theme_exposure_usd"]["CHIP_EQUIPMENT"] == "580.00"
    assert sum(map(float, x["theme_exposure_usd"].values())) == 1000
    assert x["denominator"] == "GROSS_LONG_US_EQUITY_HOLDINGS_NOT_ACCOUNT_EQUITY"
    assert x["coverage_state"] == "DECLARED_COMPLETE_UNVERIFIED"
    assert x["broker_account_verified"] is False
    assert x["broker_order_authority"] is False


def test_untagged_etf_remains_100percent_unknown():
    obj = intake(); obj["classifications"] = [meta("ASML", "EQUITY", {"CHIP_EQUIPMENT": 10000})]
    x = project_long_book_themes(snapshot(), obj, evaluated_at=NOW)
    assert x["unattributed_long_us_equity_usd"] == "700.00"
    assert x["coverage_state"] == "PARTIAL_UNVERIFIED_ATTRIBUTION"


def test_no_classifications_does_not_invent_semiconductor_exposure():
    x = project_long_book_themes(snapshot(), {"workspace_id": W, "classifications": []}, evaluated_at=NOW)
    assert x["theme_exposure_usd"] == {}
    assert x["unattributed_long_us_equity_usd"] == "1000.00"


def test_foreign_scope_rejected():
    x = intake(); x["workspace_id"] = "wrk_foreign2026xx"
    with pytest.raises(ThemeProjectionError): project_long_book_themes(snapshot(), x, evaluated_at=NOW)


def test_tampered_broker_snapshot_rejected_even_if_data_seems_fine():
    obj = snapshot(); obj["equity_usd"] = "9000.00"
    with pytest.raises(ThemeProjectionError, match="digest"):
        project_long_book_themes(obj, intake(), evaluated_at=NOW)


def test_no_duplicated_sector_allocation_above_100_percent():
    obj = intake(); obj["classifications"][0]["theme_attribution_bps"]["MEMORY"] = 1
    with pytest.raises(ThemeProjectionError): project_long_book_themes(snapshot(), obj, evaluated_at=NOW)


def test_unrecognized_theme_and_unverified_source_missing_rejected():
    obj = intake(); obj["classifications"][0]["theme_attribution_bps"] = {"BIOENERGY_NOT_THEME": 10000}
    with pytest.raises(ThemeProjectionError): project_long_book_themes(snapshot(), obj, evaluated_at=NOW)
    obj = intake(); obj["classifications"][0]["source_url"] = None
    with pytest.raises(ThemeProjectionError): project_long_book_themes(snapshot(), obj, evaluated_at=NOW)


def test_non_equity_holdings_not_silently_discarded():
    ss = snapshot(); ss["positions"][0]["asset_class"] = "crypto"
    # recompute digest to simulate even a rehashed but unsupported snapshot
    from hashlib import sha256
    import json
    ss["content_sha256"] = sha256(json.dumps({k:v for k,v in ss.items() if k!="content_sha256"}, sort_keys=True, separators=(",", ":"),allow_nan=False).encode()).hexdigest()
    with pytest.raises(ThemeProjectionError, match="complex"):
        project_long_book_themes(ss, intake(), evaluated_at=NOW)


def test_absent_classification_and_future_evidence_rejected():
    obj = intake(); obj["classifications"].append(meta("NVDA", "EQUITY", {}))
    with pytest.raises(ThemeProjectionError): project_long_book_themes(snapshot(), obj, evaluated_at=NOW)
    obj = intake(); obj["classifications"][0]["source_observed_at"] = "2027-01-01T00:00:00Z"
    with pytest.raises(ThemeProjectionError): project_long_book_themes(snapshot(), obj, evaluated_at=NOW)
