from __future__ import annotations

import time
from typing import Any, Iterator

import httpx


class PluggyAPIError(RuntimeError):
    def __init__(self, status: int, payload: Any):
        super().__init__(f"Pluggy API error {status}: {payload}")
        self.status = status
        self.payload = payload


class PluggyClient:
    """Thin httpx-based client for the Pluggy REST API.

    Designed to be resilient to SDK-side enum drift: returns plain dicts.
    Auto-refreshes the apiKey before expiry.
    """

    BASE_URL = "https://api.pluggy.ai"
    API_KEY_TTL_SECONDS = 2 * 60 * 60  # Pluggy keys live ~2h
    REFRESH_MARGIN_SECONDS = 5 * 60     # refresh 5min before expiry

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._api_key = api_key
        self._api_key_issued_at = time.time() if api_key else 0.0
        self._http = httpx.Client(base_url=self.BASE_URL, timeout=timeout)

    # ------------------------------------------------------------------ auth
    def _need_refresh(self) -> bool:
        if not self._api_key:
            return True
        age = time.time() - self._api_key_issued_at
        return age >= (self.API_KEY_TTL_SECONDS - self.REFRESH_MARGIN_SECONDS)

    def authenticate(self, *, force: bool = False) -> str:
        if not force and not self._need_refresh():
            return self._api_key  # type: ignore[return-value]
        resp = self._http.post(
            "/auth",
            json={"clientId": self._client_id, "clientSecret": self._client_secret},
        )
        if resp.status_code >= 400:
            raise PluggyAPIError(resp.status_code, _safe_json(resp))
        self._api_key = resp.json()["apiKey"]
        self._api_key_issued_at = time.time()
        return self._api_key

    def _headers(self) -> dict[str, str]:
        return {"X-API-KEY": self.authenticate(), "Accept": "application/json"}

    # ------------------------------------------------------------- low-level
    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {}) | self._headers()
        resp = self._http.request(method, path, headers=headers, **kwargs)
        if resp.status_code == 401:
            # apiKey might have expired earlier than expected — refresh once
            self.authenticate(force=True)
            headers = kwargs.pop("headers", {}) | self._headers()
            resp = self._http.request(method, path, headers=headers, **kwargs)
        if resp.status_code >= 400:
            raise PluggyAPIError(resp.status_code, _safe_json(resp))
        return _safe_json(resp)

    # --------------------------------------------------------------- public
    def list_connectors(
        self,
        *,
        sandbox: bool = False,
        countries: list[str] | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"sandbox": str(sandbox).lower()}
        if countries:
            params["countries"] = ",".join(countries)
        if name:
            params["name"] = name
        data = self._request("GET", "/connectors", params=params)
        return data.get("results", [])

    def get_connector(self, connector_id: int) -> dict[str, Any]:
        return self._request("GET", f"/connectors/{connector_id}")

    def create_connect_token(
        self,
        *,
        client_user_id: str | None = None,
        item_id: str | None = None,
    ) -> str:
        body: dict[str, Any] = {}
        if client_user_id:
            body["clientUserId"] = client_user_id
        if item_id:
            body["itemId"] = item_id
        data = self._request("POST", "/connect_token", json=body)
        return data["accessToken"]

    def list_items(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/items")
        return data.get("results", data) if isinstance(data, dict) else data

    def get_item(self, item_id: str) -> dict[str, Any]:
        return self._request("GET", f"/items/{item_id}")

    def create_sandbox_item(self, connector_id: int, parameters: dict[str, str]) -> dict[str, Any]:
        return self._request(
            "POST",
            "/items",
            json={"connectorId": connector_id, "parameters": parameters},
        )

    def delete_item(self, item_id: str) -> None:
        self._request("DELETE", f"/items/{item_id}")

    def list_accounts(self, item_id: str) -> list[dict[str, Any]]:
        data = self._request("GET", "/accounts", params={"itemId": item_id})
        return data.get("results", [])

    def list_transactions(
        self,
        account_id: str,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        page_size: int = 500,
    ) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            params: dict[str, Any] = {
                "accountId": account_id,
                "pageSize": page_size,
                "page": page,
            }
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date
            data = self._request("GET", "/transactions", params=params)
            results = data.get("results", [])
            for tx in results:
                yield tx
            if len(results) < page_size:
                return
            page += 1

    def list_categories(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/categories")
        return data.get("results", [])

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "PluggyClient":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


def _safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return {"raw": resp.text}
