"""Offline contract tests: no real account, credentials, network or order API."""
import asyncio
from copy import deepcopy
import pytest

from next_rhen.portfolio.alpaca_snapshot import (
    normalize_alpaca_snapshot, read_alpaca_snapshot, AlpacaSnapshotError, SCHEMA,
)

W = "wrk_alpacaportfolio01"
A = "00000000-1111-4222-8333-123456789001"
OBS = "2026-10-21T22:00:00Z"
NOW = "2026-10-21T22:02:00Z"


def account():
    return {
        "id": A, "currency": "USD", "status": "ACTIVE", "equity": "1980.25",
        "cash": "150.00", "buying_power": "150.00", "trading_blocked": False,
        "account_blocked": False, "account_number": None,
    }


def positions():
    return [
        {"symbol": "NVDA", "qty": "1.125", "side": "long", "market_value": "1800.50", "asset_class": "us_equity"},
        {"symbol": "SGOV", "qty": "0.2", "side": "long", "market_value": "29.75", "asset_class": "us_equity"},
    ]


def normalize(**kwargs):
    return normalize_alpaca_snapshot(account(), positions(), workspace_id=W,
                                     expected_account_id=A, environment="PAPER",
                                     observed_at=OBS, evaluated_at=NOW, **kwargs)


def test_readonly_snapshot_preserves_actual_values_and_no_authority():
    r = normalize()
    assert r["schema_version"] == SCHEMA
    assert r["holdings_count"] == 2
    assert r["equity_usd"] == "1980.25"
    assert r["long_market_value_usd"] == "1830.25"
    assert r["cash_usd"] == "150.00"
    assert r["read_consistency"].startswith("NONATOMIC")
    assert r["account_equity_reconciled"] is False
    assert r["positions"][0]["symbol"] == "NVDA"
    assert r["positions"][0]["theme_exposure"].startswith("UNKNOWN")
    assert r["source_state"] == "PROVIDER_PAYLOAD_NOT_INDEPENDENTLY_ATTESTED"
    assert r["broker_order_authority"] is False and r["transfer_authority"] is False
    assert A not in repr(r)
    assert "account_number" not in repr(r)
    assert r == normalize()


def test_readonly_port_calls_two_precise_gets_only():
    class Port:
        def __init__(self): self.paths = []
        async def get_json(self, path):
            self.paths.append(path)
            return deepcopy(account() if path == "/v2/account" else positions())
    p = Port()
    r = asyncio.run(read_alpaca_snapshot(p, workspace_id=W, expected_account_id=A,
                                         environment="LIVE", observed_at=OBS, evaluated_at=NOW))
    assert p.paths == ["/v2/account", "/v2/positions"]
    assert r["environment"] == "LIVE"
    assert r["broker_order_authority"] is False


def test_account_mismatch_refuses_positions_query():
    class ForeignPort:
        def __init__(self): self.paths = []
        async def get_json(self, path):
            self.paths.append(path)
            return {**account(), "id": "foreign123456789"}
    p = ForeignPort()
    with pytest.raises(AlpacaSnapshotError, match="binding mismatch"):
        asyncio.run(read_alpaca_snapshot(p, workspace_id=W, expected_account_id=A,
                                         environment="LIVE", observed_at=OBS, evaluated_at=NOW))
    assert p.paths == ["/v2/account"]


def test_missing_broker_or_credentials_rejected():
    for key in ("APCA-API-SECRET-KEY", "authorization", "access_token"):
        a = account(); a[key] = "fake"
        with pytest.raises(AlpacaSnapshotError):
            normalize_alpaca_snapshot(a, positions(), workspace_id=W,
                                      expected_account_id=A, environment="PAPER",
                                      observed_at=OBS, evaluated_at=NOW)


def test_wrong_account_future_and_environment_fail_closed():
    base = dict(workspace_id=W, expected_account_id=A, environment="PAPER", observed_at=OBS, evaluated_at=NOW)
    for key, val in (("workspace_id", "other"), ("expected_account_id", "unexpected1"),
                     ("environment", "DEMO"), ("observed_at", "2026-10-22T22:00:00Z")):
        obj = dict(base); obj[key] = val
        with pytest.raises(AlpacaSnapshotError): normalize_alpaca_snapshot(account(), positions(), **obj)


def test_boolean_numbers_nan_and_incomplete_account_refused():
    for field, val in (("equity", True), ("cash", "NaN"), ("buying_power", None),
                       ("currency", "EUR"), ("account_blocked", "false")):
        bad = account(); bad[field] = val
        with pytest.raises(AlpacaSnapshotError):
            normalize_alpaca_snapshot(bad, positions(), workspace_id=W,
                                      expected_account_id=A, environment="PAPER",
                                      observed_at=OBS, evaluated_at=NOW)


def test_missing_symbol_duplicate_and_inconsistent_side_rejected():
    samples = [
        [positions()[0], deepcopy(positions()[0])],
        [{**positions()[0], "symbol": "aapl"}],
        [{**positions()[0], "side": "short"}],
        [{**positions()[0], "qty": "0"}],
        [{**positions()[0], "market_value": "NaN"}],
    ]
    for sample in samples:
        with pytest.raises(AlpacaSnapshotError):
            normalize_alpaca_snapshot(account(), sample, workspace_id=W,
                                      expected_account_id=A, environment="PAPER",
                                      observed_at=OBS, evaluated_at=NOW)


def test_shorts_are_visible_not_silently_counted_as_positive_equity():
    p = [{"symbol": "TSLA", "qty": "-2", "side": "short", "market_value": "-610.22", "asset_class": "us_equity"}]
    r = normalize_alpaca_snapshot(account(), p, workspace_id=W,
                                  expected_account_id=A, environment="LIVE",
                                  observed_at=OBS, evaluated_at=NOW)
    assert r["long_market_value_usd"] == "0.00"
    assert r["short_market_value_usd"] == "610.22"
    assert r["positions"][0]["signed_market_value_usd"] == "-610.22"
    assert r["account_equity_reconciled"] is False


def test_empty_positions_means_empty_response_not_no_account():
    r = normalize_alpaca_snapshot(account(), [], workspace_id=W,
                                  expected_account_id=A, environment="PAPER",
                                  observed_at=OBS, evaluated_at=NOW)
    assert r["positions"] == [] and r["holdings_count"] == 0
    assert r["cash_usd"] == "150.00" and r["account_equity_reconciled"] is False


def test_stale_and_blocked_account_retain_uncertainty():
    a = account(); a["trading_blocked"] = True
    r = normalize_alpaca_snapshot(a, [], workspace_id=W,
                                  expected_account_id=A, environment="PAPER",
                                  observed_at=OBS, evaluated_at="2026-10-22T22:00:00Z")
    assert r["freshness"] == "STALE"
    assert r["account_trading_blocked"] is True
    assert r["broker_order_authority"] is False


def test_unsupported_get_port_fails_closed():
    with pytest.raises(AlpacaSnapshotError):
        asyncio.run(read_alpaca_snapshot(object(), workspace_id=W, expected_account_id=A,
                                         environment="PAPER", observed_at=OBS, evaluated_at=NOW))
