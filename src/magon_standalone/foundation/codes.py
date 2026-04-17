from __future__ import annotations

from sqlalchemy.orm import Session

from .db import FoundationSequence


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
        # RU: новый scope должен резервироваться idempotent даже при серии вызовов
        # в одной транзакции до flush, иначе последовательность ломается на UNIQUE.
        row = FoundationSequence(scope=scope, next_value=2)
        session.add(row)
        value = 1
    else:
        value = int(row.next_value)
        row.next_value = value + 1
    return f"{prefix}-{value:05d}"
