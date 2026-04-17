# RU: Файл входит в проверенный контур первой волны.
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import utc_now
from .models import AuthSession, UserAccount, UserRoleBinding

ROLE_GUEST = "guest"
ROLE_CUSTOMER = "customer"
ROLE_OPERATOR = "operator"
ROLE_ADMIN = "admin"
DEFAULT_SESSION_TTL = timedelta(hours=12)


def hash_password(password: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt.encode("utf-8"), 120_000)
    encoded = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256$120000${actual_salt}${encoded}"


def verify_password(password: str, encoded_password: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded_password.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), int(iterations))
    return hmac.compare_digest(base64.b64encode(candidate).decode("ascii"), digest)


def issue_session(session: Session, user: UserAccount, role_code: str, user_agent: str | None, remote_addr: str | None) -> AuthSession:
    record = AuthSession(
        token=secrets.token_urlsafe(32),
        user_id=user.id,
        role_code=role_code,
        expires_at=utc_now() + DEFAULT_SESSION_TTL,
        user_agent=user_agent,
        remote_addr=remote_addr,
    )
    session.add(record)
    session.flush()
    return record


def resolve_user_roles(session: Session, user_id: str) -> list[str]:
    rows = session.scalars(select(UserRoleBinding.role_code).where(UserRoleBinding.user_id == user_id)).all()
    if not rows:
        return []
    return sorted({str(item) for item in rows})


@dataclass(slots=True)
class AuthContext:
    user_id: str | None
    role_code: str
    email: str | None
    full_name: str | None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None
