#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

if [ -z "${PYTHON_BIN:-}" ]; then
  echo "verify-supplier-parsing-quality: python interpreter not found" >&2
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

DATASET_PATH="${1:-$REPO_ROOT/evaluation/supplier_parsing/vn_wave1/manifest.json}"
REPORT_DIR="${REPORT_DIR:-$REPO_ROOT/.cache/supplier-eval/acceptance}"
REPORT_PATH="${REPORT_PATH:-$REPORT_DIR/latest-report.json}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$REPORT_DIR/samples}"
STDOUT_LOG="${STDOUT_LOG:-$REPORT_DIR/evaluate.stdout}"
THRESHOLDS_PATH="${THRESHOLDS_PATH:-$REPORT_DIR/thresholds.json}"

mkdir -p "$REPORT_DIR" "$EVIDENCE_DIR"

if [ ! -f "$DATASET_PATH" ]; then
  echo "verify-supplier-parsing-quality: dataset not found: $DATASET_PATH" >&2
  exit 1
fi

# RU: Gate сначала валит отсутствие живого runtime, чтобы fixture-ready состояние не могло пройти как wave1 acceptance.
"$PYTHON_BIN" - <<'PY'
import json
import sys

from magon_standalone.supplier_intelligence.live_runtime import probe_live_runtime

probe = probe_live_runtime(force_refresh=True)
print(json.dumps({"runtime_probe": {"ok": probe.ok, "detail": probe.detail, "payload": probe.payload}}, ensure_ascii=False, indent=2))
raise SystemExit(0 if probe.ok else 1)
PY

"$PYTHON_BIN" scripts/evaluate_supplier_parsing.py \
  --dataset "$DATASET_PATH" \
  --output "$REPORT_PATH" \
  --evidence-dir "$EVIDENCE_DIR" \
  >"$STDOUT_LOG"

# RU: Threshold block держит канонические wave1 пороги рядом с verify, чтобы push не проходил на частично зелёном parsing contour.
"$PYTHON_BIN" - <<'PY' "$REPORT_PATH" "$EVIDENCE_DIR" "$THRESHOLDS_PATH"
from __future__ import annotations

import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
evidence_dir = Path(sys.argv[2])
thresholds_path = Path(sys.argv[3])

if not report_path.exists():
    raise SystemExit("verify-supplier-parsing-quality: report was not generated")

report = json.loads(report_path.read_text(encoding="utf-8"))
sample_count = int(report.get("sample_count") or 0)
evidence_count = len(list(evidence_dir.glob("*.json")))
if sample_count <= 0:
    raise SystemExit("verify-supplier-parsing-quality: empty evaluation report")
if evidence_count < sample_count:
    raise SystemExit(
        f"verify-supplier-parsing-quality: evidence missing ({evidence_count}/{sample_count} files)"
    )

summary = report.get("summary") or {}
field_metrics = summary.get("field_metrics") or {}
source_breakdown = summary.get("source_class_breakdown") or {}

checks = [
    ("overall_extraction_success", float(summary.get("extraction_success_rate") or 0.0), 0.70),
    ("directory_listing", float((source_breakdown.get("directory_listing") or {}).get("extraction_success_rate") or 0.0), 0.80),
    ("simple_supplier_site", float((source_breakdown.get("simple_supplier_site") or {}).get("extraction_success_rate") or 0.0), 0.55),
    ("js_heavy_supplier_site", float((source_breakdown.get("js_heavy_supplier_site") or {}).get("extraction_success_rate") or 0.0), 0.60),
    ("website_exact", float((field_metrics.get("website") or {}).get("exact_match_rate") or 0.0), 0.90),
    ("phone_exact", float((field_metrics.get("phone") or {}).get("exact_match_rate") or 0.0), 0.80),
    ("email_exact", float((field_metrics.get("email") or {}).get("exact_match_rate") or 0.0), 0.70),
    ("supplier_name_exact", float((field_metrics.get("supplier_name") or {}).get("exact_match_rate") or 0.0), 0.65),
    ("address_exact", float((field_metrics.get("address") or {}).get("exact_match_rate") or 0.0), 0.45),
    ("city_region_exact", float((field_metrics.get("city_region") or {}).get("exact_match_rate") or 0.0), 0.55),
]

results = [
    {
        "metric": name,
        "actual": round(actual, 4),
        "threshold": threshold,
        "passed": actual >= threshold,
    }
    for name, actual, threshold in checks
]
status = all(item["passed"] for item in results)
payload = {
    "status": "passed" if status else "failed",
    "sample_count": sample_count,
    "evidence_count": evidence_count,
    "checks": results,
    "failed_samples": summary.get("failed_samples") or [],
    "failed_samples_by_class": summary.get("failed_samples_by_class") or {},
    "company_site_breakdown": summary.get("company_site_breakdown") or {},
    "report_path": str(report_path),
    "evidence_dir": str(evidence_dir),
}

thresholds_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if status else 1)
PY
