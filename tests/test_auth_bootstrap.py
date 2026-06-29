from __future__ import annotations

import pytest

from src.auth.bootstrap import BootstrapInput, bootstrap_admin_family


class FakeCursor:
    def __init__(self):
        self.statements = []
        self.results = [
            ("user-1",),
            ("family-1",),
            ("person-1",),
        ]

    def execute(self, sql, params=None):
        self.statements.append((sql, params or {}))
        return self

    def fetchone(self):
        return self.results.pop(0)


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True


def test_bootstrap_admin_family_creates_user_family_membership_and_person():
    conn = FakeConnection()
    result = bootstrap_admin_family(
        conn,
        BootstrapInput(
            email=" Davi@Example.COM ",
            password="correct horse battery staple",
            display_name="Davi",
            family_name="Familia Principal",
            family_slug="familia-principal",
        ),
    )

    sql = "\n".join(statement for statement, _params in conn.cursor_obj.statements)
    assert result.user_id == "user-1"
    assert result.family_id == "family-1"
    assert result.person_id == "person-1"
    assert conn.committed
    assert "INSERT INTO users" in sql
    assert "INSERT INTO user_identities" in sql
    assert "INSERT INTO families" in sql
    assert "INSERT INTO family_members" in sql
    assert "INSERT INTO family_people" in sql
    assert "INSERT INTO user_security_state" in sql
    assert conn.cursor_obj.statements[0][1]["email"] == "davi@example.com"
    assert conn.cursor_obj.statements[0][1]["password_hash"].startswith("$argon2")


def test_bootstrap_admin_family_rejects_empty_normalized_email_without_commit():
    conn = FakeConnection()

    with pytest.raises(ValueError, match="Admin email must not be empty"):
        bootstrap_admin_family(
            conn,
            BootstrapInput(
                email="   ",
                password="correct horse battery staple",
                display_name="Davi",
                family_name="Familia Principal",
                family_slug="familia-principal",
            ),
        )

    assert not conn.committed
    assert conn.cursor_obj.statements == []


def test_bootstrap_admin_family_rejects_empty_password_without_commit():
    conn = FakeConnection()

    with pytest.raises(ValueError, match="Admin password must not be empty"):
        bootstrap_admin_family(
            conn,
            BootstrapInput(
                email="davi@example.com",
                password="",
                display_name="Davi",
                family_name="Familia Principal",
                family_slug="familia-principal",
            ),
        )

    assert not conn.committed
    assert conn.cursor_obj.statements == []
