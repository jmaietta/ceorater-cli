"""HTTP client for the CEORater API."""

import sys

import requests

from ceorater import __version__

BASE_URL = "https://api.ceorater.com"
TIMEOUT = 15


class CEORaterError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        super().__init__(message)


class Client:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "User-Agent": f"ceorater-cli/{__version__}",
        })

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self.session.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
        if not resp.ok:
            try:
                body = resp.json()
                raise CEORaterError(
                    resp.status_code,
                    body.get("code", "UNKNOWN"),
                    body.get("error", resp.text),
                )
            except (ValueError, KeyError):
                raise CEORaterError(resp.status_code, "UNKNOWN", resp.text)
        return resp.json()

    def meta(self) -> dict:
        return self._get("/v1/meta")

    def lookup(self, ticker: str, fmt: str = "raw") -> dict | list:
        return self._get(f"/v1/ceo/{ticker}", {"format": fmt})

    def search(self, query: str, fmt: str = "raw") -> dict:
        return self._get("/v1/search", {"q": query, "format": fmt})

    def list_ceos(self, limit: int = 50, offset: int = 0, fmt: str = "raw") -> dict:
        return self._get("/v1/ceos", {"limit": limit, "offset": offset, "format": fmt})
