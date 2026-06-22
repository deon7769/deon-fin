from __future__ import annotations

from unittest.mock import MagicMock

from src.pluggy.client import PluggyClient, _cursor_after


def test_cursor_after_parses_next_query():
    nxt = "?accountId=abc&after=MjAyMC0xMC0xNVQwMDowMDowMC4wMDBa"
    assert _cursor_after(nxt) == "MjAyMC0xMC0xNVQwMDowMDowMC4wMDBa"


def test_list_transactions_v2_follows_cursor():
    client = PluggyClient("id", "secret", api_key="fake.jwt.token")
    client._api_key_issued_at = 0  # evita refresh durante o teste

    responses = [
        {
            "results": [{"id": "tx1", "date": "2026-01-01T00:00:00.000Z"}],
            "next": "?accountId=acc&after=cursor-1",
        },
        {
            "results": [{"id": "tx2", "date": "2026-01-02T00:00:00.000Z"}],
            "next": None,
        },
    ]
    client._request = MagicMock(side_effect=responses)  # type: ignore[method-assign]

    txs = list(
        client.list_transactions("acc", from_date="2026-01-01", to_date="2026-01-31")
    )

    assert [t["id"] for t in txs] == ["tx1", "tx2"]
    assert client._request.call_count == 2
    first_params = client._request.call_args_list[0].kwargs["params"]
    second_params = client._request.call_args_list[1].kwargs["params"]
    assert first_params == {
        "accountId": "acc",
        "dateFrom": "2026-01-01",
        "dateTo": "2026-01-31",
    }
    assert second_params == {"accountId": "acc", "after": "cursor-1"}


def test_list_investments_follows_page_pagination():
    client = PluggyClient("id", "secret", api_key="fake.jwt.token")
    client._api_key_issued_at = 0
    client._request = MagicMock(
        side_effect=[
            {
                "page": 1,
                "totalPages": 2,
                "results": [{"id": "inv-1", "code": "WEGE3"}],
            },
            {
                "page": 2,
                "totalPages": 2,
                "results": [{"id": "inv-2", "code": "CDB123"}],
            },
        ]
    )  # type: ignore[method-assign]

    investments = list(client.list_investments("item-1", page_size=100))

    assert [investment["id"] for investment in investments] == ["inv-1", "inv-2"]
    assert client._request.call_count == 2
    assert client._request.call_args_list[0].kwargs["params"] == {
        "itemId": "item-1",
        "page": 1,
        "pageSize": 100,
    }
    assert client._request.call_args_list[1].kwargs["params"] == {
        "itemId": "item-1",
        "page": 2,
        "pageSize": 100,
    }


def test_list_investment_transactions_follows_page_pagination():
    client = PluggyClient("id", "secret", api_key="fake.jwt.token")
    client._api_key_issued_at = 0
    client._request = MagicMock(
        side_effect=[
            {
                "page": 1,
                "totalPages": 2,
                "results": [{"id": "mov-1", "type": "BUY"}],
            },
            {
                "page": 2,
                "totalPages": 2,
                "results": [{"id": "mov-2", "type": "INTEREST"}],
            },
        ]
    )  # type: ignore[method-assign]

    transactions = list(client.list_investment_transactions("inv-1", page_size=50))

    assert [transaction["id"] for transaction in transactions] == ["mov-1", "mov-2"]
    assert client._request.call_count == 2
    assert client._request.call_args_list[0].args == (
        "GET",
        "/investments/inv-1/transactions",
    )
    assert client._request.call_args_list[0].kwargs["params"] == {
        "page": 1,
        "pageSize": 50,
    }
