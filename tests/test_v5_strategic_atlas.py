"""Isolated research-only RHEN strategic intelligence; no market/broker IO."""
from copy import deepcopy
import pytest

from next_rhen.research.strategic_atlas import (
    compile_strategic_atlas, summarize_declared_exposure, StrategicContractError,
    ATLAS_INPUT, PORTFOLIO_INPUT, THEMES,
)

ASOF = "2026-10-21T20:00:00Z"
EVALUATION = "2026-10-22T20:00:00Z"
W = "wrk_research2027"


def thesis(symbol="ASML"):
    return {
        "id": "chipmaking-asml", "name": "ASML Holding", "symbol": symbol,
        "kind": "PUBLIC_EQUITY", "themes": ["CHIP_EQUIPMENT"],
        "hypothesis": "Lithography intensity may increase with chip complexity.",
        "disconfirmation": "Capex declines or alternatives erode equipment demand.",
        "next_review_date": "2027-03-31",
        "sources": [{"url": "https://example.org/filing", "observed_at": ASOF,
                     "claim": "Analyst-supplied source link, not independently checked."}],
    }


def atlas():
    return {"schema_version": ATLAS_INPUT, "workspace_id": W,
            "as_of": ASOF, "theses": [thesis()]}


def portfolio():
    return {
        "schema_version": PORTFOLIO_INPUT, "workspace_id": W,
        "as_of": ASOF, "positions": [
            {"symbol": "SMH", "kind": "ETF", "weight_bps": 7000,
             "theme_attribution_bps": {"SEMICONDUCTOR_DESIGN": 6000, "CHIP_EQUIPMENT": 4000}},
            {"symbol": "ASML", "kind": "EQUITY", "weight_bps": 3000,
             "theme_attribution_bps": {"CHIP_EQUIPMENT": 10000}},
        ],
    }


def test_atlas_has_deterministic_digest_and_no_authority():
    one = compile_strategic_atlas(atlas(), evaluated_at=EVALUATION)
    two = compile_strategic_atlas(atlas(), evaluated_at=EVALUATION)
    assert one == two
    assert one["thesis_count"] == 1
    assert one["links_supplied_unverified"] == 1
    assert one["theses"][0]["sources_unverified"][0]["url"] == "https://example.org/filing"
    assert one["source_verification"] == "NOT_PERFORMED"
    assert one["broker_order_authority"] is False
    assert one["transfer_authority"] is False
    assert one["financial_advice_or_alpha_validated"] is False
    assert set(one["theme_mention_counts_not_investment_weights"]) == THEMES


def test_private_company_must_not_masquerade_as_tradeable_security():
    item = thesis()
    item.update({"name": "Biocomputing Company", "symbol": None,
                 "kind": "PRIVATE_COMPANY", "themes": ["BIOCOMPUTING"]})
    one = atlas()
    one["theses"] = [item]
    assert compile_strategic_atlas(one, evaluated_at=EVALUATION)["theses"][0]["symbol"] is None
    item["symbol"] = "BIO"
    with pytest.raises(StrategicContractError):
        compile_strategic_atlas(one, evaluated_at=EVALUATION)


def test_missing_citations_are_not_verified_and_overdue_is_explicit():
    obj = atlas()
    obj["theses"][0]["sources"] = []
    obj["theses"][0]["next_review_date"] = "2026-10-20"
    r = compile_strategic_atlas(obj, evaluated_at=EVALUATION)
    assert r["overdue_reviews"] == 1
    assert r["theses"][0]["evidence_state"] == "MISSING_SOURCES"


@pytest.mark.parametrize("field,value", [
    ("schema_version", "unknown"), ("workspace_id", "owner"),
    ("as_of", "2026-11-01T00:00:00Z"),
])
def test_atlas_rejects_invalid_identity(field, value):
    obj = atlas()
    obj[field] = value
    with pytest.raises(StrategicContractError):
        compile_strategic_atlas(obj, evaluated_at=EVALUATION)


def test_no_extra_sensitive_or_undeclared_fields():
    obj = atlas()
    obj["api_key"] = "wrong"
    with pytest.raises(StrategicContractError):
        compile_strategic_atlas(obj, evaluated_at=EVALUATION)
    obj = atlas()
    obj["theses"][0]["positions"] = [{"qty": 100}]
    with pytest.raises(StrategicContractError):
        compile_strategic_atlas(obj, evaluated_at=EVALUATION)


def test_no_invented_source_verification():
    for corrupt in (
        {"url": "http://example.com", "observed_at": ASOF, "claim": "Claim"},
        {"url": "https://someone:secret@example.com", "observed_at": ASOF, "claim": "Claim"},
        {"url": "https://example.com", "observed_at": "2027-01-01T00:00:00Z", "claim": "Claim"},
    ):
        obj = atlas()
        obj["theses"][0]["sources"] = [corrupt]
        with pytest.raises(StrategicContractError):
            compile_strategic_atlas(obj, evaluated_at=EVALUATION)


def test_duplicate_theses_and_unknown_sector_rejected():
    obj = atlas()
    obj["theses"].append(deepcopy(obj["theses"][0]))
    with pytest.raises(StrategicContractError):
        compile_strategic_atlas(obj, evaluated_at=EVALUATION)
    obj = atlas()
    obj["theses"][0]["themes"] = ["UNVERIFIED_FUSION_GENERATION"]
    with pytest.raises(StrategicContractError):
        compile_strategic_atlas(obj, evaluated_at=EVALUATION)


def test_portfolio_etf_and_direct_overlap_counted_as_exposure_not_double_value():
    r = summarize_declared_exposure(portfolio(), evaluated_at=EVALUATION)
    assert r["theme_exposure_bps"]["CHIP_EQUIPMENT"] == 5800.0
    assert r["theme_exposure_bps"]["SEMICONDUCTOR_DESIGN"] == 4200.0
    assert r["unattributed_bps"] == 0
    assert r["coverage_state"] == "DECLARED_COMPLETE_NOT_VERIFIED"
    assert r["broker_account_verified"] is False
    assert r["broker_order_authority"] is False


def test_missing_holdings_must_not_become_zero_sector_exposure():
    obj = portfolio()
    obj["positions"] = []
    r = summarize_declared_exposure(obj, evaluated_at=EVALUATION)
    assert r["coverage_state"] == "NO_HOLDINGS_DATA"
    assert r["theme_exposure_bps"] is None
    assert r["unattributed_bps"] is None


def test_missing_etf_lookthrough_remains_unattributed():
    obj = portfolio()
    obj["positions"][0]["theme_attribution_bps"] = {}
    r = summarize_declared_exposure(obj, evaluated_at=EVALUATION)
    assert r["coverage_state"] == "INCOMPLETE"
    assert r["unattributed_bps"] == 7000


def test_rejects_overconcentration_double_count_and_bool_weights():
    for bad in [11000, True, -100]:
        obj = portfolio()
        obj["positions"][0]["weight_bps"] = bad
        with pytest.raises(StrategicContractError):
            summarize_declared_exposure(obj, evaluated_at=EVALUATION)
    obj = portfolio()
    obj["positions"][0]["theme_attribution_bps"]["MEMORY"] = 1
    with pytest.raises(StrategicContractError):
        summarize_declared_exposure(obj, evaluated_at=EVALUATION)


def test_stale_data_reported_not_silently_treated_current():
    result = summarize_declared_exposure(portfolio(), evaluated_at="2027-02-01T00:00:00Z")
    assert result["stale_snapshot"] is True
    result = compile_strategic_atlas(atlas(), evaluated_at="2027-03-01T00:00:00Z")
    assert result["stale_snapshot"] is True


def test_foreign_workspace_and_unknown_payloads_fail_closed():
    obj = portfolio()
    obj["workspace_id"] = "wrk_123"
    with pytest.raises(StrategicContractError):
        summarize_declared_exposure(obj, evaluated_at=EVALUATION)
    obj = portfolio()
    obj["secret"] = "nope"
    with pytest.raises(StrategicContractError):
        summarize_declared_exposure(obj, evaluated_at=EVALUATION)