from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit_event
from ..dependencies import get_auth_context, get_db, require_roles
from ..models import AuthSession, UserAccount
from ..security import ROLE_ADMIN, AuthContext, issue_session, resolve_user_roles, verify_password

router = APIRouter(tags=["UsersAccess"])


class LoginPayload(BaseModel):
    email: EmailStr
    password: str = Field(min_length=3)
    role_code: str | None = None


@router.post("/api/v1/auth/login")
def login(payload: LoginPayload, request: Request, session: Session = Depends(get_db)) -> dict[str, object]:
    user = session.scalar(select(UserAccount).where(UserAccount.email == payload.email, UserAccount.deleted_at.is_(None)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    roles = set(resolve_user_roles(session, user.id))
    chosen_role = payload.role_code or user.default_role_code
    if chosen_role not in roles and chosen_role != user.default_role_code:
        raise HTTPException(status_code=403, detail="role_not_assigned")
    # RU: Роль явно пишем в session record, чтобы role-restricted переходы были аудируемыми и не зависели от "магии" клиентского выбора.
    auth_session = issue_session(
        session,
        user=user,
        role_code=chosen_role,
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None,
    )
    record_audit_event(
        session,
        module_name="users_access",
        action="login",
        entity_type="user",
        entity_id=user.id,
        entity_code=user.code,
        auth=AuthContext(user_id=user.id, role_code=chosen_role, email=user.email, full_name=user.full_name),
        reason="interactive_login",
        payload_json={"email": user.email, "role_code": chosen_role},
    )
    return {"token": auth_session.token, "role_code": auth_session.role_code, "user": {"id": user.id, "code": user.code, "email": user.email, "full_name": user.full_name}}


@router.post("/api/v1/auth/logout")
def logout(auth: AuthContext = Depends(get_auth_context), session: Session = Depends(get_db), request: Request = None) -> dict[str, object]:
    header = request.headers.get("authorization", "").strip() if request else ""
    token = header.split(" ", 1)[1].strip() if header.lower().startswith("bearer ") else ""
    auth_session = session.scalar(select(AuthSession).where(AuthSession.token == token))
    if auth_session is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    auth_session.revoked_at = datetime.now(timezone.utc)
    record_audit_event(
        session,
        module_name="users_access",
        action="logout",
        entity_type="user",
        entity_id=auth.user_id or "guest",
        entity_code=auth.email,
        auth=auth,
        reason="interactive_logout",
        payload_json=None,
    )
    return {"status": "logged_out"}


@router.get("/api/v1/auth/me")
def me(auth: AuthContext = Depends(get_auth_context), session: Session = Depends(get_db)) -> dict[str, object]:
    if auth.user_id is None:
        return {"authenticated": False, "role_code": auth.role_code}
    user = session.scalar(select(UserAccount).where(UserAccount.id == auth.user_id))
    roles = resolve_user_roles(session, auth.user_id)
    return {"authenticated": True, "user": {"id": user.id, "code": user.code, "email": user.email, "full_name": user.full_name}, "role_code": auth.role_code, "roles": roles}


@router.get("/api/v1/admin/users")
def admin_users(_: AuthContext = Depends(require_roles(ROLE_ADMIN)), session: Session = Depends(get_db)) -> dict[str, object]:
    items = session.scalars(select(UserAccount).order_by(UserAccount.created_at.asc())).all()
    return {
        "items": [
            {
                "id": item.id,
                "code": item.code,
                "email": item.email,
                "full_name": item.full_name,
                "default_role_code": item.default_role_code,
                "company_id": item.company_id,
                "is_active": item.is_active,
            }
            for item in items
        ]
    }
