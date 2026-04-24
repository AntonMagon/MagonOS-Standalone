#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from magon_standalone.supplier_intelligence.evaluation import SupplierParsingEvaluator, load_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate live supplier parsing against a labeled Vietnam dataset")
    parser.add_argument(
        "--dataset",
        default=str(REPO_ROOT / "evaluation" / "supplier_parsing" / "vn_wave1" / "manifest.json"),
    )
    parser.add_argument(
        "--output",
        default=str(REPO_ROOT / ".cache" / "supplier-eval" / "latest-report.json"),
    )
    parser.add_argument(
        "--evidence-dir",
        default=str(REPO_ROOT / ".cache" / "supplier-eval" / "samples"),
    )
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--sample-ids", default="")
    args = parser.parse_args()

    # RU: CLI всегда пишет machine-readable report и sample evidence, чтобы quality gate проверял измеримые данные, а не smoke-вывод в консоли.
    sample_ids = {item.strip() for item in args.sample_ids.split(",") if item.strip()} or None
    dataset = load_dataset(args.dataset)
    report = SupplierParsingEvaluator().evaluate_dataset(
        dataset,
        evidence_dir=args.evidence_dir,
        sample_ids=sample_ids,
        max_samples=args.max_samples,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
