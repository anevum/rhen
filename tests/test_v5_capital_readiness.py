"""Isolated capital discussion envelope; deliberately not verified bank data."""
from copy import deepcopy
import pytest

from next_rhen.finance.capital_readiness import (
    project_capital_readiness, ReadinessContractError, SCHEMA,
)

AT = "2026-10-21T20:00:00Z"
NOW = "2026-10-22T20:00:00Z"


def fixture():
    return {
        "schema_version": SCHEMA, "workspace_id": "wrk_familyscope2027",
        "reviewed_at": AT, "source_domain": "HOUSEHOLD", "currency": "USD",
        "liquid_balance_usd": "10000.00", "next_90d_obligations_usd": "3000.00",
        "reserve_floor_usd": "4500.00", "tax_holdback_usd": "500.00",
        "debt_commitments_usd": "400.00", "restricted_cash_usd": "300.00",
    }


def test_declared_surplus_is_not_authorization():
    x = project_capital_readiness(fixture(), evaluated_at=NOW)
    assert x["declared_commitments_usd"] == "8700.00"
    assert x["declared_surplus_for_review_usd"] == "1300.00"
    assert x["readiness"] == "DECLARED_SURPLUS_REVIEW_ONLY"
    assert x["source_state"] == "OWNER_DECLARED_NOT_BANK_VERIFIED"
    assert x["authorized_investment_amount_usd"] is None
    assert x["bank_or_broker_verified"] is False
    assert x["broker_order_authority"] is False
    assert x["transfer_authority"] is False
    assert x["cross_domain_cash_pooling"] is False
    assert x == project_capital_readiness(fixture(), evaluated_at=NOW)


def test_shortfall_cannot_be_negative_surplus():
    f = fixture(); f["liquid_balance_usd"] = "1200.00"
    x = project_capital_readiness(f, evaluated_at=NOW)
    assert x["declared_surplus_for_review_usd"] == "0.00"
    assert x["declared_shortfall_usd"] == "7500.00"
    assert x["readiness"] == "NO_DECLARED_SURPLUS"


def test_stale_declaration_never_ready_even_if_surplus():
    x = project_capital_readiness(fixture(), evaluated_at="2027-01-30T00:00:00Z")
    assert x["readiness"] == "STALE_REVIEW"
    assert x["next_step"] == "REFRESH_AND_VERIFY"
    assert x["authorized_investment_amount_usd"] is None


def test_business_money_not_assumed_household_money():
    f = fixture(); f["source_domain"] = "ANEVUM_BUSINESS"
    x = project_capital_readiness(f, evaluated_at=NOW)
    assert x["source_domain"] == "ANEVUM_BUSINESS"
    assert x["cross_domain_cash_pooling"] is False
    assert x["broker_cash_counted_as_household_cash"] is False


def test_invalid_money_never_becomes_zero():
    for v in ("-1", "1,000", "1.999", "NaN", "Infinity", "1e9", 100, True, None):
        f = fixture(); f["liquid_balance_usd"] = v
        with pytest.raises(ReadinessContractError): project_capital_readiness(f, evaluated_at=NOW)


def test_unrecognized_source_and_credential_fields_fail_closed():
    for domain in ("COMBINED", "ALPACA", "ANY", None):
        f = fixture(); f["source_domain"] = domain
        with pytest.raises(ReadinessContractError): project_capital_readiness(f, evaluated_at=NOW)
    f = fixture(); f["api_secret"] = "not_allowed"
    with pytest.raises(ReadinessContractError): project_capital_readiness(f, evaluated_at=NOW)


def test_workspace_future_review_and_currency_refused():
    for key, value in (("workspace_id", "rhen"), ("reviewed_at", "2026-10-23T21:00:00Z"),
                       ("currency", "EUR")):
        f = fixture(); f[key] = value
        with pytest.raises(ReadinessContractError): project_capital_readiness(f, evaluated_at=NOW)
