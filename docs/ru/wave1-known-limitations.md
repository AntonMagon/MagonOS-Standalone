# Известные ограничения после wave1

Этот список фиксирует не баги, а сознательно оставленные границы первой волны.

## Supplier contour

- Есть управляемый ingest/failure/retry contour, но нет полного supplier portal.
- Dedup остаётся explainable и manual-first: спорные кейсы не автомержатся.
- Нет широкого покрытия всех стран, каналов и внешних supplier источников.

## Storefront / intake

- Публичный вход ограничен wave1-витриной и manual-first draft/request contour.
- Нет полноценного customer portal с отдельными профилями, историей кабинета и self-service управлением всеми сущностями.
- Anti-bot слой intentionally lightweight.

## Commercial flow

- `Request / Offer / Order` закрывают основную коммерческую цепочку, но не заменяют полный ERP-контур.
- `Order` остаётся thin orchestration layer, а не full-scale order management / MES / WMS.
- Денежный слой intentionally limited до внутреннего payment skeleton, без полноценного payment-core и эквайринга.

## Files / documents

- Есть версии, review/finalize, archive и role visibility, но нет полного DMS.
- Нет тяжёлого предпечатного automation contour, OCR-пайплайна или production-grade visual diff.
- Нет отдельного универсального archive UI/API для всех сущностей системы.

## Rules / notifications / escalations

- RulesEngine покрывает explainable guards и critical checks, но не является тяжёлым BPM/rules platform.
- Notification delivery ограничен DB-backed inbox contour без обязательных email/webhook/chat channels.
- Escalation contour ограничен hints и dashboard buckets без внешнего scheduler/pager orchestration.

## Runtime / operations

- `maintenance` и `emergency` режимы coarse-grained и не реализуют сложную degradation matrix.
- Секреты и конфигурация остаются env-driven; внешний secret manager не является обязательной частью wave1.
- Async contour intentionally narrow: supplier ingest retries есть, но отдельная orchestration platform не строилась.

## Сознательно отложено за post-wave-1

- полный supplier portal
- full payment-core
- склад / локальные остатки
- MES / production planning
- heavy AI contour
- mandatory vector DB
- full-country / full-channel expansion
