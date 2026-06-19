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
