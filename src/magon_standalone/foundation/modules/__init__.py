# RU: Файл входит в проверенный контур первой волны.
from .audit_dashboards import router as audit_dashboards_router
from .catalog import router as catalog_router
from .comms import router as comms_router
from .companies import router as companies_router
from .documents import router as documents_router
from .drafts_requests import router as drafts_requests_router
from .files_media import router as files_media_router
from .offers import router as offers_router
from .orders import router as orders_router
from .rules_engine import router as rules_engine_router
from .suppliers import router as suppliers_router
from .users_access import router as users_access_router

MODULE_ROUTERS = [
    users_access_router,
    companies_router,
    suppliers_router,
    catalog_router,
    drafts_requests_router,
    offers_router,
    orders_router,
    files_media_router,
    documents_router,
    comms_router,
    rules_engine_router,
    audit_dashboards_router,
]
