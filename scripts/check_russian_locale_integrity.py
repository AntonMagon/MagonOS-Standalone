#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from magon_standalone.locale_integrity import scan_runtime_routes, scan_source_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Russian locale source-of-truth and shell routes for English leakage.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--static-only", action="store_true", help="Only check versioned Russian source files.")
    parser.add_argument("--web-url", help="Optional live web base URL for runtime route checks, e.g. http://127.0.0.1:3000")
    args = parser.parse_args()

    issues = scan_source_files(args.repo_root)

    if args.web_url and not args.static_only:
        # RU: Runtime-check нужен отдельно от source-файлов, чтобы ловить протёкшие английские ярлыки уже на живом shell, а не только в JSON/markdown.
        issues.extend(scan_runtime_routes(args.web_url))

    if issues:
        print("Russian locale integrity failed.")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Russian locale integrity passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
