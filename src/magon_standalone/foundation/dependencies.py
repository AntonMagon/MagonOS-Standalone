from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Callable, Generator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .models import AuthSession, UserAccount
from .observability import TelemetryState
from .security import AuthContext, ROLE_GUEST, resolve_user_roles
from .settings import FoundationSettings


@dataclass(slots=True)
class FoundationContainer:
    settings: FoundationSettings
    session_factory: sessionmaker
    telemetry: TelemetryState


def get_container(request: Request) -> FoundationContainer:
    return request.app.state.container


def get_db(container: FoundationContainer = Depends(get_container)) -> Generator[Session, None, None]:
    session = container.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_auth_context(
    request: Request,
    session: Session = Depends(get_db),
) -> AuthContext:
    header = request.headers.get("authorization", "").strip()
    if not header or not header.lower().startswith("bearer "):
        return AuthContext(user_id=None, role_code=ROLE_GUEST, email=None, full_name=None)

    token = header.split(" ", 1)[1].strip()
    auth_session = session.scalar(
        select(AuthSession).where(AuthSession.token == token, AuthSession.revoked_at.is_(None))
    )
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")
    expires_at = auth_session.expires_at
    if expires_at.tzinfo is None:
        # RU: SQLite в local/test хранит naive datetime; здесь явно считаем их UTC, чтобы auth expiry не расходился между sqlite и postgres.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="expired_token")
    user = session.scalar(select(UserAccount).where(UserAccount.id == auth_session.user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="inactive_user")
    return AuthContext(user_id=user.id, role_code=auth_session.role_code, email=user.email, full_name=user.full_name)


def require_roles(*allowed_roles: str) -> Callable[[AuthContext], AuthContext]:
    def dependency(auth: AuthContext = Depends(get_auth_context), session: Session = Depends(get_db)) -> AuthContext:
        if auth.user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_required")
        roles = set(resolve_user_roles(session, auth.user_id))
        roles.add(auth.role_code)
        if not roles.intersection(set(allowed_roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="insufficient_role")
        return auth

    return dependency
