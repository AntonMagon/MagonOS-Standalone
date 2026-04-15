"""Minimal standalone HTTP API for supplier-intelligence with simple HTML inspection pages."""
from __future__ import annotations

import html
import json
import logging
import threading
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, make_server

from .contracts import validate_feedback_event
from .runtime import run_standalone_pipeline
from .sqlite_persistence import SqliteSupplierIntelligenceStore

LOGGER = logging.getLogger(__name__)


class SupplierIntelligenceApiService:
    def __init__(self, db_path: str | Path, default_query: str = "printing packaging vietnam", default_country: str = "VN", integration_token: str | None = None):
        self.db_path = Path(db_path)
        self.default_query = default_query
        self.default_country = default_country
        self.integration_token = integration_token

    def health(self) -> dict[str, object]:
        return {"status": "ok", "service": "magon-standalone", "db_path": str(self.db_path.resolve())}

    def status(self) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        return {**self.health(), "storage_counts": store.snapshot_counts()}

    def list_raw_records(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_raw_records(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_companies(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_companies(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_scores(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_scores(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_dedup_decisions(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_dedup_decisions(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_review_queue(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_review_queue(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_feedback_events(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_feedback_events(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_feedback_status(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        items = store.list_feedback_status(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def get_feedback_status(self, source_key: str) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        item = store.get_feedback_status(source_key)
        if item is None:
            raise LookupError(source_key)
        return {"item": item}

    def ingest_feedback_events(self, events: list[dict[str, Any]]) -> dict[str, object]:
        store = SqliteSupplierIntelligenceStore(self.db_path)
        applied = store.save_feedback_events([_feedback_event_from_json(item) for item in events])
        return {"accepted": applied, "received": len(events), "status": "ok"}

    def run_pipeline(self, query: str | None = None, country: str | None = None, fixture: str | None = None) -> dict[str, object]:
        return run_standalone_pipeline(db_path=self.db_path, query=query or self.default_query, country=country or self.default_country, fixture_path=fixture)


def create_wsgi_app(service: SupplierIntelligenceApiService) -> Callable:
    def app(environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "")
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=False)
        try:
            if method == "GET" and path == "/":
                return _html_response(start_response, 200, _home_page(service))
            if method == "GET" and path == "/health":
                return _json_response(start_response, 200, service.health())
            if method == "GET" and path == "/status":
                return _json_response(start_response, 200, service.status())
            if method == "GET" and path == "/raw-records":
                return _json_response(start_response, 200, service.list_raw_records(**_pagination(query)))
            if method == "GET" and path == "/companies":
                return _json_response(start_response, 200, service.list_companies(**_pagination(query)))
            if method == "GET" and path == "/scores":
                return _json_response(start_response, 200, service.list_scores(**_pagination(query)))
            if method == "GET" and path == "/dedup-decisions":
                return _json_response(start_response, 200, service.list_dedup_decisions(**_pagination(query)))
            if method == "GET" and path == "/review-queue":
                return _json_response(start_response, 200, service.list_review_queue(**_pagination(query)))
            if method == "GET" and path == "/feedback-events":
                return _json_response(start_response, 200, service.list_feedback_events(**_pagination(query)))
            if method == "GET" and path == "/feedback-status":
                return _json_response(start_response, 200, service.list_feedback_status(**_pagination(query)))
            if method == "GET" and path.startswith("/feedback-status/"):
                source_key = path.removeprefix("/feedback-status/").strip()
                if not source_key:
                    raise ValueError("feedback_status_source_key_required")
                return _json_response(start_response, 200, service.get_feedback_status(source_key))
            if method == "GET" and path == "/ui/raw-records":
                return _html_response(start_response, 200, _table_page("Raw records", service.list_raw_records(limit=200)["items"]))
            if method == "GET" and path == "/ui/companies":
                return _html_response(start_response, 200, _table_page("Canonical companies", service.list_companies(limit=200)["items"]))
            if method == "GET" and path == "/ui/scores":
                return _html_response(start_response, 200, _table_page("Scores", service.list_scores(limit=200)["items"]))
            if method == "GET" and path == "/ui/review-queue":
                return _html_response(start_response, 200, _table_page("Review queue", service.list_review_queue(limit=200)["items"]))
            if method == "GET" and path == "/ui/feedback-status":
                return _html_response(start_response, 200, _table_page("Feedback status", service.list_feedback_status(limit=200)["items"]))
            if method == "POST" and path == "/runs":
                body = _parse_json_body(environ)
                return _json_response(start_response, 200, service.run_pipeline(query=body.get("query"), country=body.get("country"), fixture=body.get("fixture")))
            if method == "POST" and path == "/feedback-events":
                if not _token_allowed(environ, service.integration_token):
                    return _json_response(start_response, 403, {"error": "forbidden"})
                body = _parse_json_body(environ)
                events = body.get("events")
                if not isinstance(events, list):
                    raise ValueError("events_must_be_list")
                return _json_response(start_response, 200, service.ingest_feedback_events(events))
            if path in {"/runs", "/feedback-events", "/feedback-status"} or path.startswith("/feedback-status/"):
                return _json_response(start_response, 405, {"error": "method_not_allowed"})
            return _json_response(start_response, 404, {"error": "not_found", "path": path})
        except ValueError as exc:
            return _json_response(start_response, 400, {"error": "bad_request", "detail": str(exc)})
        except LookupError as exc:
            return _json_response(start_response, 404, {"error": "not_found", "detail": str(exc)})
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("magon_standalone.request_failed path=%s", path)
            return _json_response(start_response, 500, {"error": "internal_error", "detail": str(exc)})

    return app


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("magon_standalone.http " + format, *args)


class SupplierIntelligenceApiServer:
    def __init__(self, service: SupplierIntelligenceApiService, host: str = "127.0.0.1", port: int = 8091):
        self.service = service
        self.host = host
        self.port = port
        self._server = make_server(host, port, create_wsgi_app(service), handler_class=QuietRequestHandler)
        self.port = int(self._server.server_port)
        self.base_url = f"http://{self.host}:{self.port}"

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def start_in_thread(self) -> threading.Thread:
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return thread


def _home_page(service: SupplierIntelligenceApiService) -> str:
    status = service.status()["storage_counts"]
    body = [
        "<h1>MagonOS Standalone</h1>",
        "<p>Standalone supplier-intelligence runtime without Odoo.</p>",
        "<ul>",
        '<li><a href="/ui/raw-records">Raw records</a></li>',
        '<li><a href="/ui/companies">Canonical companies</a></li>',
        '<li><a href="/ui/scores">Scores</a></li>',
        '<li><a href="/ui/review-queue">Review queue</a></li>',
        '<li><a href="/ui/feedback-status">Feedback status</a></li>',
        '<li><a href="/health">Health JSON</a></li>',
        '<li><a href="/status">Status JSON</a></li>',
        "</ul>",
        "<h2>Storage counts</h2>",
        _table(status),
    ]
    return _page("MagonOS Standalone", "".join(body))


def _table_page(title: str, items: list[dict[str, Any]]) -> str:
    return _page(title, f"<h1>{html.escape(title)}</h1>" + _table(items))


def _table(data: Any) -> str:
    if isinstance(data, dict):
        rows = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v))}</td></tr>" for k, v in data.items())
        return f"<table><tbody>{rows}</tbody></table>"
    if not data:
        return "<p>No data.</p>"
    keys = sorted({key for item in data for key in item.keys()})
    head = "".join(f"<th>{html.escape(str(k))}</th>" for k in keys)
    rows = []
    for item in data:
        cells = "".join(f"<td>{html.escape(_cell_value(item.get(k)))}</td>" for k in keys)
        rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _cell_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return "" if value is None else str(value)


def _page(title: str, body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
        + html.escape(title)
        + "</title><style>body{font-family:system-ui,sans-serif;max-width:1280px;margin:40px auto;padding:0 16px;}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #ddd;padding:8px;vertical-align:top;text-align:left}th{background:#f4f4f4}code{background:#f4f4f4;padding:2px 4px}</style></head><body>"
        + body
        + "</body></html>"
    )


def _pagination(query: dict[str, list[str]]) -> dict[str, int]:
    return {"limit": max(1, min(int(query.get("limit", ["100"])[0]), 500)), "offset": max(0, int(query.get("offset", ["0"])[0]))}


def _parse_json_body(environ: dict[str, Any]) -> dict[str, Any]:
    try:
        length = int(environ.get("CONTENT_LENGTH", "0") or "0")
    except ValueError as exc:
        raise ValueError("invalid_content_length") from exc
    raw_body = environ["wsgi.input"].read(length) if length else b"{}"
    if not raw_body:
        return {}
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_json_body") from exc
    if not isinstance(payload, dict):
        raise ValueError("json_body_must_be_object")
    return payload


def _feedback_event_from_json(payload: dict[str, Any]):
    from .contracts import FeedbackEventPayload

    if not isinstance(payload, dict):
        raise ValueError("feedback_event_must_be_object")
    event = FeedbackEventPayload(
        event_id=str(payload["event_id"]),
        source_key=str(payload["source_key"]),
        source_system="odoo",
        event_type=str(payload["event_type"]),
        event_version=str(payload["event_version"]),
        occurred_at=str(payload["occurred_at"]),
        payload_hash=str(payload["payload_hash"]),
        company_id=_optional_int(payload.get("company_id")),
        vendor_profile_id=_optional_int(payload.get("vendor_profile_id")),
        qualification_decision_id=_optional_int(payload.get("qualification_decision_id")),
        partner_id=_optional_int(payload.get("partner_id")),
        crm_lead_id=_optional_int(payload.get("crm_lead_id")),
        lead_mapping_id=_optional_int(payload.get("lead_mapping_id")),
        routing_outcome=_optional_str(payload.get("routing_outcome")),
        manual_review_status=_optional_str(payload.get("manual_review_status")),
        qualification_status=_optional_str(payload.get("qualification_status")),
        lead_status=_optional_str(payload.get("lead_status")),
        partner_linked=bool(payload.get("partner_linked")),
        crm_linked=bool(payload.get("crm_linked")),
        reason_code=_optional_str(payload.get("reason_code")),
        notes=_optional_str(payload.get("notes")),
        is_manual_override=bool(payload.get("is_manual_override")),
        payload=payload.get("payload") or {},
    )
    return validate_feedback_event(event)


def _token_allowed(environ: dict[str, Any], expected_token: str | None) -> bool:
    if not expected_token:
        return True
    return environ.get("HTTP_X_INTEGRATION_TOKEN") == expected_token


def _optional_int(value: Any) -> int | None:
    return None if value in {None, "", False} else int(value)


def _optional_str(value: Any) -> str | None:
    if value in {None, "", False}:
        return None
    return str(value)


def _json_response(start_response: Callable, status_code: int, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    start_response(f"{status_code} {_reason_phrase(status_code)}", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def _html_response(start_response: Callable, status_code: int, body: str) -> list[bytes]:
    data = body.encode("utf-8")
    start_response(f"{status_code} {_reason_phrase(status_code)}", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))])
    return [data]


def _reason_phrase(status_code: int) -> str:
    return {200: "OK", 400: "Bad Request", 403: "Forbidden", 404: "Not Found", 405: "Method Not Allowed", 500: "Internal Server Error"}.get(status_code, "OK")
