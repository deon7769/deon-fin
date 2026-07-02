from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.auth.account import AccountUpdateInput, InvalidCurrentPassword, update_auth_account
from src.auth.passwords import hash_password, verify_password


class FakeCursor:
    def __init__(self, rows):
        self.rows = list(rows)
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params or {}))
        return self

    def fetchone(self):
        if not self.rows:
            return None
        return self.rows.pop(0)


class FakeConnection:
    def __init__(self, rows):
        self.cursor_obj = FakeCursor(rows)
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


class PostgreSQLTypeCheckingCursor(FakeCursor):
    def execute(self, sql, params=None):
        if (
            "UPDATE users" in sql
            and (params or {}).get("password_hash") is None
            and "%(password_hash)s::text IS NULL" not in sql
        ):
            raise RuntimeError("could not determine data type of parameter")
        if (
            "UPDATE user_identities" in sql
            and "provider_subject = %(email)s" in sql
            and "provider_email = %(email)s" in sql
        ):
            raise RuntimeError("inconsistent types deduced for parameter")
        return super().execute(sql, params)


class PostgreSQLTypeCheckingConnection(FakeConnection):
    def __init__(self, rows):
        self.cursor_obj = PostgreSQLTypeCheckingCursor(rows)
        self.committed = False


def test_update_auth_account_changes_email_and_password_atomically():
    current_hash = hash_password("senha atual")
    conn = FakeConnection(
        [
            {
                "id": "user-1",
                "email": "antigo@example.com",
                "display_name": "Davi",
                "password_hash": current_hash,
            },
            {
                "id": "user-1",
                "email": "novo@example.com",
                "display_name": "Davi",
            },
        ],
    )
    now = datetime(2026, 7, 2, 12, 0, tzinfo=UTC)

    result = update_auth_account(
        conn,
        AccountUpdateInput(
            user_id="user-1",
            current_password="senha atual",
            email=" Novo@Example.COM ",
            new_password="senha nova forte",
            now=now,
        ),
    )

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    user_update = next(
        params
        for statement, params in conn.cursor_obj.statements
        if "UPDATE users" in statement
    )
    identity_update = next(
        params
        for statement, params in conn.cursor_obj.statements
        if "UPDATE user_identities" in statement
    )

    assert result.email == "novo@example.com"
    assert user_update["email"] == "novo@example.com"
    assert user_update["password_hash"] != "senha nova forte"
    assert verify_password("senha nova forte", user_update["password_hash"])
    assert user_update["now"] == now
    assert identity_update["provider_subject"] == "novo@example.com"
    assert identity_update["provider_email"] == "novo@example.com"
    assert "UPDATE user_security_state" in sql
    assert conn.committed


def test_update_auth_account_changes_email_only_without_ambiguous_null_password_param():
    conn = PostgreSQLTypeCheckingConnection(
        [
            {
                "id": "user-1",
                "email": "antigo@example.com",
                "display_name": "Davi",
                "password_hash": hash_password("senha atual"),
            },
            {
                "id": "user-1",
                "email": "novo@example.com",
                "display_name": "Davi",
            },
        ],
    )

    result = update_auth_account(
        conn,
        AccountUpdateInput(
            user_id="user-1",
            current_password="senha atual",
            email="novo@example.com",
            new_password=None,
        ),
    )

    user_update = next(
        params
        for statement, params in conn.cursor_obj.statements
        if "UPDATE users" in statement
    )
    assert result.email == "novo@example.com"
    assert user_update["password_hash"] is None
    assert conn.committed


def test_update_auth_account_rejects_wrong_current_password_without_writes():
    conn = FakeConnection(
        [
            {
                "id": "user-1",
                "email": "davi@example.com",
                "display_name": "Davi",
                "password_hash": hash_password("senha atual"),
            },
        ],
    )

    with pytest.raises(InvalidCurrentPassword):
        update_auth_account(
            conn,
            AccountUpdateInput(
                user_id="user-1",
                current_password="errada",
                email="novo@example.com",
                new_password="senha nova forte",
            ),
        )

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    assert "UPDATE users" not in sql
    assert not conn.committed
