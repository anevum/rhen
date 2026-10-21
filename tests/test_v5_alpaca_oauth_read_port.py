"""Only httpx mock transports; no Alpaca token, live account or network."""
import asyncio
import httpx
import pytest

from next_rhen.portfolio.alpaca_oauth_read_port import AlpacaOAuthReadPort
from next_rhen.portfolio.alpaca_snapshot import AlpacaSnapshotError

TOKEN = "synthetic-local-token-no-auth"


def test_mock_oauth_reads_both_fixed_paths_without_write_methods():
    records = []
    def fake(request):
        records.append((request.method, str(request.url), request.headers.get("Authorization")))
        payload = {"id": "not-a-real-account"} if request.url.path == "/v2/account" else []
        return httpx.Response(200, json=payload)
    port = AlpacaOAuthReadPort(environment="PAPER", oauth_token=TOKEN,
                              transport=httpx.MockTransport(fake))
    assert asyncio.run(port.get_json("/v2/account"))["id"] == "not-a-real-account"
    assert asyncio.run(port.get_json("/v2/positions")) == []
    assert records == [
        ("GET", "https://paper-api.alpaca.markets/v2/account", "Bearer " + TOKEN),
        ("GET", "https://paper-api.alpaca.markets/v2/positions", "Bearer " + TOKEN),
    ]
    assert not any(hasattr(port, name) for name in ("post", "delete", "submit_order", "buy", "sell"))


def test_live_environment_host_is_pinned():
    def fake(request):
        assert request.url.host == "api.alpaca.markets"
        assert request.method == "GET"
        return httpx.Response(200, json=[])
    port = AlpacaOAuthReadPort(environment="LIVE", oauth_token=TOKEN,
                              transport=httpx.MockTransport(fake))
    assert asyncio.run(port.get_json("/v2/positions")) == []


def test_arbitrary_paths_and_query_strings_are_rejected_without_http():
    count = []
    port = AlpacaOAuthReadPort(environment="PAPER", oauth_token=TOKEN,
                              transport=httpx.MockTransport(lambda req: count.append(req) or httpx.Response(200, json={})))
    for path in ("/v2/orders", "/v2/positions?symbol=ABC", "https://evil.example/api",
                 "/v2/account/configurations", "/v2/positions/TSLA", None, ""):
        with pytest.raises(AlpacaSnapshotError): asyncio.run(port.get_json(path))
    assert count == []


def test_unauthorized_redirect_unexpected_content_and_no_raw_body_leak():
    for response in (
        httpx.Response(302, headers={"location":"https://evil.example"}),
        httpx.Response(401, text="secret-token-should-not-surface"),
        httpx.Response(200, text="not-json", headers={"content-type":"text/plain"}),
        httpx.Response(200, content=b"a" * 2_000_001, headers={"content-type":"application/json"}),
    ):
        port = AlpacaOAuthReadPort(environment="LIVE", oauth_token=TOKEN,
                                  transport=httpx.MockTransport(lambda req: response))
        with pytest.raises(AlpacaSnapshotError) as info:
            asyncio.run(port.get_json("/v2/account"))
        assert "secret" not in str(info.value)
        assert TOKEN not in str(info.value)


def test_bad_environment_or_token_rejected_without_network():
    for env, token in (("IBKR", TOKEN), ("LIVE", ""), ("PAPER", "hi"), ("LIVE", TOKEN + "\n")):
        with pytest.raises(AlpacaSnapshotError):
            AlpacaOAuthReadPort(environment=env, oauth_token=token)
