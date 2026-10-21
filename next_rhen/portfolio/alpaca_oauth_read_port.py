"""Narrow opt-in read-only Alpaca OAuth HTTP port for the RHEN successor.

Not mounted in production, not an OAuth authorization/consent flow, and not an
account connection. OAuth tokens must come from a reviewed private secret vault
and consent WITHOUT Alpaca's trading scope. Never expose this port to browsers.
"""
from __future__ import annotations

from typing import Any
import httpx

from .alpaca_snapshot import AlpacaSnapshotError

_GET_PATHS = frozenset({"/v2/account", "/v2/positions"})
_BASE = {
    "PAPER": "https://paper-api.alpaca.markets",
    "LIVE": "https://api.alpaca.markets",
}
_MAX_RESPONSE_BYTES = 2_000_000


class AlpacaOAuthReadPort:
    """GET-only trading-account projection, no account/orders mutation path."""

    def __init__(self, *, environment: str, oauth_token: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        if environment not in _BASE:
            raise AlpacaSnapshotError("unknown Alpaca environment")
        if (not isinstance(oauth_token, str) or
                not 16 <= len(oauth_token) <= 8192 or
                any(x.isspace() for x in oauth_token)):
            raise AlpacaSnapshotError("server-side OAuth bearer credential is missing or malformed")
        self._base = _BASE[environment]
        self._token = oauth_token
        self._transport = transport

    async def get_json(self, path: str) -> Any:
        if path not in _GET_PATHS:
            raise AlpacaSnapshotError("read-only Alpaca GET path not allowlisted")
        # No POST/PATCH/DELETE, no arbitrary endpoint, query, host or redirect.
        # Explicit proxy bypass keeps the broker request target fixed.
        try:
            async with httpx.AsyncClient(
                timeout=8.0, follow_redirects=False, trust_env=False,
                transport=self._transport,
            ) as client:
                response = await client.request(
                    "GET", self._base + path,
                    headers={"Authorization": "Bearer " + self._token,
                             "Accept": "application/json"},
                )
            if response.status_code != 200:
                raise AlpacaSnapshotError("read-only Alpaca provider request unavailable")
            if "application/json" not in response.headers.get("content-type", "").lower():
                raise AlpacaSnapshotError("Alpaca response is not JSON")
            if len(response.content) > _MAX_RESPONSE_BYTES:
                raise AlpacaSnapshotError("Alpaca response exceeds bounded projection size")
            return response.json()
        except (httpx.HTTPError, ValueError, UnicodeError):
            # Do not leak upstream headers, bearer tokens, account IDs or bodies.
            raise AlpacaSnapshotError("read-only Alpaca provider request unavailable") from None
