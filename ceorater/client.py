"""HTTP client for the CEORater API.

There is no authentication. The API is free and keyless, so this carries no
Authorization header and there is nothing for a user to configure. The previous
version required CEORATER_API_KEY and pointed at api.ceorater.com/v1, a surface
that sat behind a billing gateway which no longer exists.
"""

import requests

from ceorater import __version__

BASE_URL = "https://api.ceorater.com/api/v1"
TIMEOUT = 30


class CEORaterError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        super().__init__(message)


class Client:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"ceorater-cli/{__version__}",
            "Accept": "application/json",
        })

    def _get(self, path: str, params: dict | None = None):
        params = {k: v for k, v in (params or {}).items() if v is not None}
        try:
            resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CEORaterError(0, "NETWORK", str(exc)) from exc
        if not resp.ok:
            try:
                body = resp.json()
                raise CEORaterError(resp.status_code,
                                    body.get("code", "UNKNOWN"),
                                    body.get("error", resp.text))
            except ValueError:
                raise CEORaterError(resp.status_code, "UNKNOWN", resp.text[:200])
        return resp.json()

    def meta(self) -> dict:
        return self._get("/meta")

    def lookup(self, ticker: str) -> dict:
        """One ticker. `items` is always a list -- co-CEOs give two records."""
        return self._get(f"/ceo/{ticker.strip().upper()}")

    def search(self, query: str) -> dict:
        return self._get("/search", {"q": query})

    def list_ceos(self, limit: int | None = None, offset: int = 0,
                  sector: str | None = None, industry: str | None = None,
                  founder: bool | None = None) -> dict:
        """No limit means every CEO. The API returns all of them by default."""
        return self._get("/ceos", {
            "limit": limit,
            "offset": offset or None,
            "sector": sector,
            "industry": industry,
            "founder": None if founder is None else str(bool(founder)).lower(),
        })

    def sectors(self) -> dict:
        return self._get("/sectors")

    def industries(self, sector: str | None = None) -> dict:
        return self._get("/industries", {"sector": sector})
