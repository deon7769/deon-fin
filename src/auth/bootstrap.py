from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .passwords import hash_password, normalize_email


class Cursor(Protocol):
    def execute(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        ...

    def fetchone(self) -> tuple[Any, ...] | None:
        ...


class Connection(Protocol):
    def cursor(self) -> Cursor:
        ...

    def commit(self) -> None:
        ...


@dataclass(frozen=True)
class BootstrapInput:
    email: str
    password: str
    display_name: str
    family_name: str
    family_slug: str


@dataclass(frozen=True)
class BootstrapResult:
    user_id: str
    family_id: str
    person_id: str


def _returned_id(cursor: Cursor, label: str) -> str:
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Bootstrap failed to return {label} id")
    return str(row[0])


def bootstrap_admin_family(conn: Connection, data: BootstrapInput) -> BootstrapResult:
    email = normalize_email(data.email)
    if not email:
        raise ValueError("Admin email must not be empty")
    if not data.password:
        raise ValueError("Admin password must not be empty")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (
            email,
            password_hash,
            display_name,
            status,
            password_changed_at,
            updated_at
        )
        VALUES (
            %(email)s,
            %(password_hash)s,
            %(display_name)s,
            'active',
            now(),
            now()
        )
        ON CONFLICT (email) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            display_name = EXCLUDED.display_name,
            status = 'active',
            password_changed_at = now(),
            updated_at = now()
        RETURNING id
        """,
        {
            "email": email,
            "password_hash": hash_password(data.password),
            "display_name": data.display_name,
        },
    )
    user_id = _returned_id(cursor, "user")

    cursor.execute(
        """
        INSERT INTO user_identities (
            user_id,
            provider,
            provider_subject,
            provider_email
        )
        VALUES (
            %(user_id)s,
            'local',
            %(email)s,
            %(email)s
        )
        ON CONFLICT (provider, provider_subject)
            WHERE provider_subject IS NOT NULL
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            provider_email = EXCLUDED.provider_email
        """,
        {"user_id": user_id, "email": email},
    )

    cursor.execute(
        """
        INSERT INTO families (
            name,
            slug,
            status,
            created_by_user_id,
            updated_at
        )
        VALUES (
            %(family_name)s,
            %(family_slug)s,
            'active',
            %(user_id)s,
            now()
        )
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            status = 'active',
            created_by_user_id = COALESCE(families.created_by_user_id, EXCLUDED.created_by_user_id),
            updated_at = now()
        RETURNING id
        """,
        {
            "family_name": data.family_name,
            "family_slug": data.family_slug,
            "user_id": user_id,
        },
    )
    family_id = _returned_id(cursor, "family")

    cursor.execute(
        """
        INSERT INTO family_members (
            family_id,
            user_id,
            role,
            status,
            invited_by_user_id
        )
        VALUES (
            %(family_id)s,
            %(user_id)s,
            'owner',
            'active',
            %(user_id)s
        )
        ON CONFLICT (family_id, user_id) DO UPDATE SET
            role = EXCLUDED.role,
            status = 'active',
            invited_by_user_id = COALESCE(
                family_members.invited_by_user_id,
                EXCLUDED.invited_by_user_id
            )
        """,
        {"family_id": family_id, "user_id": user_id},
    )

    cursor.execute(
        """
        INSERT INTO user_security_state (user_id)
        VALUES (%(user_id)s)
        ON CONFLICT (user_id) DO NOTHING
        """,
        {"user_id": user_id},
    )

    cursor.execute(
        """
        INSERT INTO family_people (
            family_id,
            linked_user_id,
            display_name
        )
        VALUES (
            %(family_id)s,
            %(user_id)s,
            %(display_name)s
        )
        ON CONFLICT (family_id, linked_user_id)
            WHERE linked_user_id IS NOT NULL
        DO UPDATE SET
            display_name = excluded.display_name,
            status = 'active',
            updated_at = now()
        RETURNING id
        """,
        {
            "family_id": family_id,
            "user_id": user_id,
            "display_name": data.display_name,
        },
    )
    person_id = _returned_id(cursor, "person")

    conn.commit()
    return BootstrapResult(user_id=user_id, family_id=family_id, person_id=person_id)
