from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from .passwords import normalize_email, verify_password

SESSION_COOKIE_NAME = "deon_session"
SESSION_TTL = timedelta(days=7)
ACCOUNT_FAILURE_LIMIT = 5
ACCOUNT_LOCK_TTL = timedelta(minutes=15)
IP_FAILURE_LIMIT = 20
IP_FAILURE_WINDOW = timedelta(minutes=15)
GENERIC_LOGIN_ERROR = "Invalid email or password"


class CursorLike(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> Any: ...
    def fetchone(self) -> dict[str, Any] | None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...
    def commit(self) -> None: ...


class InvalidLogin(Exception):
    """Raised for email/password failures without revealing which field failed."""


class LoginRateLimited(Exception):
    """Raised when account or IP lockout rules block a login attempt."""


class LoginForbidden(Exception):
    """Raised when credentials are valid but the user cannot open an app session."""


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str
    ip_address: str
    user_agent: str
    pepper: str
    now: datetime | None = None


@dataclass(frozen=True)
class LoginResult:
    session_id: str
    session_token: str
    user_id: str
    email: str
    display_name: str | None
    family_id: str
    family_name: str
    family_role: str
    expires_at: datetime


@dataclass(frozen=True)
class AuthSession:
    session_id: str
    user_id: str
    email: str
    display_name: str | None
    family_id: str
    family_name: str
    family_role: str


def hash_for_storage(value: str, *, pepper: str, context: str) -> str:
    payload = f"{context}:{value}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def authenticate_login(conn: ConnectionLike, data: LoginInput) -> LoginResult:
    now = _coerce_now(data.now)
    normalized = normalize_email(data.email)
    ip_hash = hash_for_storage(data.ip_address or "", pepper=data.pepper, context="ip")
    user_agent_hash = hash_for_storage(data.user_agent or "", pepper=data.pepper, context="user_agent")
    email_hash = hash_for_storage(normalized, pepper=data.pepper, context="email")
    cursor = conn.cursor()

    try:
        _enforce_ip_rate_limit(
            cursor,
            ip_hash=ip_hash,
            email_hash=email_hash,
            user_agent_hash=user_agent_hash,
            now=now,
        )
    except LoginRateLimited:
        conn.commit()
        raise

    row = _fetch_login_user(cursor, normalized)
    if row is None:
        _record_attempt(
            cursor,
            user_id=None,
            email_hash=email_hash,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            success=False,
            failure_reason="unknown_user",
            now=now,
        )
        conn.commit()
        raise InvalidLogin(GENERIC_LOGIN_ERROR)

    user_id = str(row["user_id"])
    if _is_locked(row, now):
        _record_attempt(
            cursor,
            user_id=user_id,
            email_hash=email_hash,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            success=False,
            failure_reason="account_locked",
            now=now,
        )
        conn.commit()
        raise LoginRateLimited("Account temporarily locked")

    if not verify_password(data.password, row.get("password_hash")):
        failed_count = int(row.get("failed_login_count") or 0) + 1
        locked_until = now + ACCOUNT_LOCK_TTL if failed_count >= ACCOUNT_FAILURE_LIMIT else None
        _set_security_failure(
            cursor,
            user_id=user_id,
            failed_login_count=failed_count,
            locked_until=locked_until,
            now=now,
        )
        _record_attempt(
            cursor,
            user_id=user_id,
            email_hash=email_hash,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            success=False,
            failure_reason="wrong_password",
            now=now,
        )
        conn.commit()
        raise InvalidLogin(GENERIC_LOGIN_ERROR)

    if row.get("user_status") != "active" or row.get("family_status") != "active" or not row.get("family_id"):
        _record_attempt(
            cursor,
            user_id=user_id,
            email_hash=email_hash,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
            success=False,
            failure_reason="inactive_user_or_family",
            now=now,
        )
        conn.commit()
        raise LoginForbidden("User or family is inactive")

    session_token = secrets.token_urlsafe(48)
    token_hash = hash_for_storage(session_token, pepper=data.pepper, context="session")
    expires_at = now + SESSION_TTL
    session_id = _create_session(
        cursor,
        user_id=user_id,
        family_id=str(row["family_id"]),
        token_hash=token_hash,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        expires_at=expires_at,
        now=now,
    )
    _record_attempt(
        cursor,
        user_id=user_id,
        email_hash=email_hash,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        success=True,
        failure_reason=None,
        now=now,
    )
    _reset_security_state(cursor, user_id=user_id, now=now)
    _touch_last_login(cursor, user_id=user_id, now=now)
    conn.commit()

    return LoginResult(
        session_id=session_id,
        session_token=session_token,
        user_id=user_id,
        email=str(row["email"]),
        display_name=row.get("display_name"),
        family_id=str(row["family_id"]),
        family_name=str(row["family_name"]),
        family_role=str(row["member_role"]),
        expires_at=expires_at,
    )


def current_session(
    conn: ConnectionLike,
    token: str,
    *,
    pepper: str,
    now: datetime | None = None,
) -> AuthSession | None:
    if not token:
        return None

    current_time = _coerce_now(now)
    token_hash = hash_for_storage(token, pepper=pepper, context="session")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            s.id AS session_id,
            u.id AS user_id,
            u.email AS email,
            u.display_name AS display_name,
            f.id AS family_id,
            f.name AS family_name,
            f.status AS family_status,
            fm.role AS member_role,
            s.expires_at AS expires_at,
            s.revoked_at AS revoked_at
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        JOIN families f ON f.id = s.active_family_id
        JOIN family_members fm ON fm.family_id = f.id AND fm.user_id = u.id
        WHERE s.token_hash = %(token_hash)s
          AND s.revoked_at IS NULL
          AND s.expires_at > %(now)s
          AND u.status = 'active'
          AND f.status = 'active'
          AND fm.status = 'active'
        LIMIT 1
        """,
        {"token_hash": token_hash, "now": current_time},
    )
    row = cursor.fetchone()
    if row is None:
        return None

    cursor.execute(
        """
        UPDATE sessions
        SET updated_at = %(now)s
        WHERE token_hash = %(token_hash)s
        """,
        {"token_hash": token_hash, "now": current_time},
    )
    conn.commit()
    return AuthSession(
        session_id=str(row["session_id"]),
        user_id=str(row["user_id"]),
        email=str(row["email"]),
        display_name=row.get("display_name"),
        family_id=str(row["family_id"]),
        family_name=str(row["family_name"]),
        family_role=str(row["member_role"]),
    )


def revoke_session(
    conn: ConnectionLike,
    token: str,
    *,
    pepper: str,
    now: datetime | None = None,
) -> None:
    token_hash = hash_for_storage(token, pepper=pepper, context="session")
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE sessions
        SET revoked_at = %(now)s,
            updated_at = %(now)s
        WHERE token_hash = %(token_hash)s
          AND revoked_at IS NULL
        """,
        {"token_hash": token_hash, "now": _coerce_now(now)},
    )
    conn.commit()


def _coerce_now(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _enforce_ip_rate_limit(
    cursor: CursorLike,
    *,
    ip_hash: str,
    email_hash: str,
    user_agent_hash: str,
    now: datetime,
) -> None:
    cursor.execute(
        """
        SELECT count(*) AS failed_count
        FROM login_attempts
        WHERE ip_hash = %(ip_hash)s
          AND success = false
          AND created_at >= %(since)s
        """,
        {"ip_hash": ip_hash, "since": now - IP_FAILURE_WINDOW},
    )
    row = cursor.fetchone() or {}
    if int(row.get("failed_count") or 0) < IP_FAILURE_LIMIT:
        return

    _record_attempt(
        cursor,
        user_id=None,
        email_hash=email_hash,
        ip_hash=ip_hash,
        user_agent_hash=user_agent_hash,
        success=False,
        failure_reason="ip_rate_limited",
        now=now,
    )
    raise LoginRateLimited("Too many login attempts")


def _fetch_login_user(cursor: CursorLike, normalized_email: str) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT
            u.id AS user_id,
            u.email AS email,
            u.display_name AS display_name,
            u.password_hash AS password_hash,
            u.status AS user_status,
            COALESCE(uss.failed_login_count, 0) AS failed_login_count,
            uss.locked_until AS locked_until,
            f.id AS family_id,
            f.name AS family_name,
            f.status AS family_status,
            fm.role AS member_role
        FROM users u
        LEFT JOIN user_security_state uss ON uss.user_id = u.id
        LEFT JOIN family_members fm ON fm.user_id = u.id AND fm.status = 'active'
        LEFT JOIN families f ON f.id = fm.family_id AND f.status = 'active'
        WHERE lower(u.email::text) = %(normalized_email)s
        ORDER BY fm.joined_at ASC NULLS LAST
        LIMIT 1
        """,
        {"normalized_email": normalized_email},
    )
    return cursor.fetchone()


def _is_locked(row: dict[str, Any], now: datetime) -> bool:
    locked_until = row.get("locked_until")
    return isinstance(locked_until, datetime) and locked_until > now


def _set_security_failure(
    cursor: CursorLike,
    *,
    user_id: str,
    failed_login_count: int,
    locked_until: datetime | None,
    now: datetime,
) -> None:
    cursor.execute(
        """
        UPDATE user_security_state
        SET failed_login_count = %(failed_login_count)s,
            last_failed_login_at = %(now)s,
            locked_until = %(locked_until)s,
            updated_at = %(now)s
        WHERE user_id = %(user_id)s
        """,
        {
            "user_id": user_id,
            "failed_login_count": failed_login_count,
            "locked_until": locked_until,
            "now": now,
        },
    )


def _reset_security_state(cursor: CursorLike, *, user_id: str, now: datetime) -> None:
    cursor.execute(
        """
        UPDATE user_security_state
        SET failed_login_count = 0,
            last_failed_login_at = NULL,
            locked_until = NULL,
            updated_at = %(now)s
        WHERE user_id = %(user_id)s
        """,
        {"user_id": user_id, "now": now},
    )


def _touch_last_login(cursor: CursorLike, *, user_id: str, now: datetime) -> None:
    cursor.execute(
        """
        UPDATE users
        SET last_login_at = %(now)s,
            updated_at = %(now)s
        WHERE id = %(user_id)s
        """,
        {"user_id": user_id, "now": now},
    )


def _create_session(
    cursor: CursorLike,
    *,
    user_id: str,
    family_id: str,
    token_hash: str,
    ip_hash: str,
    user_agent_hash: str,
    expires_at: datetime,
    now: datetime,
) -> str:
    cursor.execute(
        """
        INSERT INTO sessions (
            user_id,
            active_family_id,
            token_hash,
            expires_at,
            ip_hash,
            user_agent_hash,
            created_at,
            updated_at
        )
        VALUES (
            %(user_id)s,
            %(family_id)s,
            %(token_hash)s,
            %(expires_at)s,
            %(ip_hash)s,
            %(user_agent_hash)s,
            %(now)s,
            %(now)s
        )
        RETURNING id AS session_id
        """,
        {
            "user_id": user_id,
            "family_id": family_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "ip_hash": ip_hash,
            "user_agent_hash": user_agent_hash,
            "now": now,
        },
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Session insert did not return an id")
    return str(row["session_id"])


def _record_attempt(
    cursor: CursorLike,
    *,
    user_id: str | None,
    email_hash: str,
    ip_hash: str,
    user_agent_hash: str,
    success: bool,
    failure_reason: str | None,
    now: datetime,
) -> None:
    cursor.execute(
        """
        INSERT INTO login_attempts (
            user_id,
            normalized_email_hash,
            ip_hash,
            user_agent_hash,
            success,
            failure_reason,
            created_at
        )
        VALUES (
            %(user_id)s,
            %(email_hash)s,
            %(ip_hash)s,
            %(user_agent_hash)s,
            %(success)s,
            %(failure_reason)s,
            %(now)s
        )
        """,
        {
            "user_id": user_id,
            "email_hash": email_hash,
            "ip_hash": ip_hash,
            "user_agent_hash": user_agent_hash,
            "success": success,
            "failure_reason": failure_reason,
            "now": now,
        },
    )
