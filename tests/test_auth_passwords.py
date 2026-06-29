from __future__ import annotations

import pytest

from src.auth.passwords import hash_password, normalize_email, verify_password


def test_normalize_email_strips_and_lowercases():
    assert normalize_email("  Davi@Example.COM ") == "davi@example.com"


def test_normalize_email_collapses_internal_whitespace():
    assert normalize_email("  Davi   Silva@Example.COM ") == "davi silva@example.com"


def test_hash_password_uses_argon2_and_verifies():
    encoded = hash_password("correct horse battery staple")

    assert encoded.startswith("$argon2")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_hash_password_rejects_empty_password():
    with pytest.raises(ValueError, match="Password must not be empty"):
        hash_password("")


@pytest.mark.parametrize(
    ("password", "password_hash"),
    [
        ("x", None),
        ("", "$argon2..."),
    ],
)
def test_verify_password_returns_false_for_missing_inputs(
    password: str,
    password_hash: str | None,
):
    assert not verify_password(password, password_hash)


def test_verify_password_returns_false_for_invalid_hash():
    assert not verify_password("x", "not-a-real-hash")
