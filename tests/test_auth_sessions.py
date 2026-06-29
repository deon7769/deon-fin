from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.auth.passwords import hash_password
from src.auth.sessions import (
    InvalidLogin,
    LoginInput,
    LoginRateLimited,
    authenticate_login,
    current_session,
    hash_for_storage,
    revoke_session,
)


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


def _login_input(**kwargs) -> LoginInput:
    data = {
        "email": " Davi@Example.COM ",
        "password": "correct horse battery staple",
        "ip_address": "203.0.113.10",
        "user_agent": "pytest",
        "pepper": "test-pepper",
        "now": datetime(2026, 6, 29, 12, 0, tzinfo=UTC),
    }
    data.update(kwargs)
    return LoginInput(**data)


def test_hash_for_storage_uses_pepper_and_context():
    first = hash_for_storage("value", pepper="pepper-a", context="session")
    second = hash_for_storage("value", pepper="pepper-b", context="session")
    third = hash_for_storage("value", pepper="pepper-a", context="ip")

    assert first != "value"
    assert first != second
    assert first != third
    assert len(first) == 64


def test_authenticate_login_creates_session_and_resets_security_state():
    password_hash = hash_password("correct horse battery staple")
    conn = FakeConnection(
        [
            {"failed_count": 0},
            {
                "user_id": "user-1",
                "email": "davi@example.com",
                "display_name": "Davi",
                "password_hash": password_hash,
                "user_status": "active",
                "failed_login_count": 2,
                "locked_until": None,
                "family_id": "family-1",
                "family_name": "Familia Principal",
                "family_status": "active",
                "member_role": "owner",
            },
            {"session_id": "session-1"},
        ],
    )

    result = authenticate_login(conn, _login_input())

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    session_params = next(
        params
        for statement, params in conn.cursor_obj.statements
        if "INSERT INTO sessions" in statement
    )
    assert result.user_id == "user-1"
    assert result.family_id == "family-1"
    assert result.family_role == "owner"
    assert result.session_id == "session-1"
    assert result.session_token
    assert session_params["token_hash"] != result.session_token
    assert result.expires_at == _login_input().now + timedelta(days=7)
    assert "INSERT INTO login_attempts" in sql
    assert "UPDATE user_security_state" in sql
    assert "UPDATE users" in sql
    assert conn.committed


def test_authenticate_login_uses_generic_error_and_records_unknown_user():
    conn = FakeConnection(
        [
            {"failed_count": 0},
            None,
        ],
    )

    with pytest.raises(InvalidLogin, match="Invalid email or password"):
        authenticate_login(conn, _login_input(email="nobody@example.com"))

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    assert "INSERT INTO login_attempts" in sql
    assert "unknown_user" in str(conn.cursor_obj.statements)
    assert conn.committed


def test_authenticate_login_locks_account_after_repeated_wrong_passwords():
    conn = FakeConnection(
        [
            {"failed_count": 0},
            {
                "user_id": "user-1",
                "email": "davi@example.com",
                "display_name": "Davi",
                "password_hash": hash_password("correct horse battery staple"),
                "user_status": "active",
                "failed_login_count": 4,
                "locked_until": None,
                "family_id": "family-1",
                "family_name": "Familia Principal",
                "family_status": "active",
                "member_role": "owner",
            },
        ],
    )

    with pytest.raises(InvalidLogin, match="Invalid email or password"):
        authenticate_login(conn, _login_input(password="wrong password"))

    lock_params = next(
        params
        for statement, params in conn.cursor_obj.statements
        if "locked_until = %(locked_until)s" in statement
    )
    assert lock_params["failed_login_count"] == 5
    assert lock_params["locked_until"] == _login_input().now + timedelta(minutes=15)
    assert conn.committed


def test_authenticate_login_commits_ip_rate_limit_attempt():
    conn = FakeConnection([{"failed_count": 20}])

    with pytest.raises(LoginRateLimited, match="Too many login attempts"):
        authenticate_login(conn, _login_input())

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    assert "INSERT INTO login_attempts" in sql
    assert "ip_rate_limited" in str(conn.cursor_obj.statements)
    assert conn.committed


def test_current_session_returns_active_user_family_context():
    raw_token = "raw-session-token"
    conn = FakeConnection(
        [
            {
                "session_id": "session-1",
                "user_id": "user-1",
                "email": "davi@example.com",
                "display_name": "Davi",
                "family_id": "family-1",
                "family_name": "Familia Principal",
                "family_status": "active",
                "member_role": "owner",
                "expires_at": datetime(2026, 6, 30, tzinfo=UTC),
                "revoked_at": None,
            },
        ],
    )

    result = current_session(
        conn,
        raw_token,
        pepper="test-pepper",
        now=datetime(2026, 6, 29, tzinfo=UTC),
    )

    assert result is not None
    assert result.session_id == "session-1"
    assert result.user_id == "user-1"
    assert result.family_id == "family-1"
    assert conn.committed


def test_revoke_session_hashes_token_before_updating():
    conn = FakeConnection([])

    revoke_session(
        conn,
        "raw-session-token",
        pepper="test-pepper",
        now=datetime(2026, 6, 29, tzinfo=UTC),
    )

    statement, params = conn.cursor_obj.statements[0]
    assert "UPDATE sessions" in statement
    assert params["token_hash"] != "raw-session-token"
    assert conn.committed
