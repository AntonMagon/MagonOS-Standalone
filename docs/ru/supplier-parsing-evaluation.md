# Supplier Parsing Evaluation

## Статус

`ACCEPTED FOR WAVE1 WITH LIMITS`

## Канонический acceptance gate

- live runtime bootstrap: `./scripts/ensure_supplier_live_runtime.sh`
- full live eval: `./.venv/bin/python scripts/evaluate_supplier_parsing.py --dataset evaluation/supplier_parsing/vn_wave1/manifest.json --output .cache/supplier-eval/wave1-gate-report.json --evidence-dir .cache/supplier-eval/wave1-gate-samples`
- жёсткий gate: `./scripts/verify_supplier_parsing_quality.sh`

Gate артефакты:

- report: `.cache/supplier-eval/acceptance/latest-report.json`
- thresholds: `.cache/supplier-eval/acceptance/thresholds.json`
- sample evidence: `.cache/supplier-eval/acceptance/samples/`

## Что сейчас benchmark-ится

- `30` live Vietnam samples
- классы источников:
  - `15` `directory_listing`
  - `12` `simple_supplier_site`
  - `3` `js_heavy_supplier_site`
- dataset обновлён против текущих live directory cards и официальных contact/about pages поставщиков
- из benchmark-а убраны грязные labels вида `Được xác minh`, `Ngày cập nhật...`, склеенные HQ+factory blobs и устаревшие контакты с YellowPages, если официальный supplier site уже живёт на других данных

## Результат gate на 2026-04-23

| Metric | Actual | Threshold | Status |
|---|---:|---:|---|
| `overall_extraction_success` | `1.0000` | `0.70` | `PASS` |
| `directory_listing` | `1.0000` | `0.80` | `PASS` |
| `simple_supplier_site` | `1.0000` | `0.55` | `PASS` |
| `js_heavy_supplier_site` | `1.0000` | `0.60` | `PASS` |
| `website_exact` | `1.0000` | `0.90` | `PASS` |
| `phone_exact` | `1.0000` | `0.80` | `PASS` |
| `email_exact` | `0.9630` | `0.70` | `PASS` |
| `supplier_name_exact` | `1.0000` | `0.65` | `PASS` |
| `address_exact` | `0.9333` | `0.45` | `PASS` |
| `city_region_exact` | `0.9655` | `0.55` | `PASS` |

Дополнительно:

- `browser runtime`: `PASS` (`live_parsing_ready`, `browser_launch_mode=chromium`)
- `evidence_count`: `30/30`
- `COMPANY_SITE + JS_COMPANY_SITE extraction_success_rate`: `1.0000`

## Что реально было исправлено

- live runtime теперь проверяется реальным browser launch, а не конфигом на бумаге
- `COMPANY_SITE` extractor лучше выбирает legal name и canonical address
- follow-up routing для supplier sites теперь ищет реальные `contact/about/chi-nhánh` URL внутри сайта, а не только слепые `/about`
- address canonicalization в eval больше не ломает `P./Q./TP.` и не занижает `address exact`
- добавлен machine-checkable gate `scripts/verify_supplier_parsing_quality.sh`
- report теперь отдаёт:
  - `failed_samples`
  - `failed_samples_by_class`
  - `company_site_breakdown`
  - `browser_used`
  - `expected_fields` vs `extracted_fields`
  - `evidence_path`

## Что всё ещё неидеально

Это уже не wave1 acceptance blocker, но это ещё не “идеальный parser”:

- `category/capabilities` extraction всё ещё слабее contact extraction
- остаются live truth ambiguity samples:
  - `site-in-tem-nhan-thang-loi-long-cong-ty-tnhh-san-xuat-thuong-mai-thang-loi-long`
  - `site-in-an-binh-duong-cong-ty-tnhh-design-akay`
- `site-in-an-hpdc-cong-ty-trach-nhiem-huu-han-hpdc` проходит contact gate, но capability/category там ещё не доказаны качественно

## Практический вывод

- для первой волны supplier acquisition во Вьетнаме parsing contour теперь можно использовать
- но использовать его нужно как `wave1 acquisition-ready contour`, а не как доказанно полный supplier intelligence final-state
- operator review всё ещё нужен для:
  - `category/capabilities`
  - единичных ambiguous company-site truths
