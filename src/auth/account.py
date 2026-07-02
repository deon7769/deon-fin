from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from .passwords import hash_password, normalize_email, verify_password


class CursorLike(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> Any: ...
    def fetchone(self) -> Mapping[str, Any] | None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...
    def commit(self) -> None: ...


class InvalidCurrentPassword(Exception):
    """Raised when the current password cannot authorize an account change."""


class DuplicateEmail(Exception):
    """Raised when the requested login email is already assigned."""


@dataclass(frozen=True)
class AccountUpdateInput:
    user_id: str
    current_password: str
    email: str | None = None
    new_password: str | None = None
    now: datetime | None = None


@dataclass(frozen=True)
class AccountUpdateResult:
    user_id: str
    email: str
    display_name: str | None


def update_auth_account(conn: ConnectionLike, data: AccountUpdateInput) -> AccountUpdateResult:
    if not data.current_password:
        raise InvalidCurrentPassword("Current password is required")
    if data.email is None and data.new_password is None:
        raise ValueError("Email or new password is required")
    if data.new_password is not None and not data.new_password:
        raise ValueError("New password must not be empty")

    now = _coerce_now(data.now)
    cursor = conn.cursor()
    row = _fetch_user(cursor, user_id=data.user_id)
    if row is None or not verify_password(data.current_password, row.get("password_hash")):
        raise InvalidCurrentPassword("Invalid current password")

    next_email = normalize_email(data.email) if data.email is not None else str(row["email"])
    if not next_email:
        raise ValueError("Email must not be empty")

    password_hash = hash_password(data.new_password) if data.new_password is not None else None
    try:
        cursor.execute(
            """
            UPDATE users
            SET email = %(email)s,
                password_hash = COALESCE(%(password_hash)s, password_hash),
                password_changed_at = CASE
                    WHEN %(password_hash)s::text IS NULL THEN password_changed_at
                    ELSE %(now)s
                END,
                updated_at = %(now)s
            WHERE id = %(user_id)s
              AND status = 'active'
            RETURNING id, email, display_name
            """,
            {
                "user_id": data.user_id,
                "email": next_email,
                "password_hash": password_hash,
                "now": now,
            },
        )
        updated = cursor.fetchone()
        if updated is None:
            raise InvalidCurrentPassword("Invalid current password")

        cursor.execute(
            """
            UPDATE user_identities
            SET provider_subject = %(provider_subject)s,
                provider_email = %(provider_email)s
            WHERE user_id = %(user_id)s
              AND provider = 'local'
            """,
            {
                "user_id": data.user_id,
                "provider_subject": str(updated["email"]),
                "provider_email": str(updated["email"]),
            },
        )
        cursor.execute(
            """
            UPDATE user_security_state
            SET failed_login_count = 0,
                last_failed_login_at = NULL,
                locked_until = NULL,
                updated_at = %(now)s
            WHERE user_id = %(user_id)s
            """,
            {"user_id": data.user_id, "now": now},
        )
    except Exception as exc:
        if _is_unique_violation(exc):
            raise DuplicateEmail("Email already in use") from exc
        raise

    conn.commit()
    return AccountUpdateResult(
        user_id=str(updated["id"]),
        email=str(updated["email"]),
        display_name=updated.get("display_name"),
    )


def _fetch_user(cursor: CursorLike, *, user_id: str) -> Mapping[str, Any] | None:
    cursor.execute(
        """
        SELECT id, email, display_name, password_hash
        FROM users
        WHERE id = %(user_id)s
          AND status = 'active'
        LIMIT 1
        """,
        {"user_id": user_id},
    )
    return cursor.fetchone()


def _coerce_now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _is_unique_violation(exc: Exception) -> bool:
    return getattr(exc, "sqlstate", None) == "23505" or exc.__class__.__name__ == "UniqueViolation"
