from __future__ import annotations

import re

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .db import FoundationSequence


_SCOPE_TABLE_COLUMN_MAP: dict[str, tuple[str, str]] = {
    "request_customer_refs": ("requests", "customer_ref"),
}


def _resolve_scope_lookup(scope: str) -> tuple[str, str] | None:
    if scope in _SCOPE_TABLE_COLUMN_MAP:
        return _SCOPE_TABLE_COLUMN_MAP[scope]
    if scope.startswith("users:"):
        return ("users_access_users", "code")
    if re.fullmatch(r"[a-z_][a-z0-9_]*", scope):
        return (scope, "code")
    return None


def reserve_code(session: Session, scope: str, prefix: str) -> str:
    row = next(
        (
            item
            for item in session.new
            if isinstance(item, FoundationSequence) and item.scope == scope
        ),
        None,
    )
    if row is None:
        row = session.get(FoundationSequence, scope)
    if row is None:
        # RU: Если FoundationSequence для scope ещё нет, но таблица уже содержит legacy rows,
        # sequence нужно поднять от текущего max-кода, иначе repeatable seed/post-migration path ловит UNIQUE на `*-00001`.
        existing_next = 1
        existing = None
        lookup = _resolve_scope_lookup(scope)
        if lookup is not None:
            table_name, column_name = lookup
            inspector = inspect(session.get_bind())
            if inspector.has_table(table_name):
                try:
                    with session.begin_nested():
                        existing = session.execute(
                            text(f'SELECT "{column_name}" FROM "{table_name}" ORDER BY "{column_name}" DESC LIMIT 1')
                        ).scalar_one_or_none()
                except SQLAlchemyError:
                    existing = None
        if existing and isinstance(existing, str) and existing.startswith(f"{prefix}-"):
            try:
                existing_next = int(existing.split("-")[-1]) + 1
            except ValueError:
                existing_next = 1
        row = FoundationSequence(scope=scope, next_value=existing_next + 1)
        session.add(row)
        value = existing_next
    else:
        value = int(row.next_value)
        row.next_value = value + 1
    return f"{prefix}-{value:05d}"
