# RU: Файл входит в проверенный контур первой волны.
#!/usr/bin/env python3
from __future__ import annotations

import json

from magon_standalone.foundation.bootstrap import seed_foundation
from magon_standalone.foundation.db import create_session_factory, session_scope
from magon_standalone.foundation.settings import load_settings


def main() -> int:
    settings = load_settings()
    session_factory = create_session_factory(settings)
    with session_scope(session_factory) as session:
        payload = seed_foundation(session, settings)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
