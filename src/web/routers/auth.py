from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ...auth.account import (
    AccountUpdateInput,
    AccountUpdateResult,
    DuplicateEmail,
    InvalidCurrentPassword,
    update_auth_account,
)
from ...auth.sessions import (
    SESSION_COOKIE_NAME,
    InvalidLogin,
    LoginForbidden,
    LoginInput,
    LoginRateLimited,
    LoginResult,
    authenticate_login,
    current_session,
    revoke_session,
)
from ...config import settings
from ...storage.postgres import connect_postgres
from ..dependencies import get_postgres_conn

router = APIRouter(prefix="/api/auth", tags=["auth"])
SESSION_MARKER_COOKIE_NAME = "deon_session_present"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AccountUpdateRequest(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: str | None = Field(default=None, min_length=8, max_length=1024)


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    conn=Depends(get_postgres_conn),
) -> dict[str, object]:
    pepper = _require_auth_pepper()
    try:
        result = authenticate_login(
            conn,
            LoginInput(
                email=payload.email,
                password=payload.password,
                ip_address=_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                pepper=pepper,
                now=datetime.now(UTC),
            ),
        )
    except InvalidLogin as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except LoginRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LoginForbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    response.set_cookie(
        SESSION_COOKIE_NAME,
        result.session_token,
        httponly=True,
        secure=_cookie_secure(request),
        samesite="Lax",
        expires=result.expires_at,
        path="/",
    )
    response.set_cookie(
        SESSION_MARKER_COOKIE_NAME,
        "1",
        secure=_cookie_secure(request),
        samesite="Lax",
        expires=result.expires_at,
        path="/",
    )
    return _login_payload(result)


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, bool]:
    if session_token:
        _revoke_session_token(session_token, pepper=_require_auth_pepper(), now=datetime.now(UTC))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", samesite="Lax")
    response.delete_cookie(SESSION_MARKER_COOKIE_NAME, path="/", samesite="Lax")
    return {"ok": True}


@router.get("/me")
def me(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, object]:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = _current_session_for_token(session_token, pepper=_require_auth_pepper(), now=datetime.now(UTC))
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "authenticated": True,
        "user": {
            "id": session.user_id,
            "email": session.email,
            "display_name": session.display_name,
        },
        "family": {
            "id": session.family_id,
            "name": session.family_name,
            "role": session.family_role,
        },
    }


@router.patch("/me")
def update_me(
    payload: AccountUpdateRequest,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict[str, object]:
    if payload.email is None and payload.new_password is None:
        raise HTTPException(status_code=400, detail="Informe um novo e-mail ou uma nova senha")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    pepper = _require_auth_pepper()
    session = _current_session_for_token(session_token, pepper=pepper, now=datetime.now(UTC))
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        account = _update_account_credentials(session.user_id, payload, now=datetime.now(UTC))
    except InvalidCurrentPassword as exc:
        raise HTTPException(status_code=403, detail="Senha atual invalida") from exc
    except DuplicateEmail as exc:
        raise HTTPException(status_code=409, detail="Este e-mail ja esta em uso") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "authenticated": True,
        "user": {
            "id": account.user_id,
            "email": account.email,
            "display_name": account.display_name,
        },
        "family": {
            "id": session.family_id,
            "name": session.family_name,
            "role": session.family_role,
        },
    }


def _require_auth_pepper() -> str:
    pepper = settings.auth_pepper
    if not pepper:
        raise HTTPException(status_code=503, detail="AUTH_PEPPER is required for session authentication")
    return pepper


def _auth_database_url() -> str:
    return getattr(settings, "auth_database_url", None) or settings.database_url


def _current_session_for_token(session_token: str, *, pepper: str, now: datetime):
    with connect_postgres(_auth_database_url()) as conn:
        return current_session(conn, session_token, pepper=pepper, now=now)


def _revoke_session_token(session_token: str, *, pepper: str, now: datetime) -> None:
    with connect_postgres(_auth_database_url()) as conn:
        revoke_session(conn, session_token, pepper=pepper, now=now)


def _update_account_credentials(
    user_id: str,
    payload: AccountUpdateRequest,
    *,
    now: datetime,
) -> AccountUpdateResult:
    with connect_postgres(_auth_database_url()) as conn:
        return update_auth_account(
            conn,
            AccountUpdateInput(
                user_id=user_id,
                current_password=payload.current_password,
                email=payload.email,
                new_password=payload.new_password,
                now=now,
            ),
        )


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return ""


def _cookie_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()
    return forwarded_proto == "https" or request.url.scheme == "https"


def _login_payload(result: LoginResult) -> dict[str, object]:
    return {
        "authenticated": True,
        "user": {
            "id": result.user_id,
            "email": result.email,
            "display_name": result.display_name,
        },
        "family": {
            "id": result.family_id,
            "name": result.family_name,
            "role": result.family_role,
        },
        "session": {
            "id": result.session_id,
            "expires_at": result.expires_at.isoformat(),
        },
    }
