"""Standalone HTTP API and local operator panel for supplier-intelligence."""
from __future__ import annotations

import html
import json
import logging
import re
import threading
from contextvars import ContextVar
from dataclasses import asdict
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote, unquote
from wsgiref.simple_server import WSGIRequestHandler, make_server

from magon_standalone.observability import wrap_wsgi_app

from .contracts import (
    LaborPolicyInput,
    LaborRateInput,
    ShiftCapacityInput,
    WorkforceEstimateInput,
    WorkforceRoleDemand,
    validate_feedback_event,
)
from .operations_service import SupplierOperationsService
from .runtime import run_standalone_pipeline
from .sqlite_persistence import SqliteSupplierIntelligenceStore
from .workforce_estimation_service import WorkforceEstimationEngine

LOGGER = logging.getLogger(__name__)
DEFAULT_UI_FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "vn_suppliers_raw.json"
DEFAULT_WORKFORCE_FIXTURE = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "workforce_cases_vn.json"
LOCALE_COOKIE_NAME = "magonos-locale"
DEFAULT_UI_LOCALE = "ru"
SUPPORTED_UI_LOCALES = {"ru", "en"}
_REQUEST_LOCALE: ContextVar[str] = ContextVar("magonos_ui_locale", default=DEFAULT_UI_LOCALE)
_HTML_TEXT_RE = re.compile(r"(^|>)([^<>]+)(?=<|$)", re.S)
_HTML_ATTR_RE = re.compile(r'(?P<name>placeholder|aria-label|title)="(?P<value>[^"]+)"')

_UI_TEXT_RU = {
    "Dashboard": "Панель",
    "Companies": "Компании",
    "Commercial": "Коммерция",
    "Quotes": "Котировки",
    "Handoffs": "Передачи",
    "Production": "Производство",
    "Workforce": "Персонал",
    "Review queue": "Очередь проверки",
    "Feedback status": "Статус обратной связи",
    "Feedback": "Обратная связь",
    "Feedback audit": "Аудит обратной связи",
    "Raw records": "Исходные данные",
    "Scores": "Оценки",
    "Interface language": "Язык интерфейса",
    "Standalone operator panel": "Внутренняя автономная панель",
    "Supplier intelligence console": "Консоль данных о поставщиках",
    "Use the company workbench as the main operator surface. Standalone intelligence stays authoritative. Downstream commercial/Odoo-derived outcomes are shown separately as feedback.": "Используй карточку компании как основную рабочую поверхность. Данные автономного контура остаются источником истины. Коммерческие исходы и отклики из смежных систем показываются отдельно как внешняя обратная связь.",
    "Local operator actions": "Локальные действия оператора",
    "Fixture path": "Путь к фикстуре",
    "Query": "Запрос",
    "Country": "Страна",
    "Run local fixture pipeline": "Запустить локальный прогон по фикстуре",
    "Seed narrow synthetic downstream feedback so the company workbench and feedback screens are inspectable without external integrations.": "Подгрузи тестовую внешнюю обратную связь, чтобы карточку компании и экраны обратной связи можно было проверить без внешних интеграций.",
    "Load sample feedback": "Загрузить тестовую обратную связь",
    "Recent companies": "Недавние компании",
    "Recent downstream feedback": "Недавняя внешняя обратная связь",
    "Synthetic sample feedback is present": "В системе есть тестовая обратная связь",
    "These rows are local test data seeded from the operator panel. They are clearly labeled and separate from standalone intelligence.": "Эти строки являются локальными тестовыми данными, загруженными из панели оператора. Они явно помечены и отделены от основного слоя данных.",
    "Quick navigation": "Быстрая навигация",
    "Open timeline": "Открыть историю",
    "Company": "Компания",
    "City": "Город",
    "Score": "Оценка",
    "Queue": "Очередь",
    "Feedback events": "События обратной связи",
    "Companies with feedback": "Компании с обратной связью",
    "Routing feedback": "Отклики по маршрутизации",
    "Synthetic feedback": "Тестовая обратная связь",
    "Raw records": "Исходные данные",
    "Canonical companies": "Канонические компании",
    "Scored companies": "Оценённые компании",
    "No companies yet.": "Компаний пока нет.",
    "No feedback events yet.": "Событий обратной связи пока нет.",
    "No queue": "Очереди нет",
    "No feedback": "Обратная связь отсутствует",
    "Synthetic sample": "Тестовая синтетика",
    "Companies": "Компании",
    "Canonical supplier intelligence": "Канонический реестр поставщиков",
    "Browse standalone-owned supplier/company intelligence with score, queue, and feedback context.": "Просматривай данные о поставщике и компании вместе с оценкой, очередью и контекстом обратной связи.",
    "matching companies": "подходящих компаний",
    "Search company, site, contact, capability": "Поиск по компании, сайту, контакту или направлению",
    "All cities": "Все города",
    "All capabilities": "Все направления",
    "All feedback states": "Все состояния обратной связи",
    "Has feedback": "Есть обратная связь",
    "No feedback": "Нет обратной связи",
    "25 rows": "25 строк",
    "50 rows": "50 строк",
    "100 rows": "100 строк",
    "Apply": "Применить",
    "Capabilities": "Направления",
    "Contact": "Контакт",
    "Website": "Сайт",
    "No companies match the current filters.": "Нет компаний, подходящих под текущие фильтры.",
    "Company workbench": "Карточка компании",
    "This is the main operator surface for one company. Standalone intelligence, downstream feedback, raw evidence, scores, and review state are kept together here.": "Это основная рабочая поверхность по одной компании. Здесь собраны канонические данные, внешняя обратная связь, исходные материалы, оценки и текущее состояние проверки.",
    "Back to companies": "Назад к компаниям",
    "Open feedback timeline": "Открыть историю обратной связи",
    "Open feedback audit": "Открыть аудит обратной связи",
    "Open workforce planner": "Открыть планирование персонала",
    "Open opportunity list": "Открыть список сделок",
    "Jump to raw evidence": "Перейти к исходным данным",
    "Company overview": "Обзор компании",
    "Canonical company card for quick operator inspection.": "Каноническая карточка компании для быстрой операторской проверки.",
    "Standalone intelligence": "Данные автономного контура",
    "Standalone-owned normalized/canonical intelligence. Downstream feedback never overwrites this block.": "Нормализованные и канонические данные автономного контура. Внешняя обратная связь никогда не переписывает этот блок.",
    "Scores": "Оценки",
    "Standalone workflow": "Автономный рабочий процесс",
    "This is the migrated business workflow state that used to sit in Odoo vendor profile and qualification objects.": "Это перенесённое состояние бизнес-процесса, которое раньше хранилось в профиле поставщика и объектах квалификации в Odoo.",
    "Operator decision": "Решение оператора",
    "Outcome": "Исход",
    "Reason code": "Код причины",
    "Notes": "Заметки",
    "Apply standalone decision": "Применить решение",
    "Standalone commercial state": "Коммерческое состояние",
    "Editable commercial follow-up owned by standalone. This is where manual sales progress lives now, not in downstream feedback snapshots.": "Редактируемое коммерческое сопровождение, принадлежащее автономному контуру. Именно здесь теперь живёт ручной прогресс продаж, а не во внешних снимках состояния.",
    "Commercial action": "Коммерческое действие",
    "Manual-first update form for customer/opportunity progress.": "Прямая форма для ручного обновления прогресса по клиенту и сделке.",
    "Customer account": "Карточка клиента",
    "Minimum standalone customer/account owner for this commercial contour. This is not a res.partner clone.": "Это минимальная карточка клиента для текущего коммерческого контура. Она не копирует `res.partner`.",
    "Save customer account": "Сохранить клиентский аккаунт",
    "Standalone-owned customer identity used by opportunities and quote workbench.": "Эта карточка клиента используется в сделках и заявках на расчёт.",
    "Opportunities": "Сделки",
    "Standalone lead/opportunity ownership for the active contour.": "Собственный слой сделок для активного коммерческого контура.",
    "Open list": "Открыть список",
    "Create opportunity": "Создать сделку",
    "Capture the commercial owner record here instead of depending on Odoo CRM lead ownership.": "Фиксируй здесь сделку и коммерческого владельца вместо зависимости от состояния лида в Odoo CRM.",
    "Quote intents": "Заявки на расчёт",
    "Standalone-owned RFQ / quote-intent records. This is the first minimal replacement for Odoo quote handoff.": "Записи по запросам на расчёт принадлежат автономному контуру. Это первая минимальная замена старой Odoo-логики расчёта.",
    "Create quote intent": "Создать заявку на расчёт",
    "Capture the request so the operator path can continue inside standalone.": "Зафиксируй запрос, чтобы операторский маршрут продолжался внутри автономного контура.",
    "Production handoffs": "Передачи в производство",
    "Manual-first handoff into execution. This replaces jumping straight from quote status into ERP-shaped order objects.": "Ручная передача в исполнение. Она заменяет прямой переход из статуса расчёта в ERP-подобные объекты заказа.",
    "Create production handoff": "Создать передачу в производство",
    "Create a lightweight execution handoff without pulling in full ERP order logic.": "Создай лёгкую передачу в исполнение без втягивания полной ERP-логики заказа.",
    "Qualification decisions": "Решения по квалификации",
    "Standalone decision ledger for this supplier workflow.": "Журнал решений по этому процессу работы с поставщиком.",
    "Downstream feedback": "Внешняя обратная связь",
    "Projection derived from the feedback ledger. This remains separate from standalone intelligence.": "Сводка, построенная по журналу обратной связи. Она остаётся отдельной от основного слоя данных.",
    "Feedback timeline": "История обратной связи",
    "Recent downstream events relevant to this company.": "Недавние внешние события, относящиеся к этой компании.",
    "Commercial audit": "Коммерческий аудит",
    "Append-only audit for customer account, opportunity, quote, and handoff state changes in standalone.": "Неперезаписываемый журнал изменений по клиентским карточкам, сделкам, расчётам и передачам внутри автономного контура.",
    "Routing audit": "Аудит маршрутизации",
    "Audit trail of standalone queue transitions and routing decisions.": "Журнал переходов очереди и решений маршрутизации внутри автономного контура.",
    "Raw/source evidence": "Исходные данные",
    "Compact raw evidence summary. Open the raw record detail page when you need payload-level inspection.": "Краткая сводка исходных данных. Открывай карточку записи, когда нужно проверить исходный ответ целиком.",
    "No score stored yet for this company.": "Для этой компании пока нет сохранённой оценки.",
    "No standalone quote intents yet.": "Заявок на расчёт пока нет.",
    "No production handoffs yet.": "Передач в производство пока нет.",
    "No standalone commercial audit yet.": "Коммерческого аудита пока нет.",
    "No review queue entries for this company.": "Для этой компании пока нет записей в очереди проверки.",
    "No standalone qualification decisions yet.": "Решений по квалификации пока нет.",
    "No standalone routing audit yet.": "Аудита маршрутизации пока нет.",
    "No downstream feedback projection yet. Standalone intelligence is still present, but no downstream commercial/routing outcome has been ingested.": "Сводки по внешней обратной связи пока нет. Основные данные уже есть, но внешние коммерческие и маршрутные исходы ещё не были загружены.",
    "No related feedback events yet.": "Связанных событий обратной связи пока нет.",
    "No correlated raw/source evidence found for this company.": "Связанных исходных данных для этой компании не найдено.",
    "Workforce planner": "Планировщик персонала",
    "Standalone labor estimation": "Оценка трудозатрат",
    "Use the pure workforce engine to estimate labor hours, headcount, overtime, and cost. This tool does not mutate company intelligence or downstream feedback.": "Используй отдельный расчётный модуль для оценки трудочасов, численности, переработок и стоимости. Этот инструмент не меняет данные о компаниях и внешнюю обратную связь.",
    "Back to dashboard": "Назад к панели",
    "Company context": "Контекст компании",
    "Optional. This only anchors the estimate to a company workbench for operator navigation.": "Необязательно. Это лишь привязывает оценку к карточке компании для операторской навигации.",
    "Sample scenarios": "Тестовые сценарии",
    "Choose sample case": "Выбрать сценарий",
    "Load scenario": "Загрузить сценарий",
    "Scenario fixture: ": "Фикстура сценария: ",
    "Estimate input": "Вход оценки",
    "Edit the structured payload directly when you need a custom estimate. This is an explicit standalone planning tool, not hidden workflow state.": "Редактируй структурированные входные данные напрямую, когда нужна нестандартная оценка. Это отдельный планировочный инструмент, а не скрытое состояние процесса.",
    "Structured estimate payload": "Структурированные входные данные для расчёта",
    "Run workforce estimate": "Запустить оценку персонала",
    "Estimate summary": "Сводка оценки",
    "Role breakdown": "Разбивка по ролям",
    "Assumptions and gaps": "Допущения и пробелы",
    "No workforce estimate yet.": "Оценки персонала пока нет.",
    "No role breakdown yet.": "Разбивки по ролям пока нет.",
    "No assumptions yet.": "Допущений пока нет.",
    "Missing skills:": "Недостающие навыки:",
    "No assumptions recorded.": "Допущения не записаны.",
    "Commercial pipeline": "Коммерческая воронка",
    "Standalone commercial follow-up": "Коммерческое сопровождение",
    "Manual-first commercial state owned by standalone. This replaces hiding active sales progress inside Odoo-only lead state.": "Коммерческое состояние, принадлежащее автономному контуру. Оно заменяет практику прятать активный прогресс продаж внутри Odoo.",
    "commercial records": "коммерческих записей",
    "All customer states": "Все состояния клиента",
    "All stages": "Все стадии",
    "Customer status": "Статус клиента",
    "Commercial stage": "Коммерческая стадия",
    "Due": "Срок",
    "Downstream feedback": "Внешняя обратная связь",
    "No standalone commercial records yet.": "Коммерческих записей пока нет.",
    "Standalone commercial opportunities": "Коммерческие сделки",
    "Minimal lead/opportunity ownership for the active contour. This is not a generic CRM suite.": "Минимальный слой ведения сделок для активного контура. Это не универсальная CRM-система.",
    "opportunities": "возможностей",
    "All statuses": "Все статусы",
    "Account": "Аккаунт",
    "Source": "Источник",
    "Value": "Сумма",
    "Next action": "Следующее действие",
    "No opportunities yet.": "Возможностей пока нет.",
    "Standalone RFQ / quote intake": "Приём заявок на расчёт",
    "Manual-first quote requests captured inside standalone, instead of disappearing into Odoo-only order scaffolding.": "Запросы на расчёт фиксируются внутри автономного контура и не исчезают в Odoo-шаблонах заказов.",
    "quote intents": "заявок на расчёт",
    "All quote types": "Все типы котировок",
    "Type": "Тип",
    "RFQ ref": "Номер запроса",
    "Quantity": "Количество",
    "Target due": "Целевой срок",
    "Quote ref / Amount": "Номер котировки / Сумма",
    "Quote": "Расчёт",
    "Amount": "Сумма",
    "No quote intents yet.": "Заявок на расчёт пока нет.",
    "Opportunity workbench": "Карточка сделки",
    "Standalone-owned opportunity state for the active contour. This is the minimum replacement for Odoo lead ownership.": "Состояние сделки в автономном контуре. Это минимальная замена зависимости от владения лидом в Odoo.",
    "Back to opportunities": "Назад к сделкам",
    "Linked quote intents": "Связанные заявки на расчёт",
    "Opportunity summary": "Сводка сделки",
    "Update opportunity": "Обновить сделку",
    "Title": "Название",
    "Status": "Статус",
    "No linked account": "Связанного аккаунта нет",
    "Primary account": "Основной аккаунт",
    "Source channel": "Канал источника",
    "Estimated value": "Оценочная сумма",
    "Currency": "Валюта",
    "Currency code": "Код валюты",
    "Target due date": "Целевая дата",
    "External opportunity ref": "Внешний код сделки",
    "Trace Odoo lead ref": "Связь с лидом Odoo",
    "Save opportunity": "Сохранить сделку",
    "No quote intents linked to this opportunity yet.": "К этой сделке пока не привязаны заявки на расчёт.",
    "Production handoffs": "Передачи в производство",
    "Standalone execution handoff": "Передача в производство",
    "Minimal handoff from quote/commercial state into production execution. This avoids forcing everything into ERP orders too early.": "Минимальная передача из состояния расчёта и коммерческой работы в производственное исполнение. Это позволяет не тащить всё слишком рано в ERP-заказы.",
    "Open production board": "Открыть доску производства",
    "handoff records": "записей передачи",
    "Production ref": "Производственный код",
    "Ship date": "Дата отгрузки",
    "Specification": "Спецификация",
    "No production handoffs yet.": "Передач в производство пока нет.",
    "Ready for production": "Готово к производству",
    "Scheduled": "Запланировано",
    "In progress": "В работе",
    "Blocked": "Заблокировано",
    "Completed": "Завершено",
    "No quote link": "Связи с котировкой нет",
    "No opportunity": "Сделка отсутствует",
    "No quote": "Котировки нет",
    "Move to": "Переместить в",
    "Update status": "Обновить статус",
    "No handoffs in this column.": "В этой колонке нет передач.",
    "Production board": "Доска производства",
    "Standalone execution board": "Доска исполнения",
    "Operator-first production board built on top of standalone handoff records. This is the minimal replacement for hiding execution state inside ERP-shaped order objects.": "Операторская доска производства, построенная поверх записей передачи в производство. Это минимальная замена скрытию исполнения внутри ERP-объектов.",
    "Open handoff list": "Открыть список передач",
    "total handoffs": "всего передач",
    "Quote workbench": "Карточка расчёта",
    "Standalone-owned quote workflow. This is where manual pricing progress should live instead of disappearing into ERP-shaped objects too early.": "Именно здесь должен жить ручной процесс расчёта, а не исчезать слишком рано внутри ERP-подобных объектов.",
    "Back to quote intents": "Назад к заявкам на расчёт",
    "No company mapping found for this quote intent.": "Для этой заявки на расчёт не найдено соответствие компании.",
    "Canonical company": "Каноническая компания",
    "Commercial context": "Коммерческий контекст",
    "Ownership": "Владение",
    "Standalone": "Автономный контур",
    "Commercial summary": "Коммерческая сводка",
    "Quote summary": "Сводка котировки",
    "Quote reference": "Номер котировки",
    "Quoted amount": "Сумма котировки",
    "Pricing notes": "Комментарии к расчёту",
    "Save quote workflow": "Сохранить расчёт",
    "Handoff status": "Статус передачи",
    "Production reference": "Производственный код",
    "Requested ship date": "Запрошенная дата отгрузки",
    "Specification summary": "Сводка спецификации",
    "Production handoff": "Передача в производство",
    "Standalone-owned execution handoff. This is the bridge between quote state and actual production follow-through.": "Передача в производство в автономном контуре. Это мост между состоянием расчёта и фактическим ведением производства.",
    "Back to production handoffs": "Назад к передачам в производство",
    "Back to quote workbench": "Назад к карточке котировки",
    "Back to opportunity": "Назад к сделке",
    "Quote context": "Контекст котировки",
    "Opportunity context": "Контекст сделки",
    "Handoff summary": "Сводка передачи",
    "Update handoff": "Обновить передачу",
    "Save production handoff": "Сохранить передачу в производство",
    "Feedback projection": "Сводка обратной связи",
    "Downstream outcome view": "Обзор внешних исходов",
    "Projection derived from the feedback ledger. It is readable for operators and stays separate from canonical intelligence.": "Сводка, построенная по журналу обратной связи. Она удобна для оператора и остаётся отдельной от канонических данных.",
    "projection rows": "строк проекции",
    "Search source key or company": "Поиск по ключу источника или компании",
    "All states": "Все состояния",
    "Has routing": "Есть маршрутизация",
    "Has qualification": "Есть квалификация",
    "Has commercial": "Есть коммерческий исход",
    "Has linkage": "Есть связка",
    "Manual override": "Ручное переопределение",
    "Company / source": "Компания / источник",
    "Outcome summary": "Сводка исходов",
    "Partner": "Партнёр",
    "Commercial": "Коммерция",
    "Last event": "Последнее событие",
    "Reason": "Причина",
    "No feedback projection rows match the current filters.": "Под текущие фильтры не подходит ни одна строка сводки обратной связи.",
    "Feedback detail": "Детали обратной связи",
    "This is the downstream feedback projection and its audit trail. It remains separate from canonical intelligence.": "Здесь показана сводка внешней обратной связи и её журнал изменений. Она остаётся отдельной от канонических данных.",
    "Current projection": "Текущая проекция",
    "Related canonical company": "Связанная каноническая компания",
    "Feedback ledger for this source": "Журнал обратной связи по этому источнику",
    "No canonical company currently matches this feedback source key.": "Сейчас ни одна каноническая компания не соответствует этому ключу источника.",
    "Source key": "Ключ источника",
    "Routing": "Маршрутизация",
    "Manual review": "Ручная проверка",
    "Qualification": "Квалификация",
    "Partner linkage": "Связка с партнёром",
    "CRM linkage": "Связка с CRM",
    "Routing note": "Заметка по маршрутизации",
    "Qualification note": "Заметка по квалификации",
    "Commercial note": "Коммерческая заметка",
    "No feedback events yet for this source key.": "Для этого ключа источника пока нет событий обратной связи.",
    "Occurred": "Когда",
    "Event": "Событие",
    "Event ID": "ID события",
    "Feedback event ledger": "Журнал событий обратной связи",
    "Audit-level view of the downstream feedback ledger. Synthetic/sample rows are explicitly labeled.": "Аудитный вид журнала внешней обратной связи. Тестовые строки помечены отдельно.",
    "matching events": "подходящих событий",
    "Search event id, source key, company, reason": "Поиск по ID события, ключу источника, компании или причине",
    "All event types": "Все типы событий",
    "Routing": "Маршрутизация",
    "Partner linkage": "Связка с партнёром",
    "Commercial disposition": "Коммерческий исход",
    "Action": "Действие",
    "Open company": "Открыть компанию",
    "No feedback events match the current filters.": "Под текущие фильтры не подходит ни одно событие обратной связи.",
    "Raw record detail": "Детали исходной записи",
    "Source evidence": "Исходные данные",
    "Inspect the raw discovery row and jump directly back into the related company workbench when correlation exists.": "Проверь исходную запись и вернись прямо в связанную карточку компании, если связь уже установлена.",
    "Back to raw records": "Назад к исходным данным",
    "This raw record is not currently correlated to a canonical company.": "Эта исходная запись сейчас не связана с канонической компанией.",
    "Raw record metadata": "Метаданные исходной записи",
    "Canonical correlation": "Каноническая корреляция",
    "List fields": "Списковые поля",
    "Raw payload": "Исходный ответ",
    "Raw name": "Название в источнике",
    "Source type": "Тип источника",
    "Source domain": "Домен источника",
    "Scenario key": "Ключ сценария",
    "Fetch status": "Статус получения",
    "Source URL": "URL источника",
    "Candidate dedup fingerprint": "Кандидатный отпечаток дедупликации",
    "No queue items yet.": "Элементов в очереди пока нет.",
    "Operator review workload": "Нагрузка по ручной проверке",
    "Everything currently queued for manual attention, with direct links back into the company workbench.": "Всё, что сейчас стоит в очереди на ручное внимание, с прямыми ссылками назад в карточку компании.",
    "queue rows": "строк очереди",
    "Priority": "Приоритет",
    "Why in review": "Причина попадания в проверку",
    "Missing company": "Компания отсутствует",
    "Source-side discovery view": "Обзор исходных данных",
    "Inspect raw discovery rows and move directly back into the related company workbench.": "Проверяй исходные записи и сразу возвращайся в связанную карточку компании.",
    "raw rows": "сырых строк",
    "Raw record": "Исходная запись",
    "Parser conf.": "Уверенность парсера",
    "Scenario": "Сценарий",
    "Evidence summary": "Краткая сводка данных",
    "No raw records stored yet.": "Исходные записи пока не сохранены.",
    "Standalone scoring output": "Результаты оценки",
    "Readable score breakdowns with direct links into the company workbench.": "Понятная разбивка оценок с прямыми ссылками в карточку компании.",
    "score rows": "строк оценок",
    "Composite": "Итоговая",
    "Relevance": "Релевантность",
    "Capability fit": "Соответствие направлениям",
    "Contactability": "Контактируемость",
    "Trust": "Доверие",
    "No scores yet.": "Оценок пока нет.",
    "Pipeline action": "Действие по запуску",
    "Fixture pipeline run complete": "Прогон по фикстуре завершён",
    "Local operator action only. This executed the standalone supplier-intelligence pipeline against fixture-backed input.": "Это локальное операторское действие. Оно запустило автономный процесс обработки поставщиков на входных данных из фикстуры.",
    "Run report": "Отчёт запуска",
    "Storage counts": "Счётчики хранилища",
    "Next steps: ": "Следующие шаги: ",
    "inspect companies": "посмотреть компании",
    "review queue": "очередь проверки",
    "raw records": "исходные данные",
    "Feedback action": "Действие по обратной связи",
    "Sample feedback loaded": "Тестовая обратная связь загружена",
    "Local-only helper action. It seeds synthetic downstream feedback events so the operator panel is inspectable without waiting on external systems.": "Это локальное служебное действие. Оно загружает тестовые события внешней обратной связи, чтобы операторскую панель можно было проверить без ожидания внешних систем.",
    "Action result": "Результат действия",
    "generated": "сгенерировано",
    "companies_used": "использовано компаний",
    "inspect feedback projection": "проверить сводку обратной связи",
    "audit the feedback ledger": "проверить журнал обратной связи",
    "open companies": "открыть компании",
    "Standalone workflow action": "Действие рабочего процесса",
    "Decision applied": "Решение применено",
    "The standalone operations domain is now the owner of this supplier routing/qualification decision.": "Автономный операционный контур теперь является владельцем этого решения по маршрутизации и квалификации поставщика.",
    "Decision result": "Результат решения",
    "Commercial state saved": "Коммерческое состояние сохранено",
    "This company now has standalone-owned commercial follow-up state. It is editable here and no longer needs to hide behind downstream CRM snapshots.": "У этой компании теперь есть собственное коммерческое состояние. Оно редактируется здесь и больше не должно прятаться за внешними CRM-снимками.",
    "Open commercial pipeline": "Открыть коммерческую воронку",
    "Commercial state": "Коммерческое состояние",
    "Standalone customer account action": "Действие по карточке клиента",
    "Customer account saved": "Клиентский аккаунт сохранён",
    "The active commercial contour now has a standalone-owned customer/account identity instead of relying on Odoo partner ownership.": "Активный коммерческий контур теперь имеет собственную карточку клиента вместо зависимости от партнёра в Odoo.",
    "Open opportunities": "Открыть сделки",
    "Opportunity created": "Сделка создана",
    "Opportunity saved": "Сделка сохранена",
    "Standalone opportunity ownership now exists for this company without depending on Odoo CRM lead state.": "Для этой компании теперь существует собственная сделка без зависимости от состояния в Odoo CRM.",
    "Standalone opportunity ownership is updated here.": "Сделка обновляется здесь.",
    "Open opportunity": "Открыть сделку",
    "Open opportunity list": "Открыть список сделок",
    "Quote workflow saved": "Расчёт сохранён",
    "Quote intent created": "Заявка на расчёт создана",
    "This standalone quote workflow is updated here. It should not need an Odoo quote object just to track pricing progress.": "Процесс расчёта обновляется здесь. Для отслеживания прогресса ему не нужен отдельный объект котировки в Odoo.",
    "This request is now tracked in standalone. It no longer needs to start life as an Odoo-only quote or order artifact.": "Теперь этот запрос отслеживается автономно. Ему больше не нужно начинать жизнь как артефакт котировки или заказа только внутри Odoo.",
    "No company workbench link": "Ссылка на карточку компании отсутствует",
    "Open quote workbench": "Открыть карточку котировки",
    "Open quote intents": "Открыть заявки на расчёт",
    "Quote intent": "Заявка на расчёт",
    "Production handoff saved": "Передача в производство сохранена",
    "Production handoff created": "Передача в производство создана",
    "This execution handoff is updated in standalone. It should not require an ERP order object just to track production readiness.": "Эта передача в производство обновляется внутри автономного контура. Для отслеживания готовности производства ей не нужен отдельный ERP-объект заказа.",
    "This execution handoff is now tracked in standalone. It bridges quote/commercial state into delivery planning without dragging in full ERP flow.": "Эта передача в производство теперь отслеживается автономно. Она связывает расчёт и коммерческое состояние с планированием исполнения без втягивания полного ERP-потока.",
    "Open production handoff": "Открыть передачу в производство",
    "Open production handoffs": "Открыть передачи в производство",
    "Handoff": "Передача",
    "Context": "Контекст",
    "Queue transition applied": "Переход очереди применён",
    "Queue transition": "Переход очереди",
    "Pipeline run": "Запуск обработки",
    "Sample feedback": "Тестовая обратная связь",
    "Manual queue transition is now recorded in standalone routing audit instead of Odoo queue state.": "Ручной переход очереди теперь записывается в аудит маршрутизации автономного контура вместо состояния очереди в Odoo.",
    "Back to review queue": "Назад к очереди проверки",
    "Queue row": "Строка очереди",
    "No data.": "Нет данных.",
    "Partner linked": "Партнёр связан",
    "Routing update": "Обновление маршрутизации",
    "Qualification update": "Обновление квалификации",
    "Partner linkage update": "Обновление связи с партнёром",
    "Commercial update": "Коммерческое обновление",
    "Feedback event": "Событие обратной связи",
    "Time": "Время",
    "Kind": "Тип",
    "Detail": "Детали",
    "No recent activity yet.": "Недавней активности пока нет.",
    "When": "Когда",
    "Entity": "Сущность",
    "From": "Из",
    "To": "В",
    "No commercial audit yet.": "Коммерческого аудита пока нет.",
    "Linked": "Связано",
    "Not linked": "Не связано",
    "No partner": "Партнёра нет",
    "CRM linked": "Есть связь с CRM",
    "No CRM link": "Связи с CRM нет",
    "Review status": "Статус проверки",
    "No capabilities": "Направления не указаны",
    "Canonical name": "Каноническое название",
    "Address": "Адрес",
    "Email": "Электронная почта",
    "Phone": "Телефон",
    "Provenance": "Источники",
    "Freshness": "Актуальность",
    "Overall standalone score.": "Итоговая оценка автономного контура.",
    "Demand / query fit.": "Соответствие спросу и запросу.",
    "Capability coverage.": "Покрытие по направлениям.",
    "Reachability signal.": "Вероятность выхода на контакт.",
    "Source trust and consistency.": "Надёжность и согласованность источника.",
    "No standalone workflow state yet. Run the pipeline first so standalone can create a vendor workflow profile.": "Состояние рабочего процесса пока не сформировано. Сначала запусти обработку, чтобы система создала профиль поставщика.",
    "Qualification status": "Статус квалификации",
    "Lifecycle state": "Этап жизненного цикла",
    "Routing state": "Статус маршрутизации",
    "Outreach ready": "Готово к контакту",
    "Ready": "Готово",
    "Not ready": "Не готово",
    "Operator notes": "Заметки оператора",
    "No standalone commercial state yet. Create it here instead of treating downstream Odoo feedback as your editable source of truth.": "Коммерческое состояние пока не заведено. Создай его здесь, а не используй внешнюю обратную связь как редактируемый источник истины.",
    "Prospect": "Потенциальный клиент",
    "Active customer": "Активный клиент",
    "Dormant": "Неактивный",
    "New lead": "Новый лид",
    "Contacting": "В контакте",
    "RFQ requested": "Запрошен расчёт",
    "Quoted": "Просчитано",
    "Won": "Выиграно",
    "Lost": "Проиграно",
    "On hold": "На паузе",
    "Customer reference": "Код клиента",
    "Opportunity reference": "Код сделки",
    "Next action due at": "Срок следующего действия",
    "Save standalone commercial state": "Сохранить коммерческое состояние",
    "Customer ref": "Код клиента",
    "Opportunity ref": "Код сделки",
    "Next action due": "Срок следующего действия",
    "No standalone customer account yet. Create the minimum account owner here instead of relying on Odoo partner ownership for this contour.": "Карточка клиента пока не создана. Заведи минимальную карточку здесь, вместо зависимости от партнёра в Odoo.",
    "Customer account form": "Форма карточки клиента",
    "Agency": "Агентство",
    "Reseller": "Реселлер",
    "Internal": "Внутренний",
    "Active": "Активен",
    "Inactive": "Неактивен",
    "Primary contact": "Основной контакт",
    "Primary email": "Основная почта",
    "Primary phone": "Основной телефон",
    "Billing city": "Город для документов",
    "External customer ref": "Внешний код клиента",
    "Save customer account": "Сохранить карточку клиента",
    "No linked opportunity": "Связанной сделки нет",
    "Opportunity": "Сделка",
    "Requested": "Запрошено",
    "Pricing": "Расчёт",
    "Last status change": "Последнее изменение статуса",
    "Update quote workflow": "Обновить расчёт",
    "Handoff status": "Статус передачи",
    "No linked account": "Связанной карточки нет",
    "Open feedback status": "Открыть статус обратной связи",
    "Back to company workbench": "Назад к карточке компании",
    "Open company workbench": "Открыть карточку компании",
    "Open quote workbench": "Открыть карточку расчёта",
    "Back to company": "Назад к компании",
    "No company mapping found.": "Связанная компания не найдена.",
    "Unmatched": "Без привязки",
    "No company mapping found for this quote intent.": "Для этой заявки на расчёт не найдена связанная компания.",
    "Update quote workflow": "Обновить расчёт",
    "Save quote workflow": "Сохранить расчёт",
    "No company mapping found for this handoff.": "Для этой передачи не найдена связанная компания.",
    "Open handoff list": "Открыть список передач",
    "Back to feedback status": "Назад к статусу обратной связи",
    "Open timeline": "Открыть историю",
    "Open feedback status": "Открыть статус обратной связи",
    "Open opportunity": "Открыть сделку",
    "Open opportunity list": "Открыть список сделок",
    "Back to quote workbench": "Назад к карточке расчёта",
    "Back to opportunity": "Назад к сделке",
    "No company mapping found for this quote intent.": "Для этой заявки на расчёт связанная компания не найдена.",
    "Feedback": "Обратная связь",
    "Canonical key": "Канонический ключ",
    "Confidence": "Уверенность",
    "Parser confidence": "Уверенность парсера",
    "Source confidence": "Уверенность источника",
    "Source fingerprint": "Отпечаток источника",
    "Dedup fingerprint": "Отпечаток дедупликации",
    "Provisional": "Предварительно квалифицирован",
    "Unreviewed": "Не проверено",
    "Approved supplier": "Одобренный поставщик",
    "Potential supplier": "Потенциальный поставщик",
    "Needs manual review": "Нужна ручная проверка",
    "Duplicate": "Дубликат",
    "Not relevant": "Не подходит",
    "Unreachable": "Недоступен",
    "Account name": "Название аккаунта",
    "Account type": "Тип аккаунта",
    "Direct customer": "Прямой клиент",
    "Internal account": "Внутренний аккаунт",
    "Account status": "Статус аккаунта",
    "No standalone opportunities yet. Create a commercial owner record here instead of relying on Odoo lead state.": "Сделок пока нет. Создай коммерческую запись здесь, вместо зависимости от состояния лида в Odoo.",
    "New": "Новый",
    "Why this company is currently in manual review and how the queue is moving.": "Почему эта компания сейчас находится на ручной проверке и как движется очередь.",
    "High composite score; ready for qualification decision": "Высокая итоговая оценка; можно принимать решение по квалификации.",
    "Pending": "Ожидает",
    "Done": "Готово",
    "Update": "Обновить",
    "Open dedicated timeline": "Открыть полную историю",
    "Domain": "Домен",
    "Fetch": "Получение",
    "No list fields": "Списковые поля отсутствуют",
    "Quote / RFQ type": "Тип запроса на расчёт",
    "Service quote": "Расчёт услуги",
    "RFQ packaging": "Запрос на расчёт упаковки",
    "RFQ labels": "Запрос на расчёт этикеток",
    "RFQ printing": "Запрос на расчёт печати",
    "Sample request": "Запрос образца",
    "Quantity hint": "Ориентир по количеству",
    "No linked quote intent": "Связанной заявки на расчёт нет",
    "Trace Odoo partner ref (optional)": "Ссылка на партнёра Odoo (необязательно)",
    "Trace Odoo lead ref (optional)": "Ссылка на лид Odoo (необязательно)",
    "Source discovery rows persisted in standalone storage.": "Исходные записи сохранены в автономном хранилище.",
    "Deduplicated supplier/company intelligence owned by standalone.": "Дедуплицированные данные о компаниях и поставщиках принадлежат автономному контуру.",
    "Companies with composite scoring ready for review routing.": "Компании с итоговой оценкой, готовые к маршрутизации и проверке.",
    "Open the company workbench and inspect one supplier end-to-end.": "Открой карточку компании и проверь поставщика целиком в одном месте.",
    "See computed supplier scores and jump straight into a company workbench.": "Открой рассчитанные оценки поставщиков и сразу перейди в карточку компании.",
    "Track RFQ / quote requests in standalone instead of deferring everything to ERP.": "Веди запросы на расчёт внутри автономного контура, а не откладывай всё до ERP.",
    "Track standalone-owned commercial follow-up instead of hiding it in Odoo lead state.": "Веди коммерческое сопровождение внутри автономного контура, а не прячь его в статусе лида Odoo.",
    "Track execution handoff in standalone instead of pushing everything into ERP orders.": "Веди передачу в производство внутри автономного контура, а не отправляй всё сразу в ERP-заказы.",
    "Move active jobs across execution states with a simple operator board.": "Перемещай активные задания по статусам исполнения через простую операторскую доску.",
    "RFQ ready": "Готово к запросу на расчёт",
    "RFQ reference": "Номер запроса",
    "e.g. 5,000 boxes / 10,000 labels": "например, 5 000 коробок / 10 000 этикеток",
}

_UI_PREFIX_RU = {
    "Standalone commercial opportunities for ": "Сделки по компании ",
    "Quote intent #": "Заявка на расчёт #",
    "Production handoff #": "Передача в производство #",
    "Handoff #": "Передача #",
    "Quote #": "Расчёт #",
}

_UI_LABEL_RU = {
    "raw_records": "Исходные данные",
    "canonical_companies": "Канонические компании",
    "vendor_scores": "Оценки поставщиков",
    "review_queue": "Очередь проверки",
    "feedback_events": "События обратной связи",
    "companies_with_feedback": "Компании с обратной связью",
    "routing_feedback": "Отклики по маршрутизации",
    "synthetic_feedback_events_count": "Тестовая обратная связь",
    "canonical_name": "Каноническое имя",
    "canonical_key": "Канонический ключ",
    "company_key": "Ключ компании",
    "city": "Город",
    "address_text": "Адрес",
    "canonical_email": "Электронная почта",
    "canonical_phone": "Телефон",
    "website": "Сайт",
    "capabilities": "Направления",
    "review_status": "Статус проверки",
    "confidence": "Уверенность",
    "parser_confidence": "Уверенность парсера",
    "source_confidence": "Уверенность источника",
    "source_fingerprint": "Отпечаток источника",
    "dedup_fingerprint": "Отпечаток дедупликации",
    "account_name": "Название аккаунта",
    "account_type": "Тип аккаунта",
    "account_status": "Статус аккаунта",
    "primary_contact_name": "Основной контакт",
    "primary_email": "Основная почта",
    "primary_phone": "Основной телефон",
    "billing_city": "Город биллинга",
    "external_customer_ref": "Внешний код клиента",
    "customer_status": "Статус клиента",
    "commercial_stage": "Коммерческая стадия",
    "customer_reference": "Код клиента",
    "opportunity_reference": "Код сделки",
    "next_action": "Следующее действие",
    "next_action_due_at": "Срок следующего действия",
    "title": "Название",
    "status": "Статус",
    "source_channel": "Канал источника",
    "estimated_value": "Оценочная сумма",
    "currency_code": "Код валюты",
    "target_due_at": "Целевой срок",
    "external_opportunity_ref": "Внешний код сделки",
    "odoo_lead_ref": "Код лида Odoo",
    "notes": "Заметки",
    "quantity_hint": "Подсказка по количеству",
    "quote_type": "Тип котировки",
    "quote_reference": "Номер котировки",
    "quoted_amount": "Сумма котировки",
    "pricing_notes": "Комментарии к расчёту",
    "quote_intent_id": "ID заявки на расчёт",
    "handoff_status": "Статус передачи",
    "production_reference": "Производственный код",
    "requested_ship_at": "Запрошенная дата отгрузки",
    "specification_summary": "Сводка спецификации",
    "created_at": "Создано",
    "updated_at": "Обновлено",
    "event_id": "ID события",
    "occurred_at": "Когда",
    "event_type": "Тип события",
    "reason_code": "Код причины",
    "queue_name": "Очередь",
    "score": "Оценка",
    "outcome": "Исход",
    "outreach_ready": "Готово к контакту",
    "rfq_ready": "Готово к запросу на расчёт",
    "opportunity_id": "ID сделки",
    "quote_id": "ID котировки",
    "partner_linked": "Партнёр связан",
    "crm_linked": "CRM связана",
    "rfq_reference": "Номер запроса",
    "source_type": "Тип источника",
    "source_domain": "Домен источника",
    "scenario_key": "Ключ сценария",
    "candidate_dedup_fingerprint": "Кандидатный отпечаток дедупликации",
}

_UI_VALUE_LABEL_RU = {
    "new": "Новый",
    "contacting": "Контакт",
    "qualified": "Квалифицирован",
    "rfq_requested": "Запрошен расчёт",
    "quoted": "Просчитан",
    "won": "Выигран",
    "lost": "Проигран",
    "on_hold": "На паузе",
    "requested": "Запрошен",
    "pricing": "Ценообразование",
    "ready_for_production": "Готово к производству",
    "scheduled": "Запланировано",
    "in_progress": "В работе",
    "blocked": "Заблокировано",
    "completed": "Завершено",
    "approved_supplier": "Одобренный поставщик",
    "potential_supplier": "Потенциальный поставщик",
    "provisional": "Предварительно квалифицирован",
    "unqualified": "Не квалифицирован",
    "unreviewed": "Не проверено",
    "needs_manual_review": "Нужна ручная проверка",
    "needs_review": "Нужна проверка",
    "duplicate": "Дубликат",
    "not_relevant": "Не релевантно",
    "unreachable": "Недоступен",
    "pending": "Ожидает",
    "done": "Готово",
    "dismissed": "Отклонено",
    "prospect": "Проспект",
    "active_customer": "Активный клиент",
    "dormant": "Неактивен",
    "active": "Активен",
    "inactive": "Неактивен",
    "direct_customer": "Прямой клиент",
    "agency": "Агентство",
    "reseller": "Реселлер",
    "internal": "Внутренний",
    "new_lead": "Новый лид",
    "service_quote": "Расчёт услуги",
    "rfq_packaging": "Запрос на расчёт упаковки",
    "rfq_labels": "Запрос на расчёт этикеток",
    "rfq_printing": "Запрос на расчёт печати",
    "sample_request": "Запрос образца",
    "print_flexo": "Флексопечать",
    "print_offset": "Офсетная печать",
    "label_self_adhesive": "Самоклеящиеся этикетки",
    "pack_corrugated": "Гофрокартонная упаковка",
    "wide_format": "Широкоформатная печать",
    "offset_printing": "Офсетная печать",
    "label_printing": "Печать этикеток",
    "packaging": "Упаковка",
    "promo_items": "Промоматериалы",
    "routing_feedback": "Маршрутизация",
    "qualification_feedback": "Квалификация",
    "partner_linkage_feedback": "Связка с партнёром",
    "commercial_disposition_feedback": "Коммерческий исход",
    "qualification_review": "Проверка квалификации",
    "supplier_review": "Проверка поставщика",
    "dedup_review": "Проверка дубликатов",
    "manual_intake": "Ручной ввод",
    "manual_override": "Ручное переопределение",
    "missing": "Отсутствует",
}


def _current_locale() -> str:
    # Локаль живёт в request-local контексте, чтобы backend UI не протекал между запросами.
    return _REQUEST_LOCALE.get()


def _translate_exact(text: str) -> str:
    if _current_locale() != "ru" or not text:
        return text
    if text in _UI_TEXT_RU:
        return _UI_TEXT_RU[text]
    if text in _UI_LABEL_RU:
        return _UI_LABEL_RU[text]
    if text in _UI_VALUE_LABEL_RU:
        return _UI_VALUE_LABEL_RU[text]
    for source, target in _UI_PREFIX_RU.items():
        if text.startswith(source):
            return target + text[len(source):]
    return text


def _translate_preserving_whitespace(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    translated = _translate_exact(stripped)
    if translated == stripped:
        return text
    leading_len = len(text) - len(text.lstrip())
    trailing_len = len(text) - len(text.rstrip())
    leading = text[:leading_len]
    trailing = text[len(text) - trailing_len :] if trailing_len else ""
    return f"{leading}{translated}{trailing}"


def _localize_html_fragment(fragment: str) -> str:
    if _current_locale() != "ru" or not fragment:
        return fragment

    # Локализуем уже готовый HTML точечными заменами, чтобы не тащить отдельный шаблонный слой.
    def replace_text(match: re.Match[str]) -> str:
        return f"{match.group(1)}{_translate_preserving_whitespace(match.group(2))}"

    localized = _HTML_TEXT_RE.sub(replace_text, fragment)

    def replace_attr(match: re.Match[str]) -> str:
        value = html.unescape(match.group("value"))
        translated = _translate_exact(value)
        if translated == value:
            return match.group(0)
        return f'{match.group("name")}="{html.escape(translated, quote=True)}"'

    return _HTML_ATTR_RE.sub(replace_attr, localized)


def _detect_ui_locale(environ: dict[str, Any]) -> str:
    cookie_header = environ.get("HTTP_COOKIE", "")
    if cookie_header:
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        value = cookie.get(LOCALE_COOKIE_NAME)
        if value and value.value in SUPPORTED_UI_LOCALES:
            return value.value

    accept_language = (environ.get("HTTP_ACCEPT_LANGUAGE") or "").lower()
    if accept_language.startswith("en"):
        return "en"
    if accept_language.startswith("ru"):
        return "ru"
    return DEFAULT_UI_LOCALE


class SupplierIntelligenceApiService:
    def __init__(self, db_path: str | Path, default_query: str = "printing packaging vietnam", default_country: str = "VN", integration_token: str | None = None):
        self.db_path = Path(db_path)
        self.default_query = default_query
        self.default_country = default_country
        self.integration_token = integration_token

    def _store(self) -> SqliteSupplierIntelligenceStore:
        return SqliteSupplierIntelligenceStore(self.db_path)

    def _operations(self) -> SupplierOperationsService:
        return SupplierOperationsService(self._store())

    def _workforce_engine(self) -> WorkforceEstimationEngine:
        return WorkforceEstimationEngine()

    def _workforce_cases(self) -> dict[str, dict[str, Any]]:
        if not DEFAULT_WORKFORCE_FIXTURE.exists():
            return {}
        payload = json.loads(DEFAULT_WORKFORCE_FIXTURE.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return {}
        return payload

    def health(self) -> dict[str, object]:
        return {"status": "ok", "service": "magon-standalone", "db_path": str(self.db_path.resolve())}

    def status(self) -> dict[str, object]:
        store = self._store()
        return {**self.health(), "storage_counts": store.snapshot_counts()}

    def list_raw_records(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_raw_records(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_companies(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_companies(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_scores(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_scores(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_dedup_decisions(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_dedup_decisions(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_review_queue(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_review_queue(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_feedback_events(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_feedback_events(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def list_feedback_status(self, limit: int = 100, offset: int = 0) -> dict[str, object]:
        items = self._store().list_feedback_status(limit=limit, offset=offset)
        return {"items": items, "count": len(items), "limit": limit, "offset": offset}

    def get_feedback_status(self, source_key: str) -> dict[str, object]:
        item = self._store().get_feedback_status(source_key)
        if item is None:
            raise LookupError(source_key)
        return {"item": item}

    def estimate_workforce(self, payload: dict[str, Any]) -> dict[str, object]:
        estimation_input = _workforce_input_from_json(payload)
        result = self._workforce_engine().estimate(estimation_input)
        return {
            "input": payload,
            "result": _workforce_result_to_json(result),
        }

    def ingest_feedback_events(self, events: list[dict[str, Any]]) -> dict[str, object]:
        applied = self._store().save_feedback_events([_feedback_event_from_json(item) for item in events])
        return {"accepted": applied, "received": len(events), "status": "ok"}

    def run_pipeline(self, query: str | None = None, country: str | None = None, fixture: str | None = None) -> dict[str, object]:
        return run_standalone_pipeline(db_path=self.db_path, query=query or self.default_query, country=country or self.default_country, fixture_path=fixture)

    def operator_dashboard(self) -> dict[str, Any]:
        store = self._store()
        counts = store.snapshot_counts()
        companies = store.list_companies(limit=5000, offset=0)
        scores_by_key = {item["company_key"]: item for item in store.list_scores(limit=5000, offset=0)}
        feedback_rows = store.list_feedback_status(limit=5000, offset=0)
        feedback_by_key = {item["source_key"]: item for item in feedback_rows}
        feedback_events = store.list_feedback_events(limit=5000, offset=0)
        queue_by_company: dict[str, list[dict[str, Any]]] = {}
        for item in store.list_review_queue(limit=5000, offset=0):
            queue_by_company.setdefault(item.get("company_key") or "", []).append(item)

        routing_feedback = sum(1 for item in feedback_rows if item.get("routing_outcome"))
        qualification_feedback = sum(1 for item in feedback_rows if item.get("qualification_status"))
        commercial_feedback = sum(1 for item in feedback_rows if item.get("lead_status") or item.get("crm_linked"))
        linked_partners = sum(1 for item in feedback_rows if item.get("partner_linked"))
        companies_with_feedback = sum(1 for item in feedback_rows if item.get("last_event_id"))
        synthetic_feedback_events_count = sum(1 for item in feedback_events if item.get("is_synthetic"))

        companies_by_key = {item.get("canonical_key") or "": item for item in companies}
        recent_companies: list[dict[str, Any]] = []
        for company in companies[:6]:
            company_key = company.get("canonical_key") or ""
            recent_companies.append(
                {
                    "company": company,
                    "score": scores_by_key.get(company_key),
                    "feedback": feedback_by_key.get(company_key),
                    "queue_items": queue_by_company.get(company_key, []),
                }
            )

        recent_feedback: list[dict[str, Any]] = []
        for event in feedback_events[:6]:
            source_key = event.get("source_key") or ""
            recent_feedback.append(
                {
                    "event": event,
                    "company": companies_by_key.get(source_key),
                    "timeline_href": f"/ui/feedback-status/{quote(source_key, safe='')}" if source_key else "/ui/feedback-events",
                }
            )

        return {
            "counts": counts,
            "companies_with_feedback": companies_with_feedback,
            "routing_feedback": routing_feedback,
            "qualification_feedback": qualification_feedback,
            "commercial_feedback": commercial_feedback,
            "linked_partners": linked_partners,
            "synthetic_feedback_events_count": synthetic_feedback_events_count,
            "fixture_path": str(DEFAULT_UI_FIXTURE),
            "recent_companies": recent_companies,
            "recent_feedback": recent_feedback,
        }

    def operator_companies(self, search: str = "", city: str = "", capability: str = "", has_feedback: str = "", limit: int = 50, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        companies = store.list_companies(limit=5000, offset=0)
        scores = {item["company_key"]: item for item in store.list_scores(limit=5000, offset=0)}
        feedback = {item["source_key"]: item for item in store.list_feedback_status(limit=5000, offset=0)}
        queue_items = store.list_review_queue(limit=5000, offset=0)
        queue_by_company: dict[str, list[dict[str, Any]]] = {}
        for item in queue_items:
            queue_by_company.setdefault(item["company_key"], []).append(item)

        cities = sorted({item.get("city") for item in companies if item.get("city")})
        capabilities = sorted({cap for item in companies for cap in (item.get("capabilities") or [])})

        filtered: list[dict[str, Any]] = []
        search_lower = search.strip().lower()
        for company in companies:
            company_feedback = feedback.get(company.get("canonical_key") or "")
            company_score = scores.get(company.get("canonical_key") or "")
            company_queues = queue_by_company.get(company.get("canonical_key") or "", [])
            haystack = " ".join(
                [
                    str(company.get("canonical_name") or ""),
                    str(company.get("legal_name") or ""),
                    str(company.get("website") or ""),
                    str(company.get("canonical_email") or ""),
                    str(company.get("canonical_phone") or ""),
                    " ".join(company.get("capabilities") or []),
                    str(company.get("city") or ""),
                ]
            ).lower()
            if search_lower and search_lower not in haystack:
                continue
            if city and (company.get("city") or "") != city:
                continue
            if capability and capability not in (company.get("capabilities") or []):
                continue
            if has_feedback == "yes" and not company_feedback:
                continue
            if has_feedback == "no" and company_feedback:
                continue
            filtered.append(
                {
                    **company,
                    "score": company_score,
                    "feedback": company_feedback,
                    "queue_items": company_queues,
                }
            )

        filtered.sort(key=lambda item: (item.get("score") or {}).get("composite_score", 0.0), reverse=True)
        paged = filtered[offset : offset + limit]
        return {
            "items": paged,
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
            "search": search,
            "city": city,
            "capability": capability,
            "has_feedback": has_feedback,
            "city_options": cities,
            "capability_options": capabilities,
        }

    def operator_company_detail(self, company_id: int) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        canonical_key = company.get("canonical_key") or ""
        score = store.get_score(canonical_key)
        vendor_profile = store.get_vendor_profile(canonical_key)
        queue_items = store.list_review_queue(company_key=canonical_key, limit=0, offset=0)
        qualification_decisions = store.list_qualification_decisions(company_key=canonical_key, limit=200, offset=0)
        routing_audit = store.list_routing_audit(company_key=canonical_key, limit=200, offset=0)
        commercial_record = store.get_commercial_record(canonical_key)
        customer_account = store.get_customer_account(canonical_key)
        opportunities = store.list_commercial_opportunities(company_key=canonical_key, limit=0, offset=0)
        quote_intents = store.list_quote_intents(company_key=canonical_key, limit=0, offset=0)
        production_handoffs = store.list_production_handoffs(company_key=canonical_key, limit=0, offset=0)
        commercial_audit = store.list_commercial_audit(company_key=canonical_key, limit=200, offset=0)
        feedback_projection = store.get_feedback_status(canonical_key)
        feedback_events = store.list_feedback_events(limit=0, offset=0, source_key=canonical_key)
        raw_records = store.list_raw_records_linked(
            source_fingerprint=company.get("source_fingerprint") or "",
            dedup_fingerprint=company.get("dedup_fingerprint") or "",
            limit=0,
            offset=0,
        )
        return {
            "company": company,
            "score": score,
            "vendor_profile": vendor_profile,
            "queue_items": queue_items,
            "qualification_decisions": qualification_decisions,
            "routing_audit": routing_audit,
            "commercial_record": commercial_record,
            "customer_account": customer_account,
            "opportunities": opportunities,
            "quote_intents": quote_intents,
            "production_handoffs": production_handoffs,
            "commercial_audit": commercial_audit,
            "feedback_projection": feedback_projection,
            "feedback_events": feedback_events,
            "raw_records": raw_records,
        }

    def operator_upsert_customer_account(
        self,
        company_id: int,
        account_name: str,
        account_type: str,
        account_status: str,
        primary_contact_name: str = "",
        primary_email: str = "",
        primary_phone: str = "",
        billing_city: str = "",
        external_customer_ref: str = "",
        odoo_partner_ref: str = "",
        notes: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        if account_type not in {"direct_customer", "agency", "reseller", "internal"}:
            raise ValueError("invalid_account_type")
        if account_status not in {"prospect", "active", "inactive", "blocked"}:
            raise ValueError("invalid_account_status")
        record = store.upsert_customer_account(
            company_key=company.get("canonical_key") or "",
            account_name=account_name,
            account_type=account_type,
            account_status=account_status,
            primary_contact_name=primary_contact_name,
            primary_email=primary_email,
            primary_phone=primary_phone,
            billing_city=billing_city,
            external_customer_ref=external_customer_ref,
            odoo_partner_ref=odoo_partner_ref,
            notes=notes,
            actor=actor,
        )
        return {"company": company, "customer_account": record, "storage_counts": store.snapshot_counts()}

    def operator_opportunities(self, status: str = "", company_id: int | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        company_key = ""
        company = None
        if company_id is not None:
            company = store.get_company_by_id(company_id)
            if company is None:
                raise LookupError(f"company:{company_id}")
            company_key = company.get("canonical_key") or ""
        records = store.list_commercial_opportunities(company_key=company_key or None, status=status or None, limit=limit, offset=offset)
        total = store.count_commercial_opportunities(company_key=company_key or None, status=status or None)
        company_keys = [item.get("company_key") or "" for item in records]
        companies = store.list_companies_by_keys(company_keys)
        account_ids = [int(item.get("customer_account_id") or 0) for item in records if int(item.get("customer_account_id") or 0) > 0]
        accounts = {int(item["id"]): item for item in (store.get_customer_account_by_id(account_id) for account_id in sorted(set(account_ids))) if item}
        items = [{**record, "company": companies.get(record.get("company_key") or ""), "customer_account": accounts.get(int(record.get("customer_account_id") or 0))} for record in records]
        return {"items": items, "total": total, "limit": limit, "offset": offset, "status": status, "company": company}

    def operator_opportunity_detail(self, opportunity_id: int) -> dict[str, Any]:
        store = self._store()
        record = store.get_commercial_opportunity(opportunity_id)
        if record is None:
            raise LookupError(f"commercial_opportunity:{opportunity_id}")
        company = store.get_company_by_key(record.get("company_key") or "")
        customer_account = store.get_customer_account_by_id(int(record.get("customer_account_id") or 0)) if record.get("customer_account_id") else None
        quote_intents = store.list_quote_intents(company_key=record.get("company_key") or "", limit=0, offset=0)
        linked_quotes = [item for item in quote_intents if int(item.get("opportunity_id") or 0) == opportunity_id]
        audit = store.list_commercial_audit(entity_type="commercial_opportunity", entity_id=opportunity_id, limit=200, offset=0)
        return {
            "opportunity": record,
            "company": company,
            "customer_account": customer_account,
            "quote_intents": linked_quotes,
            "audit": audit,
        }

    def operator_create_opportunity(
        self,
        company_id: int,
        customer_account_id: int | None,
        title: str,
        status: str,
        source_channel: str = "",
        estimated_value: str = "",
        currency_code: str = "VND",
        target_due_at: str = "",
        next_action: str = "",
        notes: str = "",
        external_opportunity_ref: str = "",
        odoo_lead_ref: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        if status not in {"new", "contacting", "qualified", "rfq_requested", "quoted", "won", "lost", "on_hold"}:
            raise ValueError("invalid_opportunity_status")
        parsed_value = float(estimated_value) if estimated_value.strip() else None
        record = store.create_commercial_opportunity(
            company_key=company.get("canonical_key") or "",
            customer_account_id=customer_account_id,
            title=title,
            status=status,
            source_channel=source_channel,
            estimated_value=parsed_value,
            currency_code=(currency_code or "VND").upper(),
            target_due_at=target_due_at,
            next_action=next_action,
            notes=notes,
            external_opportunity_ref=external_opportunity_ref,
            odoo_lead_ref=odoo_lead_ref,
            actor=actor,
        )
        return {"company": company, "opportunity": record, "storage_counts": store.snapshot_counts()}

    def operator_update_opportunity(
        self,
        opportunity_id: int,
        title: str,
        status: str,
        customer_account_id: int | None,
        source_channel: str = "",
        estimated_value: str = "",
        currency_code: str = "VND",
        target_due_at: str = "",
        next_action: str = "",
        notes: str = "",
        external_opportunity_ref: str = "",
        odoo_lead_ref: str = "",
        actor: str = "local_operator",
    ) -> dict[str, Any]:
        store = self._store()
        if status not in {"new", "contacting", "qualified", "rfq_requested", "quoted", "won", "lost", "on_hold"}:
            raise ValueError("invalid_opportunity_status")
        parsed_value = float(estimated_value) if estimated_value.strip() else None
        record = store.update_commercial_opportunity(
            opportunity_id=opportunity_id,
            title=title,
            status=status,
            customer_account_id=customer_account_id,
            source_channel=source_channel,
            estimated_value=parsed_value,
            currency_code=(currency_code or "VND").upper(),
            target_due_at=target_due_at,
            next_action=next_action,
            notes=notes,
            external_opportunity_ref=external_opportunity_ref,
            odoo_lead_ref=odoo_lead_ref,
            actor=actor,
        )
        company = store.get_company_by_key(record.get("company_key") or "")
        return {"company": company, "opportunity": record, "storage_counts": store.snapshot_counts()}

    def operator_apply_decision(self, company_id: int, outcome: str, reason_code: str = "", notes: str = "", manual_override: bool = True) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        result = self._operations().decide(
            company_key=company.get("canonical_key") or "",
            reason_code=reason_code,
            notes=notes,
            manual_override=manual_override,
            forced_outcome=outcome,
        )
        return {"company": company, "result": result, "storage_counts": store.snapshot_counts()}

    def operator_transition_queue(self, queue_id: int, target_status: str, reason_code: str, notes: str = "", allow_reprocess: bool = False) -> dict[str, Any]:
        store = self._store()
        store.transition_review_queue(queue_id=queue_id, target_status=target_status, reason_code=reason_code, notes=notes, allow_reprocess=allow_reprocess)
        queue_item = store.get_review_queue(queue_id)
        company = None
        if queue_item:
            company = store.get_company_by_key(queue_item.get("company_key") or "")
        return {"queue_item": queue_item, "company": company, "storage_counts": store.snapshot_counts()}

    def operator_update_commercial(
        self,
        company_id: int,
        customer_status: str,
        commercial_stage: str,
        customer_reference: str = "",
        opportunity_reference: str = "",
        next_action: str = "",
        next_action_due_at: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        if customer_status not in {"prospect", "active_customer", "dormant", "blocked"}:
            raise ValueError("invalid_customer_status")
        if commercial_stage not in {"new_lead", "contacting", "qualified", "rfq_requested", "quoted", "won", "lost", "on_hold"}:
            raise ValueError("invalid_commercial_stage")
        record = store.upsert_commercial_record(
            company_key=company.get("canonical_key") or "",
            customer_status=customer_status,
            commercial_stage=commercial_stage,
            customer_reference=customer_reference,
            opportunity_reference=opportunity_reference,
            next_action=next_action,
            next_action_due_at=next_action_due_at,
            notes=notes,
            actor="local_operator",
        )
        return {"company": company, "commercial_record": record, "storage_counts": store.snapshot_counts()}

    def operator_commercial_pipeline(self, stage: str = "", customer_status: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        records = store.list_commercial_records(
            stage=stage or None,
            customer_status=customer_status or None,
            limit=limit,
            offset=offset,
        )
        total = store.count_commercial_records(stage=stage or None, customer_status=customer_status or None)
        company_keys = [item.get("company_key") or "" for item in records]
        companies = store.list_companies_by_keys(company_keys)
        feedback = store.list_feedback_status_by_source_keys(company_keys)
        accounts = {item["company_key"]: item for item in (store.get_customer_account(item.get("company_key") or "") for item in records) if item}
        items = [
            {
                **record,
                "company": companies.get(record.get("company_key") or ""),
                "feedback": feedback.get(record.get("company_key") or ""),
                "customer_account": accounts.get(record.get("company_key") or ""),
            }
            for record in records
        ]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "stage": stage,
            "customer_status": customer_status,
        }

    def operator_quote_pipeline(self, status: str = "", quote_type: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        records = store.list_quote_intents(
            status=status or None,
            quote_type=quote_type or None,
            limit=limit,
            offset=offset,
        )
        total = store.count_quote_intents(status=status or None, quote_type=quote_type or None)
        company_keys = [item.get("company_key") or "" for item in records]
        companies = store.list_companies_by_keys(company_keys)
        account_ids = [int(item.get("customer_account_id") or 0) for item in records if int(item.get("customer_account_id") or 0) > 0]
        accounts = {int(item["id"]): item for item in (store.get_customer_account_by_id(account_id) for account_id in sorted(set(account_ids))) if item}
        opportunity_ids = [int(item.get("opportunity_id") or 0) for item in records if int(item.get("opportunity_id") or 0) > 0]
        opportunities = store.list_commercial_opportunities_by_ids(opportunity_ids)
        quote_ids = [int(item.get("id") or 0) for item in records if int(item.get("id") or 0) > 0]
        handoff_by_quote = store.list_production_handoffs_by_quote_intent_ids(quote_ids)
        items = []
        for record in records:
            quote_id = int(record.get("id") or 0)
            company_key = record.get("company_key") or ""
            items.append(
                {
                    **record,
                    "company": companies.get(company_key),
                    "customer_account": accounts.get(int(record.get("customer_account_id") or 0)),
                    "opportunity": opportunities.get(int(record.get("opportunity_id") or 0)),
                    "production_handoff": handoff_by_quote.get(quote_id),
                }
            )
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "status": status,
            "quote_type": quote_type,
        }

    def operator_quote_intent_detail(self, quote_intent_id: int) -> dict[str, Any]:
        store = self._store()
        record = store.get_quote_intent(quote_intent_id)
        if record is None:
            raise LookupError(f"quote_intent:{quote_intent_id}")
        company = store.get_company_by_key(record.get("company_key") or "")
        customer_account = store.get_customer_account_by_id(int(record.get("customer_account_id") or 0)) if record.get("customer_account_id") else None
        opportunity = store.get_commercial_opportunity(int(record.get("opportunity_id") or 0)) if record.get("opportunity_id") else None
        commercial_record = store.get_commercial_record(record.get("company_key") or "")
        feedback_projection = store.get_feedback_status(record.get("company_key") or "")
        handoffs = store.list_production_handoffs(quote_intent_id=quote_intent_id, limit=0, offset=0)
        audit = store.list_commercial_audit(entity_type="quote_intent", entity_id=quote_intent_id, limit=200, offset=0)
        return {
            "quote_intent": record,
            "company": company,
            "customer_account": customer_account,
            "opportunity": opportunity,
            "commercial_record": commercial_record,
            "feedback_projection": feedback_projection,
            "production_handoffs": handoffs,
            "audit": audit,
        }

    def operator_production_handoffs(self, status: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        records = store.list_production_handoffs(status=status or None, limit=limit, offset=offset)
        total = store.count_production_handoffs(status=status or None)
        company_keys = [item.get("company_key") or "" for item in records]
        companies = store.list_companies_by_keys(company_keys)
        quote_ids = [int(item.get("quote_intent_id") or 0) for item in records if int(item.get("quote_intent_id") or 0) > 0]
        quote_intents = store.list_quote_intents_by_ids(quote_ids)
        opportunity_ids = [int(item.get("opportunity_id") or 0) for item in quote_intents.values() if int(item.get("opportunity_id") or 0) > 0]
        opportunities = store.list_commercial_opportunities_by_ids(opportunity_ids)
        items = [
            {
                **record,
                "company": companies.get(record.get("company_key") or ""),
                "quote_intent": quote_intents.get(int(record.get("quote_intent_id") or 0)),
                "opportunity": opportunities.get(int((quote_intents.get(int(record.get("quote_intent_id") or 0)) or {}).get("opportunity_id") or 0)),
            }
            for record in records
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset, "status": status}

    def operator_production_board(self) -> dict[str, Any]:
        data = self.operator_production_handoffs(status="", limit=0, offset=0)
        columns = ["ready_for_production", "scheduled", "in_progress", "blocked", "completed"]
        grouped: dict[str, list[dict[str, Any]]] = {key: [] for key in columns}
        for item in data["items"]:
            grouped.setdefault(item.get("handoff_status") or "ready_for_production", []).append(item)
        return {"columns": grouped, "total": data["total"]}

    def operator_production_handoff_detail(self, handoff_id: int) -> dict[str, Any]:
        store = self._store()
        record = store.get_production_handoff(handoff_id)
        if record is None:
            raise LookupError(f"production_handoff:{handoff_id}")
        company = store.get_company_by_key(record.get("company_key") or "")
        quote_intent = store.get_quote_intent(int(record.get("quote_intent_id") or 0)) if record.get("quote_intent_id") else None
        opportunity = store.get_commercial_opportunity(int(quote_intent.get("opportunity_id") or 0)) if quote_intent and quote_intent.get("opportunity_id") else None
        audit = store.list_commercial_audit(entity_type="production_handoff", entity_id=handoff_id, limit=200, offset=0)
        return {"production_handoff": record, "company": company, "quote_intent": quote_intent, "opportunity": opportunity, "audit": audit}

    def operator_create_quote_intent(
        self,
        company_id: int,
        customer_account_id: int | None,
        opportunity_id: int | None,
        quote_type: str,
        quantity_hint: str = "",
        target_due_at: str = "",
        status: str = "requested",
        rfq_reference: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        if quote_type not in {"sample_request", "rfq_packaging", "rfq_labels", "rfq_printing", "service_quote"}:
            raise ValueError("invalid_quote_type")
        if status not in {"requested", "pricing", "quoted", "won", "lost", "on_hold"}:
            raise ValueError("invalid_quote_status")
        record = store.create_quote_intent(
            company_key=company.get("canonical_key") or "",
            customer_account_id=customer_account_id,
            opportunity_id=opportunity_id,
            quote_type=quote_type,
            quantity_hint=quantity_hint,
            target_due_at=target_due_at,
            status=status,
            rfq_reference=rfq_reference,
            notes=notes,
            actor="local_operator",
        )
        return {"company": company, "quote_intent": record, "storage_counts": store.snapshot_counts()}

    def operator_update_quote_intent(
        self,
        quote_intent_id: int,
        customer_account_id: int | None,
        opportunity_id: int | None,
        status: str,
        rfq_reference: str = "",
        quote_reference: str = "",
        quoted_amount: str = "",
        currency_code: str = "VND",
        target_due_at: str = "",
        pricing_notes: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        store = self._store()
        if status not in {"requested", "pricing", "quoted", "won", "lost", "on_hold"}:
            raise ValueError("invalid_quote_status")
        parsed_amount: float | None = None
        if quoted_amount.strip():
            parsed_amount = float(quoted_amount)
        record = store.update_quote_intent(
            quote_intent_id=quote_intent_id,
            customer_account_id=customer_account_id,
            opportunity_id=opportunity_id,
            status=status,
            rfq_reference=rfq_reference,
            quote_reference=quote_reference,
            quoted_amount=parsed_amount,
            currency_code=(currency_code or "VND").upper(),
            target_due_at=target_due_at,
            pricing_notes=pricing_notes,
            notes=notes,
            actor="local_operator",
        )
        company = store.get_company_by_key(record.get("company_key") or "")
        return {"company": company, "quote_intent": record, "storage_counts": store.snapshot_counts()}

    def operator_create_production_handoff(
        self,
        company_id: int,
        quote_intent_id: int | None = None,
        handoff_status: str = "ready_for_production",
        production_reference: str = "",
        requested_ship_at: str = "",
        specification_summary: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        store = self._store()
        company = store.get_company_by_id(company_id)
        if company is None:
            raise LookupError(f"company:{company_id}")
        if handoff_status not in {"ready_for_production", "scheduled", "in_progress", "blocked", "completed"}:
            raise ValueError("invalid_handoff_status")
        record = store.create_production_handoff(
            company_key=company.get("canonical_key") or "",
            quote_intent_id=quote_intent_id,
            handoff_status=handoff_status,
            production_reference=production_reference,
            requested_ship_at=requested_ship_at,
            specification_summary=specification_summary,
            notes=notes,
            actor="local_operator",
        )
        return {"company": company, "production_handoff": record, "storage_counts": store.snapshot_counts()}

    def operator_update_production_handoff(
        self,
        handoff_id: int,
        handoff_status: str,
        production_reference: str | None = None,
        requested_ship_at: str | None = None,
        specification_summary: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        store = self._store()
        if handoff_status not in {"ready_for_production", "scheduled", "in_progress", "blocked", "completed"}:
            raise ValueError("invalid_handoff_status")
        record = store.update_production_handoff(
            handoff_id=handoff_id,
            handoff_status=handoff_status,
            production_reference=production_reference,
            requested_ship_at=requested_ship_at,
            specification_summary=specification_summary,
            notes=notes,
            actor="local_operator",
        )
        company = store.get_company_by_key(record.get("company_key") or "")
        return {"company": company, "production_handoff": record, "storage_counts": store.snapshot_counts()}

    def operator_feedback_status(self, search: str = "", state: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        items = store.list_feedback_status(limit=5000, offset=0)
        companies = {item["canonical_key"]: item for item in store.list_companies(limit=5000, offset=0)}
        search_lower = search.strip().lower()
        filtered: list[dict[str, Any]] = []
        for item in items:
            company = companies.get(item.get("source_key") or "")
            if search_lower:
                haystack = " ".join([str(item.get("source_key") or ""), str(company.get("canonical_name") if company else "")]).lower()
                if search_lower not in haystack:
                    continue
            if state == "routing" and not item.get("routing_outcome"):
                continue
            if state == "qualification" and not item.get("qualification_status"):
                continue
            if state == "commercial" and not (item.get("lead_status") or item.get("crm_linked")):
                continue
            if state == "linkage" and not item.get("partner_linked"):
                continue
            if state == "manual_override" and not (
                item.get("routing_is_manual_override")
                or item.get("qualification_is_manual_override")
                or item.get("commercial_is_manual_override")
            ):
                continue
            filtered.append({**item, "company": company})
        filtered.sort(key=lambda item: item.get("last_event_at") or "", reverse=True)
        return {"items": filtered[offset : offset + limit], "total": len(filtered), "limit": limit, "offset": offset, "search": search, "state": state}

    def operator_feedback_status_detail(self, source_key: str) -> dict[str, Any]:
        store = self._store()
        projection = store.get_feedback_status(source_key)
        if projection is None:
            raise LookupError(f"feedback_status:{source_key}")
        company = next((item for item in store.list_companies(limit=5000, offset=0) if item.get("canonical_key") == source_key), None)
        events = [item for item in store.list_feedback_events(limit=5000, offset=0) if item.get("source_key") == source_key]
        events.sort(key=lambda item: item.get("occurred_at") or "", reverse=True)
        return {"source_key": source_key, "projection": projection, "company": company, "events": events}

    def operator_feedback_events(self, search: str = "", event_type: str = "", limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        companies = {item["canonical_key"]: item for item in store.list_companies(limit=5000, offset=0)}
        search_lower = search.strip().lower()
        items: list[dict[str, Any]] = []
        for event in store.list_feedback_events(limit=5000, offset=0):
            company = companies.get(event.get("source_key") or "")
            if event_type and (event.get("event_type") or "") != event_type:
                continue
            if search_lower:
                haystack = " ".join([
                    str(event.get("event_id") or ""),
                    str(event.get("source_key") or ""),
                    str(event.get("event_type") or ""),
                    str(company.get("canonical_name") if company else ""),
                    str(event.get("reason_code") or ""),
                ]).lower()
                if search_lower not in haystack:
                    continue
            items.append({**event, "company": company})
        items.sort(key=lambda item: item.get("occurred_at") or "", reverse=True)
        return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset, "search": search, "event_type": event_type}

    def operator_scores(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        companies = {item["canonical_key"]: item for item in store.list_companies(limit=5000, offset=0)}
        feedback = {item["source_key"]: item for item in store.list_feedback_status(limit=5000, offset=0)}
        items = []
        for score_row in store.list_scores(limit=5000, offset=0):
            company_key = score_row.get("company_key") or ""
            items.append({**score_row, "company": companies.get(company_key), "feedback": feedback.get(company_key)})
        items.sort(key=lambda item: float(item.get("composite_score") or 0.0), reverse=True)
        return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset}

    def operator_review_queue(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        companies = {item["canonical_key"]: item for item in store.list_companies(limit=5000, offset=0)}
        scores = {item["company_key"]: item for item in store.list_scores(limit=5000, offset=0)}
        items = []
        for queue_item in store.list_review_queue(limit=5000, offset=0):
            company_key = queue_item.get("company_key") or ""
            items.append({**queue_item, "company": companies.get(company_key), "score_detail": scores.get(company_key)})
        items.sort(key=lambda item: (-int(item.get("priority") or 0), -(int(item.get("id") or 0))))
        return {"items": items[offset : offset + limit], "total": len(items), "limit": limit, "offset": offset}

    def operator_raw_records(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        store = self._store()
        companies = store.list_companies(limit=5000, offset=0)
        company_by_source = {item.get("source_fingerprint") or "": item for item in companies if item.get("source_fingerprint")}
        company_by_dedup = {item.get("dedup_fingerprint") or "": item for item in companies if item.get("dedup_fingerprint")}
        rows = []
        for raw in store.list_raw_records(limit=5000, offset=0):
            company = company_by_source.get(raw.get("source_fingerprint") or "") or company_by_dedup.get(raw.get("candidate_dedup_fingerprint") or "")
            rows.append({**raw, "company": company})
        return {"items": rows[offset : offset + limit], "total": len(rows), "limit": limit, "offset": offset}

    def operator_raw_record_detail(self, raw_id: int) -> dict[str, Any]:
        store = self._store()
        companies = store.list_companies(limit=5000, offset=0)
        company_by_source = {item.get("source_fingerprint") or "": item for item in companies if item.get("source_fingerprint")}
        company_by_dedup = {item.get("dedup_fingerprint") or "": item for item in companies if item.get("dedup_fingerprint")}
        raw = next((item for item in store.list_raw_records(limit=5000, offset=0) if int(item.get("id") or 0) == raw_id), None)
        if raw is None:
            raise LookupError(f"raw_record:{raw_id}")
        company = company_by_source.get(raw.get("source_fingerprint") or "") or company_by_dedup.get(raw.get("candidate_dedup_fingerprint") or "")
        return {"raw_record": raw, "company": company}

    def load_sample_feedback(self) -> dict[str, Any]:
        store = self._store()
        companies = store.list_companies(limit=5000, offset=0)
        if not companies:
            raise ValueError("sample_feedback_requires_companies")
        sample_events = [_feedback_event_from_json(item) for item in _sample_feedback_payloads(companies)]
        accepted = store.save_feedback_events(sample_events)
        return {
            "accepted": accepted,
            "generated": len(sample_events),
            "companies_used": min(len(companies), 3),
            "storage_counts": store.snapshot_counts(),
        }

    def operator_workforce(self, case: str = "", company_id: int | None = None, payload_json: str = "") -> dict[str, Any]:
        cases = self._workforce_cases()
        case_keys = list(cases.keys())
        selected_case = case if case in cases else (case_keys[0] if case_keys else "")
        default_payload = ((cases.get(selected_case) or {}).get("input") or {}) if selected_case else {}
        payload_text = payload_json.strip() or json.dumps(default_payload, ensure_ascii=False, indent=2, sort_keys=True)
        try:
            payload = json.loads(payload_text) if payload_text.strip() else {}
        except json.JSONDecodeError as exc:
            raise ValueError("invalid_workforce_payload_json") from exc
        if not isinstance(payload, dict):
            raise ValueError("workforce_payload_must_be_object")

        company = None
        if company_id is not None:
            company = next(
                (item for item in self._store().list_companies(limit=5000, offset=0) if int(item.get("id") or 0) == company_id),
                None,
            )
            if company is None:
                raise LookupError(f"company:{company_id}")

        estimation = self.estimate_workforce(payload) if payload else None
        return {
            "cases": [{"key": key, "label": _labelize(key)} for key in case_keys],
            "selected_case": selected_case,
            "payload_json": payload_text,
            "estimation": estimation,
            "company": company,
            "fixture_path": str(DEFAULT_WORKFORCE_FIXTURE),
        }


def create_wsgi_app(service: SupplierIntelligenceApiService) -> Callable:
    def app(environ: dict[str, Any], start_response: Callable) -> list[bytes]:
        locale_token = _REQUEST_LOCALE.set(_detect_ui_locale(environ))
        method = environ["REQUEST_METHOD"].upper()
        path = environ.get("PATH_INFO", "")
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=False)
        try:
            if method == "GET" and path == "/":
                return _html_response(start_response, 200, _dashboard_page(service.operator_dashboard()))
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
            if method == "POST" and path == "/workforce/estimate":
                body = _parse_json_body(environ)
                return _json_response(start_response, 200, service.estimate_workforce(body))
            if method == "GET" and path == "/ui/raw-records":
                return _html_response(start_response, 200, _raw_records_page(service.operator_raw_records(**_pagination(query))))
            if method == "GET" and path.startswith("/ui/raw-records/"):
                raw_id = int(path.removeprefix("/ui/raw-records/").strip())
                return _html_response(start_response, 200, _raw_record_detail_page(service.operator_raw_record_detail(raw_id)))
            if method == "GET" and path == "/ui/workforce":
                company_id_raw = _query_value(query, "company_id")
                company_id = int(company_id_raw) if company_id_raw else None
                return _html_response(start_response, 200, _workforce_page(service.operator_workforce(
                    case=_query_value(query, "case"),
                    company_id=company_id,
                    payload_json=_query_value(query, "payload_json"),
                )))
            if method == "GET" and path == "/ui/companies":
                return _html_response(start_response, 200, _companies_page(service.operator_companies(
                    search=_query_value(query, "search"),
                    city=_query_value(query, "city"),
                    capability=_query_value(query, "capability"),
                    has_feedback=_query_value(query, "has_feedback"),
                    **_pagination(query),
                )))
            if method == "GET" and path.startswith("/ui/companies/"):
                company_id = int(path.removeprefix("/ui/companies/").strip())
                return _html_response(start_response, 200, _company_detail_page(service.operator_company_detail(company_id)))
            if method == "GET" and path == "/ui/scores":
                return _html_response(start_response, 200, _scores_page(service.operator_scores(**_pagination(query))))
            if method == "GET" and path == "/ui/review-queue":
                return _html_response(start_response, 200, _review_queue_page(service.operator_review_queue(**_pagination(query))))
            if method == "GET" and path == "/ui/commercial-pipeline":
                return _html_response(start_response, 200, _commercial_pipeline_page(service.operator_commercial_pipeline(
                    stage=_query_value(query, "stage"),
                    customer_status=_query_value(query, "customer_status"),
                    **_pagination(query),
                )))
            if method == "GET" and path == "/ui/opportunities":
                return _html_response(start_response, 200, _opportunities_page(service.operator_opportunities(
                    status=_query_value(query, "status"),
                    company_id=_optional_int(_query_value(query, "company_id")),
                    **_pagination(query),
                )))
            if method == "GET" and path.startswith("/ui/opportunities/"):
                opportunity_id = int(path.removeprefix("/ui/opportunities/").strip())
                return _html_response(start_response, 200, _opportunity_detail_page(service.operator_opportunity_detail(opportunity_id)))
            if method == "GET" and path == "/ui/quote-intents":
                return _html_response(start_response, 200, _quote_pipeline_page(service.operator_quote_pipeline(
                    status=_query_value(query, "status"),
                    quote_type=_query_value(query, "quote_type"),
                    **_pagination(query),
                )))
            if method == "GET" and path.startswith("/ui/quote-intents/"):
                quote_intent_id = int(path.removeprefix("/ui/quote-intents/").strip())
                return _html_response(start_response, 200, _quote_intent_detail_page(service.operator_quote_intent_detail(quote_intent_id)))
            if method == "GET" and path == "/ui/production-handoffs":
                return _html_response(start_response, 200, _production_handoff_page(service.operator_production_handoffs(
                    status=_query_value(query, "status"),
                    **_pagination(query),
                )))
            if method == "GET" and path == "/ui/production-board":
                return _html_response(start_response, 200, _production_board_page(service.operator_production_board()))
            if method == "GET" and path.startswith("/ui/production-handoffs/"):
                handoff_id = int(path.removeprefix("/ui/production-handoffs/").strip())
                return _html_response(start_response, 200, _production_handoff_detail_page(service.operator_production_handoff_detail(handoff_id)))
            if method == "GET" and path == "/ui/feedback-status":
                return _html_response(start_response, 200, _feedback_status_page(service.operator_feedback_status(
                    search=_query_value(query, "search"),
                    state=_query_value(query, "state"),
                    **_pagination(query),
                )))
            if method == "GET" and path.startswith("/ui/feedback-status/"):
                source_key = unquote(path.removeprefix("/ui/feedback-status/").strip())
                if not source_key:
                    raise ValueError("feedback_status_source_key_required")
                return _html_response(start_response, 200, _feedback_status_detail_page(service.operator_feedback_status_detail(source_key)))
            if method == "GET" and path == "/ui/feedback-events":
                return _html_response(start_response, 200, _feedback_events_page(service.operator_feedback_events(
                    search=_query_value(query, "search"),
                    event_type=_query_value(query, "event_type"),
                    **_pagination(query),
                )))
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
            if method == "POST" and path == "/ui/actions/run-pipeline":
                form = _parse_form_body(environ)
                result = service.run_pipeline(
                    query=form.get("query") or service.default_query,
                    country=form.get("country") or service.default_country,
                    fixture=form.get("fixture") or str(DEFAULT_UI_FIXTURE),
                )
                return _html_response(start_response, 200, _run_result_page(result))
            if method == "POST" and path == "/ui/actions/load-sample-feedback":
                result = service.load_sample_feedback()
                return _html_response(start_response, 200, _sample_feedback_result_page(result))
            if method == "POST" and path == "/ui/actions/workforce-estimate":
                form = _parse_form_body(environ)
                company_id_raw = form.get("company_id") or ""
                company_id = int(company_id_raw) if company_id_raw else None
                return _html_response(start_response, 200, _workforce_page(service.operator_workforce(
                    case=form.get("case") or "",
                    company_id=company_id,
                    payload_json=form.get("payload_json") or "",
                )))
            if method == "POST" and path.startswith("/ui/actions/companies/") and path.endswith("/decide"):
                company_id = int(path.removeprefix("/ui/actions/companies/").removesuffix("/decide").strip())
                form = _parse_form_body(environ)
                result = service.operator_apply_decision(
                    company_id=company_id,
                    outcome=form.get("outcome") or "needs_manual_review",
                    reason_code=form.get("reason_code") or "",
                    notes=form.get("notes") or "",
                    manual_override=(form.get("manual_override") or "yes") != "no",
                )
                return _html_response(start_response, 200, _decision_result_page(result))
            if method == "POST" and path.startswith("/ui/actions/companies/") and path.endswith("/commercial"):
                company_id = int(path.removeprefix("/ui/actions/companies/").removesuffix("/commercial").strip())
                form = _parse_form_body(environ)
                result = service.operator_update_commercial(
                    company_id=company_id,
                    customer_status=form.get("customer_status") or "prospect",
                    commercial_stage=form.get("commercial_stage") or "new_lead",
                    customer_reference=form.get("customer_reference") or "",
                    opportunity_reference=form.get("opportunity_reference") or "",
                    next_action=form.get("next_action") or "",
                    next_action_due_at=form.get("next_action_due_at") or "",
                    notes=form.get("notes") or "",
                )
                return _html_response(start_response, 200, _commercial_result_page(result))
            if method == "POST" and path.startswith("/ui/actions/companies/") and path.endswith("/customer-account"):
                company_id = int(path.removeprefix("/ui/actions/companies/").removesuffix("/customer-account").strip())
                form = _parse_form_body(environ)
                result = service.operator_upsert_customer_account(
                    company_id=company_id,
                    account_name=form.get("account_name") or "",
                    account_type=form.get("account_type") or "direct_customer",
                    account_status=form.get("account_status") or "prospect",
                    primary_contact_name=form.get("primary_contact_name") or "",
                    primary_email=form.get("primary_email") or "",
                    primary_phone=form.get("primary_phone") or "",
                    billing_city=form.get("billing_city") or "",
                    external_customer_ref=form.get("external_customer_ref") or "",
                    odoo_partner_ref=form.get("odoo_partner_ref") or "",
                    notes=form.get("notes") or "",
                )
                return _html_response(start_response, 200, _customer_account_result_page(result))
            if method == "POST" and path.startswith("/ui/actions/companies/") and path.endswith("/opportunities"):
                company_id = int(path.removeprefix("/ui/actions/companies/").removesuffix("/opportunities").strip())
                form = _parse_form_body(environ)
                result = service.operator_create_opportunity(
                    company_id=company_id,
                    customer_account_id=_optional_int(form.get("customer_account_id")),
                    title=form.get("title") or "",
                    status=form.get("status") or "new",
                    source_channel=form.get("source_channel") or "",
                    estimated_value=form.get("estimated_value") or "",
                    currency_code=form.get("currency_code") or "VND",
                    target_due_at=form.get("target_due_at") or "",
                    next_action=form.get("next_action") or "",
                    notes=form.get("notes") or "",
                    external_opportunity_ref=form.get("external_opportunity_ref") or "",
                    odoo_lead_ref=form.get("odoo_lead_ref") or "",
                )
                return _html_response(start_response, 200, _opportunity_result_page(result))
            if method == "POST" and path.startswith("/ui/actions/opportunities/"):
                opportunity_id = int(path.removeprefix("/ui/actions/opportunities/").strip())
                form = _parse_form_body(environ)
                result = service.operator_update_opportunity(
                    opportunity_id=opportunity_id,
                    customer_account_id=_optional_int(form.get("customer_account_id")),
                    title=form.get("title") or "",
                    status=form.get("status") or "new",
                    source_channel=form.get("source_channel") or "",
                    estimated_value=form.get("estimated_value") or "",
                    currency_code=form.get("currency_code") or "VND",
                    target_due_at=form.get("target_due_at") or "",
                    next_action=form.get("next_action") or "",
                    notes=form.get("notes") or "",
                    external_opportunity_ref=form.get("external_opportunity_ref") or "",
                    odoo_lead_ref=form.get("odoo_lead_ref") or "",
                )
                return _html_response(start_response, 200, _opportunity_result_page(result, updated=True))
            if method == "POST" and path.startswith("/ui/actions/companies/") and path.endswith("/quote-intents"):
                company_id = int(path.removeprefix("/ui/actions/companies/").removesuffix("/quote-intents").strip())
                form = _parse_form_body(environ)
                result = service.operator_create_quote_intent(
                    company_id=company_id,
                    customer_account_id=_optional_int(form.get("customer_account_id")),
                    opportunity_id=_optional_int(form.get("opportunity_id")),
                    quote_type=form.get("quote_type") or "service_quote",
                    quantity_hint=form.get("quantity_hint") or "",
                    target_due_at=form.get("target_due_at") or "",
                    status=form.get("status") or "requested",
                    rfq_reference=form.get("rfq_reference") or "",
                    notes=form.get("notes") or "",
                )
                return _html_response(start_response, 200, _quote_intent_result_page(result))
            if method == "POST" and path.startswith("/ui/actions/quote-intents/"):
                quote_intent_id = int(path.removeprefix("/ui/actions/quote-intents/").strip())
                form = _parse_form_body(environ)
                result = service.operator_update_quote_intent(
                    quote_intent_id=quote_intent_id,
                    customer_account_id=_optional_int(form.get("customer_account_id")),
                    opportunity_id=_optional_int(form.get("opportunity_id")),
                    status=form.get("status") or "requested",
                    rfq_reference=form.get("rfq_reference") or "",
                    quote_reference=form.get("quote_reference") or "",
                    quoted_amount=form.get("quoted_amount") or "",
                    currency_code=form.get("currency_code") or "VND",
                    target_due_at=form.get("target_due_at") or "",
                    pricing_notes=form.get("pricing_notes") or "",
                    notes=form.get("notes") or "",
                )
                return _html_response(start_response, 200, _quote_intent_result_page(result, updated=True))
            if method == "POST" and path.startswith("/ui/actions/companies/") and path.endswith("/production-handoffs"):
                company_id = int(path.removeprefix("/ui/actions/companies/").removesuffix("/production-handoffs").strip())
                form = _parse_form_body(environ)
                quote_intent_raw = form.get("quote_intent_id") or ""
                result = service.operator_create_production_handoff(
                    company_id=company_id,
                    quote_intent_id=int(quote_intent_raw) if quote_intent_raw else None,
                    handoff_status=form.get("handoff_status") or "ready_for_production",
                    production_reference=form.get("production_reference") or "",
                    requested_ship_at=form.get("requested_ship_at") or "",
                    specification_summary=form.get("specification_summary") or "",
                    notes=form.get("notes") or "",
                )
                return _html_response(start_response, 200, _production_handoff_result_page(result))
            if method == "POST" and path.startswith("/ui/actions/production-handoffs/"):
                handoff_id = int(path.removeprefix("/ui/actions/production-handoffs/").strip())
                form = _parse_form_body(environ)
                result = service.operator_update_production_handoff(
                    handoff_id=handoff_id,
                    handoff_status=form.get("handoff_status") or "ready_for_production",
                    production_reference=form.get("production_reference"),
                    requested_ship_at=form.get("requested_ship_at"),
                    specification_summary=form.get("specification_summary"),
                    notes=form.get("notes"),
                )
                return _html_response(start_response, 200, _production_handoff_result_page(result, updated=True))
            if method == "POST" and path.startswith("/ui/actions/queue/") and path.endswith("/transition"):
                queue_id = int(path.removeprefix("/ui/actions/queue/").removesuffix("/transition").strip())
                form = _parse_form_body(environ)
                result = service.operator_transition_queue(
                    queue_id=queue_id,
                    target_status=form.get("target_status") or "in_progress",
                    reason_code=form.get("reason_code") or "manual_transition",
                    notes=form.get("notes") or "",
                    allow_reprocess=(form.get("allow_reprocess") or "") == "yes",
                )
                return _html_response(start_response, 200, _queue_transition_result_page(result))
            if path in {"/runs", "/feedback-events", "/feedback-status", "/workforce/estimate"} or path.startswith("/feedback-status/"):
                return _json_response(start_response, 405, {"error": "method_not_allowed"})
            return _json_response(start_response, 404, {"error": "not_found", "path": path})
        except ValueError as exc:
            return _json_response(start_response, 400, {"error": "bad_request", "detail": str(exc)})
        except LookupError as exc:
            return _json_response(start_response, 404, {"error": "not_found", "detail": str(exc)})
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("magon_standalone.request_failed path=%s", path)
            return _json_response(start_response, 500, {"error": "internal_error", "detail": str(exc)})
        finally:
            _REQUEST_LOCALE.reset(locale_token)

    return app


class QuietRequestHandler(WSGIRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        LOGGER.info("magon_standalone.http " + format, *args)


class SupplierIntelligenceApiServer:
    def __init__(self, service: SupplierIntelligenceApiService, host: str = "127.0.0.1", port: int = 8091):
        self.service = service
        self.host = host
        self.port = port
        # RU: Даже локальный simple-server должен идти через observability wrapper, чтобы perf/error capture не существовал только в deploy-режиме.
        self._server = make_server(host, port, wrap_wsgi_app(create_wsgi_app(service)), handler_class=QuietRequestHandler)
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


def _dashboard_page(data: dict[str, Any]) -> str:
    counts = data["counts"]
    cards = [
        _stat_card("Raw records", counts["raw_records"], "Source discovery rows persisted in standalone storage."),
        _stat_card("Canonical companies", counts["canonical_companies"], "Deduplicated supplier/company intelligence owned by standalone."),
        _stat_card("Scored companies", counts["vendor_scores"], "Companies with composite scoring ready for review routing."),
        _stat_card("Review queue", counts["review_queue"], "Items currently queued for operator review."),
        _stat_card("Feedback events", counts["feedback_events"], "Downstream feedback ledger entries stored separately from intelligence."),
        _stat_card("Companies with feedback", data["companies_with_feedback"], "Canonical companies that already have downstream outcome projection."),
        _stat_card("Routing feedback", data["routing_feedback"], "Companies that already have a routing outcome projection."),
        _stat_card("Synthetic feedback", data["synthetic_feedback_events_count"], "Local sample/test feedback currently visible in the console."),
    ]
    quick_links = "".join(
        [
            _nav_card("Companies", "/ui/companies", "Open the company workbench and inspect one supplier end-to-end."),
            _nav_card("Commercial pipeline", "/ui/commercial-pipeline", "Track standalone-owned commercial follow-up instead of hiding it in Odoo lead state."),
            _nav_card("Quote intents", "/ui/quote-intents", "Track RFQ / quote requests in standalone instead of deferring everything to ERP."),
            _nav_card("Production handoffs", "/ui/production-handoffs", "Track execution handoff in standalone instead of pushing everything into ERP orders."),
            _nav_card("Production board", "/ui/production-board", "Move active jobs across execution states with a simple operator board."),
            _nav_card("Review queue", "/ui/review-queue", "See what is waiting for operator review and why."),
            _nav_card("Feedback status", "/ui/feedback-status", "Inspect downstream commercial/routing/qualification outcomes without mutating intelligence."),
            _nav_card("Feedback audit", "/ui/feedback-events", "Read the feedback ledger itself when you need traceability."),
            _nav_card("Workforce planner", "/ui/workforce", "Run labor/headcount estimation without touching company intelligence state."),
            _nav_card("Raw records", "/ui/raw-records", "Inspect raw discovery evidence and its company correlation."),
            _nav_card("Scores", "/ui/scores", "See computed supplier scores and jump straight into a company workbench."),
        ]
    )

    recent_company_rows: list[str] = []
    for item in data.get("recent_companies", []):
        company = item.get("company") or {}
        company_id = int(company.get("id") or 0)
        queue_badges = " ".join(
            _badge(_labelize(queue.get("queue_name") or "review"), _queue_tone(queue.get("queue_name") or ""))
            for queue in (item.get("queue_items") or [])
        )
        if not queue_badges:
            queue_badges = '<span class="muted">No queue</span>'
        recent_company_rows.append(
            (
                f'<tr><td><a class="strong-link" href="/ui/companies/{company_id}">{html.escape(company.get("canonical_name") or company.get("legal_name") or "Company")}</a>'
                f'<div class="muted small">{html.escape(company.get("canonical_key") or "")}</div></td>'
                f'<td>{html.escape(company.get("city") or "—")}</td>'
                f'<td>{_score_badge((item.get("score") or {}).get("composite_score"))}</td>'
                f'<td>{queue_badges}</td>'
                f'<td>{_feedback_summary_badges(item.get("feedback"))}</td></tr>'
            )
        )
    recent_companies_body = ''.join(recent_company_rows)
    if not recent_companies_body:
        recent_companies_body = '<tr><td colspan="5" class="muted">No companies yet.</td></tr>'
    recent_companies_table = (
        '<table><thead><tr><th>Company</th><th>City</th><th>Score</th><th>Queue</th><th>Feedback</th></tr></thead>'
        f'<tbody>{recent_companies_body}</tbody></table>'
    )

    recent_feedback_rows: list[str] = []
    for item in data.get("recent_feedback", []):
        event = item.get("event") or {}
        company = item.get("company") or {}
        company_cell = '<span class="muted">Unmatched</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{int(company.get("id") or 0)}">{html.escape(company.get("canonical_name") or "Company")}</a>'
        synthetic = _synthetic_badge() if event.get("is_synthetic") else ''
        recent_feedback_rows.append(
            (
                f'<tr><td>{company_cell}</td>'
                f'<td>{_badge(_labelize(event.get("event_type") or "feedback"), "accent")} {synthetic}</td>'
                f'<td>{_feedback_event_outcome_summary(event)}</td>'
                f'<td><a class="strong-link" href="{html.escape(item.get("timeline_href") or "/ui/feedback-status")}">Open timeline</a></td></tr>'
            )
        )
    recent_feedback_body = ''.join(recent_feedback_rows)
    if not recent_feedback_body:
        recent_feedback_body = '<tr><td colspan="4" class="muted">No feedback events yet.</td></tr>'
    recent_feedback_table = (
        '<table><thead><tr><th>Company</th><th>Event</th><th>Outcome summary</th><th>Action</th></tr></thead>'
        f'<tbody>{recent_feedback_body}</tbody></table>'
    )

    synthetic_notice = ''
    if data.get("synthetic_feedback_events_count"):
        synthetic_notice = (
            '<section class="panel"><div class="split"><div>'
            '<h2>Synthetic sample feedback is present</h2>'
            '<p class="muted">These rows are local test data seeded from the operator panel. They are clearly labeled and separate from standalone intelligence.</p>'
            f'</div><div>{_synthetic_badge()}</div></div></section>'
        )

    body = f"""
    <section class="hero">
      <div>
        <p class="eyebrow">Standalone operator panel</p>
        <h1>Supplier intelligence console</h1>
        <p class="lead">Use the company workbench as the main operator surface. Standalone intelligence stays authoritative. Downstream commercial/Odoo-derived outcomes are shown separately as feedback.</p>
      </div>
      <div class="panel panel-tight">
        <h2>Local operator actions</h2>
        <form method="post" action="/ui/actions/run-pipeline" class="stack">
          <label>Fixture path<input type="text" name="fixture" value="{html.escape(data['fixture_path'])}"></label>
          <label>Query<input type="text" name="query" value="printing packaging vietnam"></label>
          <label>Country<input type="text" name="country" value="VN"></label>
          <button type="submit">Run local fixture pipeline</button>
        </form>
        <form method="post" action="/ui/actions/load-sample-feedback" class="stack">
          <p class="muted small">Seed narrow synthetic downstream feedback so the company workbench and feedback screens are inspectable without external integrations.</p>
          <button type="submit">Load sample feedback</button>
        </form>
      </div>
    </section>
    <section class="cards">{''.join(cards)}</section>
    {synthetic_notice}
    <section class="grid two">
      <div class="panel"><h2>Quick navigation</h2><div class="cards compact">{quick_links}</div></div>
      <div class="panel"><h2>Recent companies</h2>{recent_companies_table}</div>
    </section>
    <section class="panel"><h2>Recent downstream feedback</h2>{recent_feedback_table}</section>
    """
    return _layout("Dashboard", body, active="dashboard")


def _companies_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        score = item.get("score") or {}
        feedback = item.get("feedback")
        queue_items = item.get("queue_items") or []
        city = item.get("city") or "—"
        contact = " / ".join(part for part in [item.get("canonical_email") or "", item.get("canonical_phone") or ""] if part) or "—"
        website = item.get("website") or "—"
        capabilities = _chips(item.get("capabilities") or [], tone="neutral") or '<span class="muted">No capabilities</span>'
        queue_summary = " ".join(_badge(_labelize(queue.get("queue_name") or "review"), _queue_tone(queue.get("queue_name") or "")) for queue in queue_items) or '<span class="muted">No queue</span>'
        feedback_summary = _feedback_summary_badges(feedback)
        rows.append(
            f"<tr>"
            f"<td><a class=\"strong-link\" href=\"/ui/companies/{item['id']}\">{html.escape(item.get('canonical_name') or 'Company')}</a><div class=\"muted small\">{html.escape(item.get('legal_name') or '')}</div></td>"
            f"<td>{html.escape(city)}</td>"
            f"<td>{capabilities}</td>"
            f"<td>{html.escape(contact)}</td>"
            f"<td>{_truncate(website, 32)}</td>"
            f"<td>{_score_badge(score.get('composite_score'))}</td>"
            f"<td>{queue_summary}</td>"
            f"<td>{feedback_summary}</td>"
            f"</tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan=8 class="muted">No companies match the current filters.</td></tr>'
    table = f"<table><thead><tr><th>Company</th><th>City</th><th>Capabilities</th><th>Contact</th><th>Website</th><th>Score</th><th>Queue</th><th>Feedback</th></tr></thead><tbody>{body_rows}</tbody></table>"
    filters = f"""
    <form method=\"get\" action=\"/ui/companies\" class=\"toolbar\">
      <input type=\"text\" name=\"search\" value=\"{html.escape(data['search'])}\" placeholder=\"Search company, site, contact, capability\">
      <select name=\"city\">{_options('All cities', data['city_options'], data['city'])}</select>
      <select name=\"capability\">{_options('All capabilities', data['capability_options'], data['capability'])}</select>
      <select name=\"has_feedback\">{_simple_options([('','All feedback states'),('yes','Has feedback'),('no','No feedback')], data['has_feedback'])}</select>
      <select name=\"limit\">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type=\"submit\">Apply</button>
    </form>
    """
    body = f"""
    <section class=\"hero compact\"><div><p class=\"eyebrow\">Companies</p><h1>Canonical supplier intelligence</h1><p class=\"lead\">Browse standalone-owned supplier/company intelligence with score, queue, and feedback context.</p></div><div class=\"panel panel-tight\"><strong>{data['total']}</strong><span class=\"muted\">matching companies</span></div></section>
    <section class=\"panel\">{filters}{table}</section>
    """
    return _layout("Companies", body, active="companies")


def _company_detail_page(data: dict[str, Any]) -> str:
    company = data["company"]
    score = data.get("score")
    vendor_profile = data.get("vendor_profile")
    queue_items = data.get("queue_items") or []
    qualification_decisions = data.get("qualification_decisions") or []
    routing_audit = data.get("routing_audit") or []
    commercial_record = data.get("commercial_record")
    customer_account = data.get("customer_account")
    opportunities = data.get("opportunities") or []
    quote_intents = data.get("quote_intents") or []
    production_handoffs = data.get("production_handoffs") or []
    commercial_audit = data.get("commercial_audit") or []
    feedback_projection = data.get("feedback_projection")
    feedback_events = data.get("feedback_events") or []
    raw_records = data.get("raw_records") or []
    source_key = company.get("canonical_key") or ""

    company_capabilities = _chips(company.get('capabilities') or [], tone='neutral') or '<span class="muted">No capabilities</span>'
    company_provenance = '<br>'.join(_external_link(item) for item in company.get('provenance') or []) or '—'
    company_overview = f"""
    <div class="detail-grid">
      <div><span class="field-label">Canonical name</span><div class="field-value">{html.escape(company.get('canonical_name') or '—')}</div></div>
      <div><span class="field-label">Canonical key</span><div class="field-value mono">{html.escape(company.get('canonical_key') or '—')}</div></div>
      <div><span class="field-label">City</span><div class="field-value">{html.escape(company.get('city') or '—')}</div></div>
      <div><span class="field-label">Address</span><div class="field-value">{html.escape(company.get('address_text') or '—')}</div></div>
      <div><span class="field-label">Email</span><div class="field-value">{html.escape(company.get('canonical_email') or '—')}</div></div>
      <div><span class="field-label">Phone</span><div class="field-value">{html.escape(company.get('canonical_phone') or '—')}</div></div>
      <div><span class="field-label">Website</span><div class="field-value">{_external_link(company.get('website'))}</div></div>
      <div><span class="field-label">Capabilities</span><div class="field-value">{company_capabilities}</div></div>
    </div>
    """
    intelligence_summary = f"""
    <div class="detail-grid">
      <div><span class="field-label">Review status</span><div class="field-value">{_badge(_labelize(company.get('review_status') or 'new'), 'neutral')}</div></div>
      <div><span class="field-label">Confidence</span><div class="field-value">{_score_badge(company.get('confidence'))}</div></div>
      <div><span class="field-label">Parser confidence</span><div class="field-value">{_score_badge(company.get('parser_confidence'))}</div></div>
      <div><span class="field-label">Source confidence</span><div class="field-value">{_score_badge(company.get('source_confidence'))}</div></div>
      <div><span class="field-label">Source fingerprint</span><div class="field-value mono">{html.escape(company.get('source_fingerprint') or '—')}</div></div>
      <div><span class="field-label">Dedup fingerprint</span><div class="field-value mono">{html.escape(company.get('dedup_fingerprint') or '—')}</div></div>
      <div class="span-2"><span class="field-label">Provenance</span><div class="field-value">{company_provenance}</div></div>
    </div>
    """

    score_block = '<div class="empty">No score stored yet for this company.</div>'
    if score:
        score_cards = [
            _stat_card('Composite', f"{float(score.get('composite_score') or 0.0):.2f}", 'Overall standalone score.'),
            _stat_card('Relevance', f"{float(score.get('relevance_score') or 0.0):.2f}", 'Demand / query fit.'),
            _stat_card('Capability fit', f"{float(score.get('capability_fit_score') or 0.0):.2f}", 'Capability coverage.'),
            _stat_card('Contactability', f"{float(score.get('contactability_score') or 0.0):.2f}", 'Reachability signal.'),
            _stat_card('Freshness', f"{float(score.get('freshness_score') or 0.0):.2f}", 'Recency / freshness.'),
            _stat_card('Trust', f"{float(score.get('trust_score') or 0.0):.2f}", 'Source trust and consistency.'),
        ]
        score_block = f'<div class="cards compact metrics">{"".join(score_cards)}</div>'

    workflow_block = '<div class="empty">No standalone workflow state yet. Run the pipeline first so standalone can create a vendor workflow profile.</div>'
    if vendor_profile:
        workflow_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Review status</span><div class="field-value">{_badge(_labelize(vendor_profile.get('review_status') or 'new'), 'neutral')}</div></div>
          <div><span class="field-label">Qualification status</span><div class="field-value">{_badge(_labelize(vendor_profile.get('qualification_status') or 'unqualified'), 'neutral')}</div></div>
          <div><span class="field-label">Lifecycle state</span><div class="field-value">{_badge(_labelize(vendor_profile.get('lifecycle_state') or 'new'), 'info')}</div></div>
          <div><span class="field-label">Routing state</span><div class="field-value">{_feedback_badge(vendor_profile.get('routing_state'))}</div></div>
          <div><span class="field-label">Outreach ready</span><div class="field-value">{_bool_badge(bool(vendor_profile.get('outreach_ready')), 'Ready', 'Not ready')}</div></div>
          <div><span class="field-label">RFQ ready</span><div class="field-value">{_bool_badge(bool(vendor_profile.get('rfq_ready')), 'Ready', 'Not ready')}</div></div>
          <div class="span-2"><span class="field-label">Operator notes</span><div class="field-value">{html.escape(vendor_profile.get('notes') or '—')}</div></div>
        </div>
        """

    commercial_block = '<div class="empty">No standalone commercial state yet. Create it here instead of treating downstream Odoo feedback as your editable source of truth.</div>'
    commercial_form = f"""
    <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0)}/commercial" class="stack">
      <label>Customer status
        <select name="customer_status">
          {_simple_options([
            ('prospect', 'Prospect'),
            ('active_customer', 'Active customer'),
            ('dormant', 'Dormant'),
            ('blocked', 'Blocked'),
          ], str((commercial_record or {}).get('customer_status') or 'prospect'))}
        </select>
      </label>
      <label>Commercial stage
        <select name="commercial_stage">
          {_simple_options([
            ('new_lead', 'New lead'),
            ('contacting', 'Contacting'),
            ('qualified', 'Qualified'),
            ('rfq_requested', 'RFQ requested'),
            ('quoted', 'Quoted'),
            ('won', 'Won'),
            ('lost', 'Lost'),
            ('on_hold', 'On hold'),
          ], str((commercial_record or {}).get('commercial_stage') or 'new_lead'))}
        </select>
      </label>
      <label>Customer reference<input type="text" name="customer_reference" value="{html.escape((commercial_record or {}).get('customer_reference') or '')}"></label>
      <label>Opportunity reference<input type="text" name="opportunity_reference" value="{html.escape((commercial_record or {}).get('opportunity_reference') or '')}"></label>
      <label>Next action<input type="text" name="next_action" value="{html.escape((commercial_record or {}).get('next_action') or '')}"></label>
      <label>Next action due at<input type="text" name="next_action_due_at" value="{html.escape((commercial_record or {}).get('next_action_due_at') or '')}" placeholder="2026-04-20"></label>
      <label>Notes<input type="text" name="notes" value="{html.escape((commercial_record or {}).get('notes') or '')}"></label>
      <button type="submit">Save standalone commercial state</button>
    </form>
    """
    if commercial_record:
        commercial_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Customer status</span><div class="field-value">{_badge(_labelize(commercial_record.get('customer_status') or 'prospect'), 'neutral')}</div></div>
          <div><span class="field-label">Commercial stage</span><div class="field-value">{_badge(_labelize(commercial_record.get('commercial_stage') or 'new_lead'), 'accent')}</div></div>
          <div><span class="field-label">Customer ref</span><div class="field-value mono">{html.escape(commercial_record.get('customer_reference') or '—')}</div></div>
          <div><span class="field-label">Opportunity ref</span><div class="field-value mono">{html.escape(commercial_record.get('opportunity_reference') or '—')}</div></div>
          <div><span class="field-label">Next action</span><div class="field-value">{html.escape(commercial_record.get('next_action') or '—')}</div></div>
          <div><span class="field-label">Next action due</span><div class="field-value">{html.escape(commercial_record.get('next_action_due_at') or '—')}</div></div>
          <div class="span-2"><span class="field-label">Notes</span><div class="field-value">{html.escape(commercial_record.get('notes') or '—')}</div></div>
        </div>
        """

    customer_account_block = '<div class="empty">No standalone customer account yet. Create the minimum account owner here instead of relying on Odoo partner ownership for this contour.</div>'
    if customer_account:
        customer_account_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Account name</span><div class="field-value">{html.escape(customer_account.get('account_name') or '—')}</div></div>
          <div><span class="field-label">Account status</span><div class="field-value">{_badge(_labelize(customer_account.get('account_status') or 'prospect'), 'neutral')}</div></div>
          <div><span class="field-label">Account type</span><div class="field-value">{_badge(_labelize(customer_account.get('account_type') or 'direct_customer'), 'info')}</div></div>
          <div><span class="field-label">External ref</span><div class="field-value mono">{html.escape(customer_account.get('external_customer_ref') or '—')}</div></div>
          <div><span class="field-label">Primary contact</span><div class="field-value">{html.escape(customer_account.get('primary_contact_name') or '—')}</div></div>
          <div><span class="field-label">Primary email</span><div class="field-value">{html.escape(customer_account.get('primary_email') or '—')}</div></div>
          <div><span class="field-label">Primary phone</span><div class="field-value">{html.escape(customer_account.get('primary_phone') or '—')}</div></div>
          <div><span class="field-label">Billing city</span><div class="field-value">{html.escape(customer_account.get('billing_city') or '—')}</div></div>
          <div class="span-2"><span class="field-label">Notes</span><div class="field-value">{html.escape(customer_account.get('notes') or '—')}</div></div>
        </div>
        """
    customer_account_form = f"""
    <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0)}/customer-account" class="stack">
      <label>Account name<input type="text" name="account_name" value="{html.escape((customer_account or {}).get('account_name') or company.get('canonical_name') or '')}"></label>
      <label>Account type<select name="account_type">{_simple_options([('direct_customer', 'Direct customer'), ('agency', 'Agency'), ('reseller', 'Reseller'), ('internal', 'Internal account')], str((customer_account or {}).get('account_type') or 'direct_customer'))}</select></label>
      <label>Account status<select name="account_status">{_simple_options([('prospect', 'Prospect'), ('active', 'Active'), ('inactive', 'Inactive'), ('blocked', 'Blocked')], str((customer_account or {}).get('account_status') or 'prospect'))}</select></label>
      <label>Primary contact<input type="text" name="primary_contact_name" value="{html.escape((customer_account or {}).get('primary_contact_name') or '')}"></label>
      <label>Primary email<input type="text" name="primary_email" value="{html.escape((customer_account or {}).get('primary_email') or company.get('canonical_email') or '')}"></label>
      <label>Primary phone<input type="text" name="primary_phone" value="{html.escape((customer_account or {}).get('primary_phone') or company.get('canonical_phone') or '')}"></label>
      <label>Billing city<input type="text" name="billing_city" value="{html.escape((customer_account or {}).get('billing_city') or company.get('city') or '')}"></label>
      <label>External customer ref<input type="text" name="external_customer_ref" value="{html.escape((customer_account or {}).get('external_customer_ref') or '')}"></label>
      <label>Trace Odoo partner ref (optional)<input type="text" name="odoo_partner_ref" value="{html.escape((customer_account or {}).get('odoo_partner_ref') or '')}"></label>
      <label>Notes<input type="text" name="notes" value="{html.escape((customer_account or {}).get('notes') or '')}"></label>
      <button type="submit">Save customer account</button>
    </form>
    """

    account_option_pairs = [("", "No linked account")]
    if customer_account:
        account_option_pairs.append((str(int(customer_account.get("id") or 0)), customer_account.get("account_name") or "Primary account"))

    opportunity_form = f"""
    <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0)}/opportunities" class="stack">
      <label>Title<input type="text" name="title" value="" placeholder="Packaging follow-up for key buyer"></label>
      <label>Status<select name="status">{_simple_options([('new', 'New'), ('contacting', 'Contacting'), ('qualified', 'Qualified'), ('rfq_requested', 'RFQ requested'), ('quoted', 'Quoted'), ('won', 'Won'), ('lost', 'Lost'), ('on_hold', 'On hold')], 'new')}</select></label>
      <label>Customer account<select name="customer_account_id">{_simple_options(account_option_pairs, str(int(customer_account.get('id') or 0)) if customer_account else '')}</select></label>
      <label>Source channel<input type="text" name="source_channel" value="" placeholder="manual, inbound_form, referral"></label>
      <label>Estimated value<input type="text" name="estimated_value" value="" placeholder="12500000"></label>
      <label>Currency<input type="text" name="currency_code" value="VND"></label>
      <label>Target due date<input type="text" name="target_due_at" value="" placeholder="2026-04-25"></label>
      <label>Next action<input type="text" name="next_action" value="" placeholder="Send spec request"></label>
      <label>External opportunity ref<input type="text" name="external_opportunity_ref" value=""></label>
      <label>Trace Odoo lead ref (optional)<input type="text" name="odoo_lead_ref" value=""></label>
      <label>Notes<input type="text" name="notes" value=""></label>
      <button type="submit">Create opportunity</button>
    </form>
    """
    opportunities_block = '<div class="empty">No standalone opportunities yet. Create a commercial owner record here instead of relying on Odoo lead state.</div>'
    if opportunities:
        opportunity_rows = ''.join(
            f"<tr><td><a class=\"strong-link\" href=\"/ui/opportunities/{int(item.get('id') or 0)}\">{html.escape(item.get('title') or 'Opportunity')}</a></td><td>{_badge(_labelize(item.get('status') or 'new'), 'accent')}</td><td>{html.escape(item.get('source_channel') or '—')}</td><td>{_money(item.get('estimated_value'), item.get('currency_code') or 'VND')}</td><td>{html.escape(item.get('target_due_at') or '—')}</td><td>{html.escape(item.get('next_action') or '—')}</td></tr>"
            for item in opportunities
        )
        opportunities_block = f"<table><thead><tr><th>Opportunity</th><th>Status</th><th>Source</th><th>Value</th><th>Target due</th><th>Next action</th></tr></thead><tbody>{opportunity_rows}</tbody></table>"

    opportunity_option_pairs = [("", "No linked opportunity")] + [
        (str(int(item.get("id") or 0)), f"#{int(item.get('id') or 0)} {item.get('title') or 'Opportunity'}")
        for item in opportunities
    ]
    quote_form = f"""
    <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0)}/quote-intents" class="stack">
      <label>Customer account<select name="customer_account_id">{_simple_options(account_option_pairs, str(int(customer_account.get('id') or 0)) if customer_account else '')}</select></label>
      <label>Opportunity<select name="opportunity_id">{_simple_options(opportunity_option_pairs, '')}</select></label>
      <label>Quote / RFQ type
        <select name="quote_type">
          {_simple_options([
            ('service_quote', 'Service quote'),
            ('rfq_packaging', 'RFQ packaging'),
            ('rfq_labels', 'RFQ labels'),
            ('rfq_printing', 'RFQ printing'),
            ('sample_request', 'Sample request'),
          ], 'service_quote')}
        </select>
      </label>
      <label>RFQ reference<input type="text" name="rfq_reference" value="" placeholder="ZAPR-2026-001"></label>
      <label>Quantity hint<input type="text" name="quantity_hint" value="" placeholder="e.g. 5,000 boxes / 10,000 labels"></label>
      <label>Target due date<input type="text" name="target_due_at" value="" placeholder="2026-04-25"></label>
      <label>Status
        <select name="status">
          {_simple_options([
            ('requested', 'Requested'),
            ('pricing', 'Pricing'),
            ('quoted', 'Quoted'),
            ('won', 'Won'),
            ('lost', 'Lost'),
            ('on_hold', 'On hold'),
          ], 'requested')}
        </select>
      </label>
      <label>Notes<input type="text" name="notes" value=""></label>
      <button type="submit">Create quote intent</button>
    </form>
    """
    quote_block = '<div class="empty">No standalone quote intents yet.</div>'
    if quote_intents:
        opportunities_by_id = {int(item.get("id") or 0): item for item in opportunities}
        quote_rows = ''.join(
            f"<tr><td><a class=\"strong-link\" href=\"/ui/quote-intents/{int(item.get('id') or 0)}\">{html.escape(item.get('created_at') or '—')}</a></td><td>{_badge(_labelize(item.get('quote_type') or 'service_quote'), 'accent')}</td><td>{html.escape((opportunities_by_id.get(int(item.get('opportunity_id') or 0)) or {}).get('title') or '—')}</td><td>{html.escape(item.get('rfq_reference') or '—')}</td><td>{html.escape(item.get('quantity_hint') or '—')}</td><td>{html.escape(item.get('target_due_at') or '—')}</td><td>{_badge(_labelize(item.get('status') or 'requested'), 'neutral')}</td><td>{html.escape(item.get('quote_reference') or '—')}</td><td>{_money(item.get('quoted_amount'), item.get('currency_code') or 'VND')}</td></tr>"
            for item in quote_intents
        )
        quote_block = f"<table><thead><tr><th>Created</th><th>Type</th><th>Opportunity</th><th>RFQ ref</th><th>Quantity</th><th>Target due</th><th>Status</th><th>Quote ref</th><th>Amount</th></tr></thead><tbody>{quote_rows}</tbody></table>"

    handoff_form = f"""
    <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0)}/production-handoffs" class="stack">
      <label>Quote intent
        <select name="quote_intent_id">
          {_simple_options([('', 'No linked quote intent')] + [(str(int(item.get('id') or 0)), f"#{int(item.get('id') or 0)} {_labelize(item.get('quote_type') or 'service_quote')}") for item in quote_intents], '')}
        </select>
      </label>
      <label>Handoff status
        <select name="handoff_status">{_simple_options([('ready_for_production', 'Ready for production'), ('scheduled', 'Scheduled'), ('in_progress', 'In progress'), ('blocked', 'Blocked'), ('completed', 'Completed')], 'ready_for_production')}</select>
      </label>
      <label>Production reference<input type="text" name="production_reference" value="" placeholder="JOB-2026-001"></label>
      <label>Requested ship date<input type="text" name="requested_ship_at" value="" placeholder="2026-04-30"></label>
      <label>Specification summary<input type="text" name="specification_summary" value="" placeholder="5000 corrugated cartons, 4c print"></label>
      <label>Notes<input type="text" name="notes" value=""></label>
      <button type="submit">Create production handoff</button>
    </form>
    """
    handoff_block = '<div class="empty">No production handoffs yet.</div>'
    if production_handoffs:
        handoff_rows = ''.join(
            f"<tr><td><a class=\"strong-link\" href=\"/ui/production-handoffs/{int(item.get('id') or 0)}\">{html.escape(item.get('created_at') or '—')}</a></td><td>{_badge(_labelize(item.get('handoff_status') or 'ready_for_production'), 'accent')}</td><td>{html.escape(item.get('production_reference') or '—')}</td><td>{html.escape(item.get('requested_ship_at') or '—')}</td><td>{html.escape(item.get('specification_summary') or '—')}</td><td>{html.escape(item.get('notes') or '—')}</td></tr>"
            for item in production_handoffs
        )
        handoff_block = f"<table><thead><tr><th>Created</th><th>Status</th><th>Production ref</th><th>Ship date</th><th>Specification</th><th>Notes</th></tr></thead><tbody>{handoff_rows}</tbody></table>"

    commercial_audit_block = '<div class="empty">No standalone commercial audit yet.</div>'
    if commercial_audit:
        audit_rows = ''.join(
            f"<tr><td>{html.escape(item.get('occurred_at') or '—')}</td><td>{_badge(_labelize(item.get('entity_type') or ''), 'neutral')}</td><td>{html.escape(item.get('action_type') or '—')}</td><td>{html.escape(item.get('previous_status') or '—')}</td><td>{html.escape(item.get('new_status') or '—')}</td><td>{html.escape(item.get('note') or '—')}</td></tr>"
            for item in commercial_audit
        )
        commercial_audit_block = f"<table><thead><tr><th>When</th><th>Entity</th><th>Action</th><th>From</th><th>To</th><th>Note</th></tr></thead><tbody>{audit_rows}</tbody></table>"

    decision_form = f"""
    <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0)}/decide" class="stack">
      <label>Outcome
        <select name="outcome">
          {_simple_options([
            ('approved_supplier','Approved supplier'),
            ('potential_supplier','Potential supplier'),
            ('needs_manual_review','Needs manual review'),
            ('duplicate','Duplicate'),
            ('not_relevant','Not relevant'),
            ('unreachable','Unreachable'),
          ], 'potential_supplier')}
        </select>
      </label>
      <label>Reason code<input type="text" name="reason_code" value="manual_operator_decision"></label>
      <label>Notes<input type="text" name="notes" value=""></label>
      <input type="hidden" name="manual_override" value="yes">
      <button type="submit">Apply standalone decision</button>
    </form>
    """

    queue_block = '<div class="empty">No review queue entries for this company.</div>'
    if queue_items:
        queue_rows = ''
        for item in queue_items:
            transition_form = (
                f'<form method="post" action="/ui/actions/queue/{int(item.get("id") or 0)}/transition" class="inline-form">'
                f'<input type="hidden" name="reason_code" value="manual_transition">'
                f'<input type="hidden" name="notes" value="Изменено из карточки компании">'
                f'<select name="target_status">{_simple_options([("pending","Pending"),("in_progress","In progress"),("done","Done"),("dismissed","Dismissed")], str(item.get("status") or "pending"))}</select>'
                f'<button type="submit">Update</button>'
                f'</form>'
            )
            queue_rows += (
                f"<tr><td>{_badge(_labelize(item.get('queue_name') or ''), _queue_tone(item.get('queue_name') or ''))}</td>"
                f"<td>{int(item.get('priority') or 0)}</td>"
                f"<td>{_score_badge(item.get('score'))}</td>"
                f"<td>{html.escape(item.get('reason') or '—')}</td>"
                f"<td>{_badge(_labelize(item.get('status') or 'pending'), 'neutral')}</td>"
                f"<td>{transition_form}</td></tr>"
            )
        queue_block = f"<table><thead><tr><th>Queue</th><th>Priority</th><th>Score</th><th>Why in review</th><th>Status</th><th>Action</th></tr></thead><tbody>{queue_rows}</tbody></table>"

    decisions_block = '<div class="empty">No standalone qualification decisions yet.</div>'
    if qualification_decisions:
        decision_rows = ''.join(
            f"<tr><td>{html.escape(item.get('decision_at') or '—')}</td><td>{_badge(_labelize(item.get('decision') or ''), 'accent')}</td><td>{_feedback_badge(item.get('route_outcome'))}</td><td>{html.escape(item.get('reason_code') or '—')}</td><td>{html.escape(item.get('internal_note') or '—')}</td></tr>"
            for item in qualification_decisions
        )
        decisions_block = f"<table><thead><tr><th>When</th><th>Decision</th><th>Route outcome</th><th>Reason</th><th>Notes</th></tr></thead><tbody>{decision_rows}</tbody></table>"

    audit_block = '<div class="empty">No standalone routing audit yet.</div>'
    if routing_audit:
        audit_rows = ''.join(
            f"<tr><td>{html.escape(item.get('event_at') or '—')}</td><td>{_badge(_labelize(item.get('event_type') or ''), 'neutral')}</td><td>{html.escape(item.get('from_state') or '—')}</td><td>{html.escape(item.get('to_state') or '—')}</td><td>{html.escape(item.get('reason_code') or '—')}</td></tr>"
            for item in routing_audit
        )
        audit_block = f"<table><thead><tr><th>When</th><th>Event</th><th>From</th><th>To</th><th>Reason</th></tr></thead><tbody>{audit_rows}</tbody></table>"

    feedback_block = '<div class="empty">No downstream feedback projection yet. Standalone intelligence is still present, but no downstream commercial/routing outcome has been ingested.</div>'
    feedback_badges = ''
    if feedback_projection:
        if _projection_is_synthetic(feedback_projection):
            feedback_badges = _synthetic_badge()
        feedback_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Routing status</span><div class="field-value">{_feedback_badge(feedback_projection.get('routing_outcome'))}</div></div>
          <div><span class="field-label">Qualification status</span><div class="field-value">{_feedback_badge(feedback_projection.get('qualification_status'))}</div></div>
          <div><span class="field-label">Commercial disposition</span><div class="field-value">{_feedback_badge(feedback_projection.get('lead_status'))}</div></div>
          <div><span class="field-label">Partner linkage</span><div class="field-value">{_bool_badge(bool(feedback_projection.get('partner_linked')), 'Linked', 'Not linked')}</div></div>
          <div><span class="field-label">Manual review</span><div class="field-value">{_feedback_badge(feedback_projection.get('manual_review_status'))}</div></div>
          <div><span class="field-label">Last event at</span><div class="field-value">{html.escape(feedback_projection.get('last_event_at') or '—')}</div></div>
          <div class="span-2"><span class="field-label">Reason codes</span><div class="field-value">{html.escape(' / '.join(part for part in [feedback_projection.get('routing_reason_code') or '', feedback_projection.get('qualification_reason_code') or '', feedback_projection.get('commercial_reason_code') or ''] if part) or '—')}</div></div>
          <div class="span-2"><span class="field-label">Notes</span><div class="field-value">{html.escape(' | '.join(part for part in [feedback_projection.get('routing_notes') or '', feedback_projection.get('qualification_notes') or '', feedback_projection.get('commercial_notes') or ''] if part) or '—')}</div></div>
        </div>
        """

    timeline_block = '<div class="empty">No related feedback events yet.</div>'
    if feedback_events:
        event_rows = ''.join(
            f"<tr><td>{html.escape(item.get('occurred_at') or '—')}</td><td>{_badge(_labelize(item.get('event_type') or ''), 'accent')} {' ' + _synthetic_badge() if item.get('is_synthetic') else ''}</td><td>{_feedback_event_outcome_summary(item)}</td><td>{html.escape(item.get('reason_code') or '—')}</td><td>{html.escape(item.get('notes') or '—')}</td></tr>"
            for item in feedback_events
        )
        timeline_block = f"<table><thead><tr><th>Occurred</th><th>Event</th><th>Outcome summary</th><th>Reason</th><th>Notes</th></tr></thead><tbody>{event_rows}</tbody></table>"

    raw_block = '<div class="empty">No correlated raw/source evidence found for this company.</div>'
    if raw_records:
        raw_rows = ''.join(
            f"<tr><td><a class=\"strong-link\" href=\"/ui/raw-records/{int(item.get('id') or 0)}\">{html.escape(item.get('company_name') or item.get('legal_name') or '—')}</a></td><td>{_external_link(item.get('source_url'))}</td><td>{html.escape(item.get('source_domain') or '—')}</td><td>{html.escape(item.get('city') or '—')}</td><td>{_badge(str(item.get('fetch_status') or 'unknown').upper(), 'neutral')}</td><td>{_score_badge(item.get('parser_confidence'))}</td><td>{html.escape(_summarize_raw_lists(item) or 'No list fields')}</td></tr>"
            for item in raw_records
        )
        raw_block = f"<table><thead><tr><th>Raw record</th><th>Source</th><th>Domain</th><th>City</th><th>Fetch</th><th>Parser conf.</th><th>Evidence summary</th></tr></thead><tbody>{raw_rows}</tbody></table>"

    actions = [f'<a class="button-link ghost" href="/ui/companies">Back to companies</a>']
    timeline_action = ''
    if source_key:
        timeline_href = f'/ui/feedback-status/{quote(source_key, safe="")}'
        audit_href = f'/ui/feedback-events?search={quote(source_key, safe="")}'
        actions.append(f'<a class="button-link ghost" href="{timeline_href}">Open feedback timeline</a>')
        actions.append(f'<a class="button-link ghost" href="{audit_href}">Open feedback audit</a>')
        timeline_action = f'<a class="button-link ghost" href="{timeline_href}">Open dedicated timeline</a>'
    actions.append(f'<a class="button-link ghost" href="/ui/workforce?company_id={int(company.get("id") or 0)}">Open workforce planner</a>')
    actions.append(f'<a class="button-link ghost" href="/ui/opportunities?company_id={int(company.get("id") or 0)}">Open opportunity list</a>')
    actions.append('<a class="button-link ghost" href="#raw-evidence">Jump to raw evidence</a>')

    body = f"""
    <section class="hero compact">
      <div>
        <p class="eyebrow">Company workbench</p>
        <h1>{html.escape(company.get('canonical_name') or 'Company')}</h1>
        <p class="lead">This is the main operator surface for one company. Standalone intelligence, downstream feedback, raw evidence, scores, and review state are kept together here.</p>
      </div>
      <div class="panel panel-tight"><div class="button-row">{' '.join(actions)}</div></div>
    </section>
    <section class="grid two">
      <div class="panel" id="overview"><h2>Company overview</h2><p class="muted">Canonical company card for quick operator inspection.</p>{company_overview}</div>
      <div class="panel" id="intelligence"><h2>Standalone intelligence</h2><p class="muted">Standalone-owned normalized/canonical intelligence. Downstream feedback never overwrites this block.</p>{intelligence_summary}</div>
    </section>
    <section class="grid two">
      <div class="panel" id="scores"><h2>Scores</h2>{score_block}</div>
      <div class="panel panel-accent" id="workflow"><h2>Standalone workflow</h2><p class="muted">This is the migrated business workflow state that used to sit in Odoo vendor profile and qualification objects.</p>{workflow_block}<h2 class="kicker">Operator decision</h2>{decision_form}</div>
    </section>
    <section class="grid two">
      <div class="panel panel-accent" id="commercial"><h2>Standalone commercial state</h2><p class="muted">Editable commercial follow-up owned by standalone. This is where manual sales progress lives now, not in downstream feedback snapshots.</p>{commercial_block}</div>
      <div class="panel"><h2>Commercial action</h2><p class="muted">Manual-first update form for customer/opportunity progress.</p>{commercial_form}</div>
    </section>
    <section class="grid two">
      <div class="panel panel-accent" id="customer-account"><h2>Customer account</h2><p class="muted">Minimum standalone customer/account owner for this commercial contour. This is not a res.partner clone.</p>{customer_account_block}</div>
      <div class="panel"><h2>Save customer account</h2><p class="muted">Standalone-owned customer identity used by opportunities and quote workbench.</p>{customer_account_form}</div>
    </section>
    <section class="grid two">
      <div class="panel panel-accent" id="opportunities"><div class="split"><div><h2>Opportunities</h2><p class="muted">Standalone lead/opportunity ownership for the active contour.</p></div><div><a class="button-link ghost" href="/ui/opportunities?company_id={int(company.get('id') or 0)}">Open list</a></div></div>{opportunities_block}</div>
      <div class="panel"><h2>Create opportunity</h2><p class="muted">Capture the commercial owner record here instead of depending on Odoo CRM lead ownership.</p>{opportunity_form}</div>
    </section>
    <section class="grid two">
      <div class="panel panel-accent" id="quotes"><h2>Quote intents</h2><p class="muted">Standalone-owned RFQ / quote-intent records. This is the first minimal replacement for Odoo quote handoff.</p>{quote_block}</div>
      <div class="panel"><h2>Create quote intent</h2><p class="muted">Capture the request so the operator path can continue inside standalone.</p>{quote_form}</div>
    </section>
    <section class="grid two">
      <div class="panel panel-accent" id="handoffs"><h2>Production handoffs</h2><p class="muted">Manual-first handoff into execution. This replaces jumping straight from quote status into ERP-shaped order objects.</p>{handoff_block}</div>
      <div class="panel"><h2>Create production handoff</h2><p class="muted">Create a lightweight execution handoff without pulling in full ERP order logic.</p>{handoff_form}</div>
    </section>
    <section class="grid two">
      <div class="panel" id="review"><h2>Review queue</h2><p class="muted">Why this company is currently in manual review and how the queue is moving.</p>{queue_block}</div>
      <div class="panel"><h2>Qualification decisions</h2><p class="muted">Standalone decision ledger for this supplier workflow.</p>{decisions_block}</div>
    </section>
    <section class="panel panel-accent" id="feedback"><div class="split"><div><h2>Downstream feedback</h2><p class="muted">Projection derived from the feedback ledger. This remains separate from standalone intelligence.</p></div><div>{feedback_badges}</div></div>{feedback_block}</section>
    <section class="panel"><div class="split"><div><h2>Feedback timeline</h2><p class="muted">Recent downstream events relevant to this company.</p></div><div>{timeline_action}</div></div>{timeline_block}</section>
    <section class="panel"><h2>Commercial audit</h2><p class="muted">Append-only audit for customer account, opportunity, quote, and handoff state changes in standalone.</p>{commercial_audit_block}</section>
    <section class="panel"><h2>Routing audit</h2><p class="muted">Audit trail of standalone queue transitions and routing decisions.</p>{audit_block}</section>
    <section class="panel" id="raw-evidence"><h2>Raw/source evidence</h2><p class="muted">Compact raw evidence summary. Open the raw record detail page when you need payload-level inspection.</p>{raw_block}</section>
    """
    return _layout(company.get("canonical_name") or "Company workbench", body, active="companies")


def _workforce_page(data: dict[str, Any]) -> str:
    company = data.get("company")
    estimation = data.get("estimation") or {}
    result = estimation.get("result") or {}
    payload_json = data.get("payload_json") or "{}"
    company_block = '<div class="empty">No company context selected. This tool stays standalone and does not mutate company intelligence state.</div>'
    company_hidden = ""
    if company:
        company_hidden = f'<input type="hidden" name="company_id" value="{int(company.get("id") or 0)}">'
        company_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Company</span><div class="field-value"><a class="strong-link" href="/ui/companies/{int(company.get('id') or 0)}">{html.escape(company.get('canonical_name') or 'Company')}</a></div></div>
          <div><span class="field-label">Canonical key</span><div class="field-value mono">{html.escape(company.get('canonical_key') or '—')}</div></div>
          <div><span class="field-label">City</span><div class="field-value">{html.escape(company.get('city') or '—')}</div></div>
          <div><span class="field-label">Capabilities</span><div class="field-value">{_chips(company.get('capabilities') or [], tone='neutral') or '<span class="muted">No capabilities</span>'}</div></div>
        </div>
        """

    cards = '<div class="empty">No workforce estimate yet.</div>'
    breakdown = '<div class="empty">No role breakdown yet.</div>'
    assumptions = '<div class="empty">No assumptions yet.</div>'
    if result:
        cards = (
            '<div class="cards compact metrics">'
            + _stat_card("Estimated hours", result.get("estimated_hours", "—"), "Total labor hours required.")
            + _stat_card("Required headcount", result.get("required_headcount", "—"), "Headcount implied by current shift capacity.")
            + _stat_card("Total labor cost", f'{float(result.get("total_labor_cost") or 0.0):,.0f} VND', "Standard plus overtime labor cost.")
            + _stat_card("Time remaining", result.get("time_remaining_hours", "—"), "Available hours minus required hours.")
            + _stat_card("Bottleneck role", result.get("bottleneck_role_code") or "—", "Role that constrains delivery right now.")
            + _stat_card("Overtime", "Yes" if result.get("overtime_required") else "No", "Whether the current plan requires overtime.")
            + '</div>'
        )
        role_rows = ''.join(
            f"<tr><td>{html.escape(item.get('role_code') or '—')}</td><td>{float(item.get('required_hours') or 0.0):.2f}</td><td>{float(item.get('available_hours') or 0.0):.2f}</td><td>{int(item.get('estimated_headcount') or 0)}</td><td>{float(item.get('overtime_hours') or 0.0):.2f}</td><td>{float(item.get('standard_cost') or 0.0):,.0f}</td><td>{float(item.get('overtime_cost') or 0.0):,.0f}</td><td>{_bool_badge(bool(item.get('bottleneck')), 'Yes', 'No')}</td></tr>"
            for item in result.get("role_breakdown") or []
        )
        empty_role_row = '<tr><td colspan="8" class="muted">No role breakdown.</td></tr>'
        breakdown = (
            "<table><thead><tr><th>Role</th><th>Required hours</th><th>Available hours</th><th>Headcount</th><th>Overtime</th><th>Standard cost</th><th>Overtime cost</th><th>Bottleneck</th></tr></thead>"
            f"<tbody>{role_rows or empty_role_row}</tbody></table>"
        )
        missing_skills = result.get("missing_skill_roles") or []
        assumptions_parts = []
        if missing_skills:
            assumptions_parts.append(f"<p><strong>Missing skills:</strong> {_chips(missing_skills, tone='warn')}</p>")
        assumption_items = ''.join(f"<li>{html.escape(str(item))}</li>" for item in result.get("assumptions") or [])
        assumptions = f"{''.join(assumptions_parts)}<ul class=\"link-list\">{assumption_items or '<li>No assumptions recorded.</li>'}</ul>"

    case_options = _simple_options([("", "Choose sample case")] + [(item["key"], item["label"]) for item in data.get("cases") or []], data.get("selected_case") or "")
    action_links = ['<a class="button-link ghost" href="/">Back to dashboard</a>']
    if company:
        action_links.append(f'<a class="button-link ghost" href="/ui/companies/{int(company.get("id") or 0)}">Back to company workbench</a>')
    body = f"""
    <section class="hero compact">
      <div>
        <p class="eyebrow">Workforce planner</p>
        <h1>Standalone labor estimation</h1>
        <p class="lead">Use the pure workforce engine to estimate labor hours, headcount, overtime, and cost. This tool does not mutate company intelligence or downstream feedback.</p>
      </div>
      <div class="panel panel-tight"><div class="button-row">{' '.join(action_links)}</div></div>
    </section>
    <section class="grid two">
      <div class="panel"><h2>Company context</h2><p class="muted">Optional. This only anchors the estimate to a company workbench for operator navigation.</p>{company_block}</div>
      <div class="panel"><h2>Sample scenarios</h2><form method="get" action="/ui/workforce" class="toolbar"><select name="case">{case_options}</select>{company_hidden}<button type="submit">Load scenario</button></form><p class="muted small">Scenario fixture: {html.escape(data.get('fixture_path') or '')}</p></div>
    </section>
    <section class="panel panel-accent">
      <h2>Estimate input</h2>
      <p class="muted">Edit the structured payload directly when you need a custom estimate. This is an explicit standalone planning tool, not hidden workflow state.</p>
      <form method="post" action="/ui/actions/workforce-estimate" class="stack">
        {company_hidden}
        <input type="hidden" name="case" value="{html.escape(data.get('selected_case') or '')}">
        <label>Structured estimate payload<textarea name="payload_json" rows="22" style="width:100%;padding:12px;border:1px solid var(--line);border-radius:12px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace">{html.escape(payload_json)}</textarea></label>
        <button type="submit">Run workforce estimate</button>
      </form>
    </section>
    <section class="panel"><h2>Estimate summary</h2>{cards}</section>
    <section class="grid two">
      <div class="panel"><h2>Role breakdown</h2>{breakdown}</div>
      <div class="panel"><h2>Assumptions and gaps</h2>{assumptions}</div>
    </section>
    """
    return _layout("Workforce planner", body, active="workforce")


def _commercial_pipeline_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        company = item.get("company")
        feedback = item.get("feedback")
        company_cell = '<span class="muted">Unmatched</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{int(company.get("id") or 0)}">{html.escape(company.get("canonical_name") or "Company")}</a><div class="muted small">{html.escape(company.get("city") or "—")}</div>'
        rows.append(
            f"<tr>"
            f"<td>{company_cell}</td>"
            f"<td>{_badge(_labelize(item.get('customer_status') or 'prospect'), 'neutral')}</td>"
            f"<td>{_badge(_labelize(item.get('commercial_stage') or 'new_lead'), 'accent')}</td>"
            f"<td>{html.escape(item.get('next_action') or '—')}</td>"
            f"<td>{html.escape(item.get('next_action_due_at') or '—')}</td>"
            f"<td>{_feedback_summary_badges(feedback)}</td>"
            f"</tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan="6" class="muted">No standalone commercial records yet.</td></tr>'
    filters = f"""
    <form method="get" action="/ui/commercial-pipeline" class="toolbar">
      <select name="customer_status">{_simple_options([('', 'All customer states'), ('prospect', 'Prospect'), ('active_customer', 'Active customer'), ('dormant', 'Dormant'), ('blocked', 'Blocked')], data['customer_status'])}</select>
      <select name="stage">{_simple_options([('', 'All stages'), ('new_lead', 'New lead'), ('contacting', 'Contacting'), ('qualified', 'Qualified'), ('rfq_requested', 'RFQ requested'), ('quoted', 'Quoted'), ('won', 'Won'), ('lost', 'Lost'), ('on_hold', 'On hold')], data['stage'])}</select>
      <select name="limit">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type="submit">Apply</button>
    </form>
    """
    table = f"<table><thead><tr><th>Company</th><th>Customer status</th><th>Commercial stage</th><th>Next action</th><th>Due</th><th>Downstream feedback</th></tr></thead><tbody>{body_rows}</tbody></table>"
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Commercial pipeline</p><h1>Standalone commercial follow-up</h1><p class="lead">Manual-first commercial state owned by standalone. This replaces hiding active sales progress inside Odoo-only lead state.</p></div><div class="panel panel-tight"><strong>{data['total']}</strong><span class="muted">commercial records</span></div></section>
    <section class="panel">{filters}{table}</section>
    """
    return _layout("Commercial pipeline", body, active="commercial")


def _opportunities_page(data: dict[str, Any]) -> str:
    company = data.get("company")
    rows = []
    for item in data["items"]:
        row_company = item.get("company")
        account = item.get("customer_account")
        company_cell = '<span class="muted">Unmatched</span>'
        if row_company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{int(row_company.get("id") or 0)}">{html.escape(row_company.get("canonical_name") or "Company")}</a><div class="muted small">{html.escape(row_company.get("city") or "—")}</div>'
        account_cell = html.escape((account or {}).get("account_name") or "—")
        rows.append(
            f"<tr>"
            f"<td>{company_cell}</td>"
            f"<td><a class=\"strong-link\" href=\"/ui/opportunities/{int(item.get('id') or 0)}\">{html.escape(item.get('title') or 'Opportunity')}</a></td>"
            f"<td>{_badge(_labelize(item.get('status') or 'new'), 'accent')}</td>"
            f"<td>{account_cell}</td>"
            f"<td>{html.escape(item.get('source_channel') or '—')}</td>"
            f"<td>{_money(item.get('estimated_value'), item.get('currency_code') or 'VND')}</td>"
            f"<td>{html.escape(item.get('next_action') or '—')}</td>"
            f"</tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan="7" class="muted">No opportunities yet.</td></tr>'
    company_hidden = f'<input type="hidden" name="company_id" value="{int(company.get("id") or 0)}">' if company else ''
    company_label = f' for {html.escape(company.get("canonical_name") or "company")}' if company else ''
    filters = f"""
    <form method="get" action="/ui/opportunities" class="toolbar">
      {company_hidden}
      <select name="status">{_simple_options([('', 'All statuses'), ('new', 'New'), ('contacting', 'Contacting'), ('qualified', 'Qualified'), ('rfq_requested', 'RFQ requested'), ('quoted', 'Quoted'), ('won', 'Won'), ('lost', 'Lost'), ('on_hold', 'On hold')], data['status'])}</select>
      <select name="limit">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type="submit">Apply</button>
    </form>
    """
    table = f"<table><thead><tr><th>Company</th><th>Opportunity</th><th>Status</th><th>Account</th><th>Source</th><th>Value</th><th>Next action</th></tr></thead><tbody>{body_rows}</tbody></table>"
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Opportunities</p><h1>Standalone commercial opportunities{company_label}</h1><p class="lead">Minimal lead/opportunity ownership for the active contour. This is not a generic CRM suite.</p></div><div class="panel panel-tight"><strong>{data['total']}</strong><span class="muted">opportunities</span></div></section>
    <section class="panel">{filters}{table}</section>
    """
    return _layout("Opportunities", body, active="commercial")


def _quote_pipeline_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        company = item.get("company")
        account = item.get("customer_account")
        opportunity = item.get("opportunity")
        company_cell = '<span class="muted">Unmatched</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{int(company.get("id") or 0)}">{html.escape(company.get("canonical_name") or "Company")}</a><div class="muted small">{html.escape(company.get("city") or "—")}</div>'
        opportunity_href = None
        if opportunity:
            opportunity_href = f"/ui/opportunities/{int(opportunity.get('id') or 0)}"
        rows.append(
            f"<tr>"
            f"<td>{company_cell}</td>"
            f"<td>{html.escape((account or {}).get('account_name') or '—')}</td>"
            f"<td>{_maybe_link((opportunity or {}).get('title') or '—', opportunity_href)}</td>"
            f"<td><a class=\"strong-link\" href=\"/ui/quote-intents/{int(item.get('id') or 0)}\">{_badge(_labelize(item.get('quote_type') or 'service_quote'), 'accent')}</a></td>"
            f"<td>{html.escape(item.get('rfq_reference') or '—')}</td>"
            f"<td>{html.escape(item.get('quantity_hint') or '—')}</td>"
            f"<td>{html.escape(item.get('target_due_at') or '—')}</td>"
            f"<td>{_badge(_labelize(item.get('status') or 'requested'), 'neutral')}</td>"
            f"<td>{html.escape(item.get('quote_reference') or '—')}<div class=\"muted small\">{_money(item.get('quoted_amount'), item.get('currency_code') or 'VND')}</div></td>"
            f"</tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan="9" class="muted">No quote intents yet.</td></tr>'
    filters = f"""
    <form method="get" action="/ui/quote-intents" class="toolbar">
      <select name="quote_type">{_simple_options([('', 'All quote types'), ('service_quote', 'Service quote'), ('rfq_packaging', 'RFQ packaging'), ('rfq_labels', 'RFQ labels'), ('rfq_printing', 'RFQ printing'), ('sample_request', 'Sample request')], data['quote_type'])}</select>
      <select name="status">{_simple_options([('', 'All statuses'), ('requested', 'Requested'), ('pricing', 'Pricing'), ('quoted', 'Quoted'), ('won', 'Won'), ('lost', 'Lost'), ('on_hold', 'On hold')], data['status'])}</select>
      <select name="limit">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type="submit">Apply</button>
    </form>
    """
    table = f"<table><thead><tr><th>Company</th><th>Account</th><th>Opportunity</th><th>Type</th><th>RFQ ref</th><th>Quantity</th><th>Target due</th><th>Status</th><th>Quote ref / Amount</th></tr></thead><tbody>{body_rows}</tbody></table>"
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Quote intents</p><h1>Standalone RFQ / quote intake</h1><p class="lead">Manual-first quote requests captured inside standalone, instead of disappearing into Odoo-only order scaffolding.</p></div><div class="panel panel-tight"><strong>{data['total']}</strong><span class="muted">quote intents</span></div></section>
    <section class="panel">{filters}{table}</section>
    """
    return _layout("Quote intents", body, active="quotes")


def _opportunity_detail_page(data: dict[str, Any]) -> str:
    record = data["opportunity"]
    company = data.get("company")
    customer_account = data.get("customer_account")
    quote_intents = data.get("quote_intents") or []
    audit = data.get("audit") or []
    action_links = ['<a class="button-link ghost" href="/ui/opportunities">Back to opportunities</a>']
    if company:
        action_links.append(f'<a class="button-link" href="/ui/companies/{int(company.get("id") or 0)}">Back to company workbench</a>')
    quote_block = '<div class="empty">No quote intents linked to this opportunity yet.</div>'
    if quote_intents:
        rows = ''.join(
            f"<tr><td><a class=\"strong-link\" href=\"/ui/quote-intents/{int(item.get('id') or 0)}\">Quote #{int(item.get('id') or 0)}</a></td><td>{_badge(_labelize(item.get('quote_type') or 'service_quote'), 'accent')}</td><td>{html.escape(item.get('rfq_reference') or '—')}</td><td>{_badge(_labelize(item.get('status') or 'requested'), 'neutral')}</td><td>{_money(item.get('quoted_amount'), item.get('currency_code') or 'VND')}</td></tr>"
            for item in quote_intents
        )
        quote_block = f"<table><thead><tr><th>Quote</th><th>Type</th><th>RFQ ref</th><th>Status</th><th>Amount</th></tr></thead><tbody>{rows}</tbody></table>"
    account_block = '<div class="empty">No linked customer account.</div>'
    if customer_account:
        account_block = _dict_table({
            "account_name": customer_account.get("account_name"),
            "account_status": customer_account.get("account_status"),
            "primary_contact_name": customer_account.get("primary_contact_name"),
            "primary_email": customer_account.get("primary_email"),
        })
    company_block = '<div class="empty">No company mapping found.</div>'
    if company:
        company_block = _dict_table({
            "canonical_name": company.get("canonical_name"),
            "canonical_key": company.get("canonical_key"),
            "city": company.get("city"),
        })
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Opportunity workbench</p><h1>{html.escape(record.get('title') or 'Opportunity')}</h1><p class="lead">Standalone-owned opportunity state for the active contour. This is the minimum replacement for Odoo lead ownership.</p></div><div class="panel panel-tight"><div class="button-row">{''.join(action_links)}</div></div></section>
    <section class="grid two"><div class="panel"><h2>Company</h2>{company_block}</div><div class="panel"><h2>Customer account</h2>{account_block}</div></section>
    <section class="grid two">
      <div class="panel"><h2>Opportunity summary</h2>{_dict_table({"status": record.get("status"), "source_channel": record.get("source_channel"), "estimated_value": record.get("estimated_value"), "currency_code": record.get("currency_code"), "target_due_at": record.get("target_due_at"), "next_action": record.get("next_action"), "external_opportunity_ref": record.get("external_opportunity_ref"), "odoo_lead_ref": record.get("odoo_lead_ref"), "notes": record.get("notes")})}</div>
      <div class="panel"><h2>Update opportunity</h2><form method="post" action="/ui/actions/opportunities/{int(record.get('id') or 0)}" class="stack"><label>Title<input type="text" name="title" value="{html.escape(record.get('title') or '')}"></label><label>Status<select name="status">{_simple_options([('new', 'New'), ('contacting', 'Contacting'), ('qualified', 'Qualified'), ('rfq_requested', 'RFQ requested'), ('quoted', 'Quoted'), ('won', 'Won'), ('lost', 'Lost'), ('on_hold', 'On hold')], str(record.get('status') or 'new'))}</select></label><label>Customer account<select name="customer_account_id">{_simple_options([('', 'No linked account')] + ([(str(int(customer_account.get('id') or 0)), customer_account.get('account_name') or 'Primary account')] if customer_account else []), str(int(customer_account.get('id') or 0)) if customer_account else '')}</select></label><label>Source channel<input type="text" name="source_channel" value="{html.escape(record.get('source_channel') or '')}"></label><label>Estimated value<input type="text" name="estimated_value" value="{html.escape('' if record.get('estimated_value') in {None, ''} else str(record.get('estimated_value')))}"></label><label>Currency<input type="text" name="currency_code" value="{html.escape(record.get('currency_code') or 'VND')}"></label><label>Target due date<input type="text" name="target_due_at" value="{html.escape(record.get('target_due_at') or '')}"></label><label>Next action<input type="text" name="next_action" value="{html.escape(record.get('next_action') or '')}"></label><label>External opportunity ref<input type="text" name="external_opportunity_ref" value="{html.escape(record.get('external_opportunity_ref') or '')}"></label><label>Trace Odoo lead ref<input type="text" name="odoo_lead_ref" value="{html.escape(record.get('odoo_lead_ref') or '')}"></label><label>Notes<input type="text" name="notes" value="{html.escape(record.get('notes') or '')}"></label><button type="submit">Save opportunity</button></form></div>
    </section>
    <section class="panel"><h2>Linked quote intents</h2>{quote_block}</section>
    <section class="panel"><h2>Commercial audit</h2>{_commercial_audit_table(audit)}</section>
    """
    return _layout(html.escape(record.get("title") or "Opportunity"), body, active="commercial")


def _production_handoff_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        company = item.get("company")
        quote_intent = item.get("quote_intent")
        opportunity = item.get("opportunity")
        company_cell = '<span class="muted">Unmatched</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{int(company.get("id") or 0)}">{html.escape(company.get("canonical_name") or "Company")}</a><div class="muted small">{html.escape(company.get("city") or "—")}</div>'
        quote_cell = '<span class="muted">No quote link</span>'
        if quote_intent:
            quote_cell = f'<a class="strong-link" href="/ui/quote-intents/{int(quote_intent.get("id") or 0)}">Quote #{int(quote_intent.get("id") or 0)}</a><div class="muted small">{_labelize(quote_intent.get("quote_type") or "service_quote")}</div>'
        opportunity_cell = '<span class="muted">No opportunity</span>'
        if opportunity:
            opportunity_cell = f'<a class="strong-link" href="/ui/opportunities/{int(opportunity.get("id") or 0)}">{html.escape(opportunity.get("title") or "Opportunity")}</a>'
        rows.append(
            f"<tr>"
            f"<td>{company_cell}</td>"
            f"<td><a class=\"strong-link\" href=\"/ui/production-handoffs/{int(item.get('id') or 0)}\">{_badge(_labelize(item.get('handoff_status') or 'ready_for_production'), 'accent')}</a></td>"
            f"<td>{html.escape(item.get('production_reference') or '—')}</td>"
            f"<td>{html.escape(item.get('requested_ship_at') or '—')}</td>"
            f"<td>{opportunity_cell}</td>"
            f"<td>{quote_cell}</td>"
            f"<td>{html.escape(item.get('specification_summary') or '—')}</td>"
            f"</tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan="7" class="muted">No production handoffs yet.</td></tr>'
    filters = f"""
    <form method="get" action="/ui/production-handoffs" class="toolbar">
      <select name="status">{_simple_options([('', 'All statuses'), ('ready_for_production', 'Ready for production'), ('scheduled', 'Scheduled'), ('in_progress', 'In progress'), ('blocked', 'Blocked'), ('completed', 'Completed')], data['status'])}</select>
      <select name="limit">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type="submit">Apply</button>
    </form>
    """
    table = f"<table><thead><tr><th>Company</th><th>Status</th><th>Production ref</th><th>Ship date</th><th>Opportunity</th><th>Quote</th><th>Specification</th></tr></thead><tbody>{body_rows}</tbody></table>"
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Production handoffs</p><h1>Standalone execution handoff</h1><p class="lead">Minimal handoff from quote/commercial state into production execution. This avoids forcing everything into ERP orders too early.</p></div><div class="panel panel-tight"><div class=\"button-row\"><a class=\"button-link ghost\" href=\"/ui/production-board\">Open production board</a><strong>{data['total']}</strong><span class=\"muted\">handoff records</span></div></div></section>
    <section class="panel">{filters}{table}</section>
    """
    return _layout("Production handoffs", body, active="handoffs")


def _production_board_page(data: dict[str, Any]) -> str:
    labels = {
        "ready_for_production": ("Ready for production", "accent"),
        "scheduled": ("Scheduled", "info"),
        "in_progress": ("In progress", "success"),
        "blocked": ("Blocked", "danger"),
        "completed": ("Completed", "neutral"),
    }
    columns_html = []
    for key, items in data["columns"].items():
        label, tone = labels.get(key, (_labelize(key), "neutral"))
        if items:
            cards = []
            for item in items:
                company = item.get("company")
                quote_intent = item.get("quote_intent")
                company_line = '<span class="muted">Unmatched</span>'
                if company:
                    company_line = f'<a class="strong-link" href="/ui/companies/{int(company.get("id") or 0)}">{html.escape(company.get("canonical_name") or "Company")}</a><div class="muted small">{html.escape(company.get("city") or "—")}</div>'
                quote_line = '<span class="muted">No quote</span>'
                if quote_intent:
                    quote_line = f'<a class="strong-link" href="/ui/quote-intents/{int(quote_intent.get("id") or 0)}">Quote #{int(quote_intent.get("id") or 0)}</a>'
                move_options = _simple_options(
                    [
                        ("ready_for_production", "Ready for production"),
                        ("scheduled", "Scheduled"),
                        ("in_progress", "In progress"),
                        ("blocked", "Blocked"),
                        ("completed", "Completed"),
                    ],
                    str(item.get("handoff_status") or "ready_for_production"),
                )
                cards.append(
                    f"""
                    <div class="stat-card">
                      <div class="split"><strong><a class="strong-link" href="/ui/production-handoffs/{int(item.get('id') or 0)}">Handoff #{int(item.get('id') or 0)}</a></strong>{_badge(label, tone)}</div>
                      <p class="small muted" style="margin:8px 0 10px">Production ref: {html.escape(item.get('production_reference') or '—')}</p>
                      <div class="stack" style="gap:8px">
                        <div>{company_line}</div>
                        <div class="small">{quote_line}</div>
                        <div class="small"><strong>Ship:</strong> {html.escape(item.get('requested_ship_at') or '—')}</div>
                        <div class="small"><strong>Spec:</strong> {html.escape(item.get('specification_summary') or '—')}</div>
                      </div>
                      <form method="post" action="/ui/actions/production-handoffs/{int(item.get('id') or 0)}" class="stack" style="margin-top:12px">
                        <label>Move to<select name="handoff_status">{move_options}</select></label>
                        <button type="submit">Update status</button>
                      </form>
                    </div>
                    """
                )
            body = "".join(cards)
        else:
            body = '<div class="empty">No handoffs in this column.</div>'
        columns_html.append(f'<div class="panel"><div class="split"><h2>{label}</h2><span class="muted">{len(items)}</span></div>{body}</div>')
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Production board</p><h1>Standalone execution board</h1><p class="lead">Operator-first production board built on top of standalone handoff records. This is the minimal replacement for hiding execution state inside ERP-shaped order objects.</p></div><div class="panel panel-tight"><div class="button-row"><a class="button-link ghost" href="/ui/production-handoffs">Open handoff list</a><strong>{data['total']}</strong><span class="muted">total handoffs</span></div></div></section>
    <section class="cards compact" style="grid-template-columns:repeat(5,minmax(0,1fr));align-items:start">{''.join(columns_html)}</section>
    """
    return _layout("Production board", body, active="production-board")


def _quote_intent_detail_page(data: dict[str, Any]) -> str:
    record = data["quote_intent"]
    company = data.get("company")
    customer_account = data.get("customer_account")
    opportunity = data.get("opportunity")
    commercial_record = data.get("commercial_record")
    feedback_projection = data.get("feedback_projection")
    audit = data.get("audit") or []
    company_actions = ['<a class="button-link ghost" href="/ui/quote-intents">Back to quote intents</a>']
    if company:
        company_actions.append(f'<a class="button-link" href="/ui/companies/{int(company.get("id") or 0)}">Back to company workbench</a>')
    company_block = '<div class="empty">No company mapping found for this quote intent.</div>'
    if company:
        company_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Canonical company</span><div class="field-value"><a class="strong-link" href="/ui/companies/{int(company.get('id') or 0)}">{html.escape(company.get('canonical_name') or 'Company')}</a></div></div>
          <div><span class="field-label">City</span><div class="field-value">{html.escape(company.get('city') or '—')}</div></div>
          <div><span class="field-label">Capabilities</span><div class="field-value">{_chips(company.get('capabilities') or [], 'neutral') or '<span class="muted">—</span>'}</div></div>
          <div><span class="field-label">Feedback</span><div class="field-value">{_feedback_summary_badges(feedback_projection)}</div></div>
        </div>
        """
    ownership_block = f"""
    <div class="detail-grid">
      <div><span class="field-label">Customer account</span><div class="field-value">{_maybe_link((customer_account or {}).get('account_name') or '—', f"/ui/companies/{int(company.get('id') or 0)}#customer-account" if customer_account and company else None)}</div></div>
      <div><span class="field-label">Opportunity</span><div class="field-value">{_maybe_link((opportunity or {}).get('title') or '—', f"/ui/opportunities/{int(opportunity.get('id') or 0)}" if opportunity else None)}</div></div>
      <div><span class="field-label">RFQ reference</span><div class="field-value mono">{html.escape(record.get('rfq_reference') or '—')}</div></div>
      <div><span class="field-label">Ownership</span><div class="field-value">{_badge('Standalone', 'success')}</div></div>
    </div>
    """
    commercial_block = '<div class="empty">No standalone commercial state for this company yet.</div>'
    if commercial_record:
        commercial_block = f"""
        <div class="detail-grid">
          <div><span class="field-label">Customer status</span><div class="field-value">{_badge(_labelize(commercial_record.get('customer_status') or 'prospect'), 'neutral')}</div></div>
          <div><span class="field-label">Commercial stage</span><div class="field-value">{_badge(_labelize(commercial_record.get('commercial_stage') or 'new_lead'), 'accent')}</div></div>
          <div><span class="field-label">Next action</span><div class="field-value">{html.escape(commercial_record.get('next_action') or '—')}</div></div>
          <div><span class="field-label">Next action due</span><div class="field-value">{html.escape(commercial_record.get('next_action_due_at') or '—')}</div></div>
        </div>
        """
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Quote workbench</p><h1>Quote intent #{int(record.get('id') or 0)}</h1><p class="lead">Standalone-owned quote workflow. This is where manual pricing progress should live instead of disappearing into ERP-shaped objects too early.</p></div><div class="panel panel-tight"><div class="button-row">{''.join(company_actions)}</div></div></section>
    <section class="grid two">
      <div class="panel"><h2>Company context</h2>{company_block}</div>
      <div class="panel"><h2>Commercial context</h2>{ownership_block}<h2 class="kicker">Commercial summary</h2>{commercial_block}</div>
    </section>
    <section class="grid two">
      <div class="panel">
        <h2>Quote summary</h2>
        <div class="detail-grid">
          <div><span class="field-label">Type</span><div class="field-value">{_badge(_labelize(record.get('quote_type') or 'service_quote'), 'accent')}</div></div>
          <div><span class="field-label">Status</span><div class="field-value">{_badge(_labelize(record.get('status') or 'requested'), 'neutral')}</div></div>
          <div><span class="field-label">RFQ reference</span><div class="field-value mono">{html.escape(record.get('rfq_reference') or '—')}</div></div>
          <div><span class="field-label">Quantity</span><div class="field-value">{html.escape(record.get('quantity_hint') or '—')}</div></div>
          <div><span class="field-label">Target due</span><div class="field-value">{html.escape(record.get('target_due_at') or '—')}</div></div>
          <div><span class="field-label">Quote ref</span><div class="field-value mono">{html.escape(record.get('quote_reference') or '—')}</div></div>
          <div><span class="field-label">Quoted amount</span><div class="field-value">{_money(record.get('quoted_amount'), record.get('currency_code') or 'VND')}</div></div>
          <div><span class="field-label">Last status change</span><div class="field-value">{html.escape(record.get('last_status_at') or '—')}</div></div>
          <div><span class="field-label">Created</span><div class="field-value">{html.escape(record.get('created_at') or '—')}</div></div>
          <div class="span-2"><span class="field-label">Pricing notes</span><div class="field-value">{html.escape(record.get('pricing_notes') or '—')}</div></div>
          <div class="span-2"><span class="field-label">Notes</span><div class="field-value">{html.escape(record.get('notes') or '—')}</div></div>
        </div>
      </div>
      <div class="panel">
        <h2>Update quote workflow</h2>
        <form method="post" action="/ui/actions/quote-intents/{int(record.get('id') or 0)}" class="stack">
          <label>Customer account<select name="customer_account_id">{_simple_options([('', 'No linked account')] + ([(str(int(customer_account.get('id') or 0)), customer_account.get('account_name') or 'Primary account')] if customer_account else []), str(int(customer_account.get('id') or 0)) if customer_account else '')}</select></label>
          <label>Opportunity<select name="opportunity_id">{_simple_options([('', 'No linked opportunity')] + ([(str(int(opportunity.get('id') or 0)), opportunity.get('title') or 'Opportunity')] if opportunity else []), str(int(opportunity.get('id') or 0)) if opportunity else '')}</select></label>
          <label>Status
            <select name="status">{_simple_options([('requested', 'Requested'), ('pricing', 'Pricing'), ('quoted', 'Quoted'), ('won', 'Won'), ('lost', 'Lost'), ('on_hold', 'On hold')], str(record.get('status') or 'requested'))}</select>
          </label>
          <label>RFQ reference<input type="text" name="rfq_reference" value="{html.escape(record.get('rfq_reference') or '')}"></label>
          <label>Quote reference<input type="text" name="quote_reference" value="{html.escape(record.get('quote_reference') or '')}"></label>
          <label>Quoted amount<input type="text" name="quoted_amount" value="{html.escape('' if record.get('quoted_amount') in {None, ''} else str(record.get('quoted_amount')))}" placeholder="12500000"></label>
          <label>Currency code<input type="text" name="currency_code" value="{html.escape(record.get('currency_code') or 'VND')}"></label>
          <label>Target due date<input type="text" name="target_due_at" value="{html.escape(record.get('target_due_at') or '')}"></label>
          <label>Pricing notes<input type="text" name="pricing_notes" value="{html.escape(record.get('pricing_notes') or '')}"></label>
          <label>Notes<input type="text" name="notes" value="{html.escape(record.get('notes') or '')}"></label>
          <button type="submit">Save quote workflow</button>
        </form>
        <h2 class="kicker">Create production handoff</h2>
        <form method="post" action="/ui/actions/companies/{int(company.get('id') or 0) if company else 0}/production-handoffs" class="stack">
          <input type="hidden" name="quote_intent_id" value="{int(record.get('id') or 0)}">
          <label>Handoff status
            <select name="handoff_status">{_simple_options([('ready_for_production', 'Ready for production'), ('scheduled', 'Scheduled'), ('in_progress', 'In progress'), ('blocked', 'Blocked'), ('completed', 'Completed')], 'ready_for_production')}</select>
          </label>
          <label>Production reference<input type="text" name="production_reference" value=""></label>
          <label>Requested ship date<input type="text" name="requested_ship_at" value="{html.escape(record.get('target_due_at') or '')}"></label>
          <label>Specification summary<input type="text" name="specification_summary" value="{html.escape((record.get('quantity_hint') or '')[:120])}"></label>
          <label>Notes<input type="text" name="notes" value=""></label>
          <button type="submit">Create production handoff</button>
        </form>
      </div>
    </section>
    <section class="panel"><h2>Commercial audit</h2>{_commercial_audit_table(audit)}</section>
    """
    return _layout(f"Quote intent #{int(record.get('id') or 0)}", body, active="quotes")


def _production_handoff_detail_page(data: dict[str, Any]) -> str:
    record = data["production_handoff"]
    company = data.get("company")
    quote_intent = data.get("quote_intent")
    opportunity = data.get("opportunity")
    audit = data.get("audit") or []
    action_links = ['<a class="button-link ghost" href="/ui/production-handoffs">Back to production handoffs</a>']
    if company:
        action_links.append(f'<a class="button-link" href="/ui/companies/{int(company.get("id") or 0)}">Back to company workbench</a>')
    if quote_intent:
        action_links.append(f'<a class="button-link ghost" href="/ui/quote-intents/{int(quote_intent.get("id") or 0)}">Back to quote workbench</a>')
    if opportunity:
        action_links.append(f'<a class="button-link ghost" href="/ui/opportunities/{int(opportunity.get("id") or 0)}">Back to opportunity</a>')
    company_block = '<div class="empty">No company mapping found.</div>'
    if company:
        company_block = _dict_table({
            "canonical_name": company.get("canonical_name"),
            "canonical_key": company.get("canonical_key"),
            "city": company.get("city"),
            "website": company.get("website"),
        })
    quote_block = '<div class="empty">No linked quote intent.</div>'
    if quote_intent:
        quote_block = _dict_table({
            "quote_id": quote_intent.get("id"),
            "quote_type": quote_intent.get("quote_type"),
            "status": quote_intent.get("status"),
            "rfq_reference": quote_intent.get("rfq_reference"),
            "quote_reference": quote_intent.get("quote_reference"),
            "quoted_amount": quote_intent.get("quoted_amount"),
        })
    opportunity_block = '<div class="empty">No linked opportunity.</div>'
    if opportunity:
        opportunity_block = _dict_table({
            "opportunity_id": opportunity.get("id"),
            "title": opportunity.get("title"),
            "status": opportunity.get("status"),
            "source_channel": opportunity.get("source_channel"),
            "next_action": opportunity.get("next_action"),
        })
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Production handoff</p><h1>Handoff #{int(record.get('id') or 0)}</h1><p class="lead">Standalone-owned execution handoff. This is the bridge between quote state and actual production follow-through.</p></div><div class="panel panel-tight"><div class="button-row">{''.join(action_links)}</div></div></section>
    <section class="grid two">
      <div class="panel"><h2>Company context</h2>{company_block}</div>
      <div class="panel"><h2>Quote context</h2>{quote_block}</div>
    </section>
    <section class="panel"><h2>Opportunity context</h2>{opportunity_block}</section>
    <section class="grid two">
      <div class="panel"><h2>Handoff summary</h2>{_dict_table({"handoff_status": record.get("handoff_status"), "production_reference": record.get("production_reference"), "requested_ship_at": record.get("requested_ship_at"), "specification_summary": record.get("specification_summary"), "notes": record.get("notes"), "created_at": record.get("created_at"), "updated_at": record.get("updated_at")})}</div>
      <div class="panel"><h2>Update handoff</h2><form method="post" action="/ui/actions/production-handoffs/{int(record.get('id') or 0)}" class="stack"><label>Status<select name="handoff_status">{_simple_options([('ready_for_production', 'Ready for production'), ('scheduled', 'Scheduled'), ('in_progress', 'In progress'), ('blocked', 'Blocked'), ('completed', 'Completed')], str(record.get('handoff_status') or 'ready_for_production'))}</select></label><label>Production reference<input type="text" name="production_reference" value="{html.escape(record.get('production_reference') or '')}"></label><label>Requested ship date<input type="text" name="requested_ship_at" value="{html.escape(record.get('requested_ship_at') or '')}"></label><label>Specification summary<input type="text" name="specification_summary" value="{html.escape(record.get('specification_summary') or '')}"></label><label>Notes<input type="text" name="notes" value="{html.escape(record.get('notes') or '')}"></label><button type="submit">Save production handoff</button></form></div>
    </section>
    <section class="panel"><h2>Commercial audit</h2>{_commercial_audit_table(audit)}</section>
    """
    return _layout(f"Production handoff #{int(record.get('id') or 0)}", body, active="handoffs")


def _feedback_status_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        company = item.get("company")
        company_cell = '<span class="muted">Unmatched</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or company.get("legal_name") or item.get("source_key") or "Company")}</a><div class="muted small"><code>{html.escape(item.get("source_key") or "")}</code></div>'
        rows.append(
            (
                f'<tr><td>{company_cell}<div class="muted small"><a href="/ui/feedback-status/{quote(item.get("source_key") or "", safe="")}">Open timeline</a></div></td>'
                f'<td>{_feedback_summary_badges(item)}</td>'
                f'<td>{_bool_badge(bool(item.get("partner_linked")), "Partner linked", "No partner")}</td>'
                f'<td>{_bool_badge(bool(item.get("crm_linked")), "CRM linked", "No CRM link")}</td>'
                f'<td>{html.escape(item.get("last_event_at") or "—")}</td>'
                f'<td>{html.escape(item.get("routing_reason_code") or item.get("qualification_reason_code") or item.get("commercial_reason_code") or "—")}</td></tr>'
            )
        )
    filters = f"""
    <form method="get" action="/ui/feedback-status" class="toolbar">
      <input type="text" name="search" value="{html.escape(data['search'])}" placeholder="Search source key or company">
      <select name="state">{_simple_options([('', 'All states'), ('routing', 'Has routing'), ('qualification', 'Has qualification'), ('commercial', 'Has commercial'), ('linkage', 'Has linkage'), ('manual_override', 'Manual override')], data['state'])}</select>
      <select name="limit">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type="submit">Apply</button>
    </form>
    """
    body_rows = ''.join(rows)
    if not body_rows:
        body_rows = '<tr><td colspan="6" class="muted">No feedback projection rows match the current filters.</td></tr>'
    table = '<table><thead><tr><th>Company / source</th><th>Outcome summary</th><th>Partner</th><th>Commercial</th><th>Last event</th><th>Reason</th></tr></thead>' + f'<tbody>{body_rows}</tbody></table>'
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Feedback projection</p><h1>Downstream outcome view</h1><p class="lead">Projection derived from the feedback ledger. It is readable for operators and stays separate from canonical intelligence.</p></div><div class="panel panel-tight"><strong>{data['total']}</strong><span class="muted">projection rows</span></div></section>
    <section class="panel">{filters}{table}</section>
    """
    return _layout("Feedback status", body, active="feedback")


def _feedback_status_detail_page(data: dict[str, Any]) -> str:
    source_key = data['source_key']
    projection = data['projection']
    company = data.get('company')
    events = data.get('events') or []
    action_links = ['<a class="button-link ghost" href="/ui/feedback-status">Back to feedback status</a>']
    if company:
        action_links.append(f'<a class="button-link ghost" href="/ui/companies/{company["id"]}">Back to company workbench</a>')
    company_block = '<div class="empty">No canonical company currently matches this feedback source key.</div>'
    if company:
        company_block = f'<div class="detail-grid"><div><span class="field-label">Canonical company</span><div class="field-value"><a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or "Company")}</a></div></div><div><span class="field-label">City</span><div class="field-value">{html.escape(company.get("city") or "—")}</div></div><div><span class="field-label">Website</span><div class="field-value">{_external_link(company.get("website"))}</div></div><div><span class="field-label">Review status</span><div class="field-value">{_badge(_labelize(company.get("review_status") or "new"), "neutral")}</div></div></div>'
    projection_block = f'''
    <div class="detail-grid">
      <div><span class="field-label">Source key</span><div class="field-value mono">{html.escape(source_key)}</div></div>
      <div><span class="field-label">Last event</span><div class="field-value">{html.escape(projection.get('last_event_type') or '—')} {' ' + _synthetic_badge() if projection.get('last_event_is_synthetic') else ''}</div></div>
      <div><span class="field-label">Last event at</span><div class="field-value">{html.escape(projection.get('last_event_at') or '—')}</div></div>
      <div><span class="field-label">Routing</span><div class="field-value">{_feedback_badge(projection.get('routing_outcome'))} {' ' + _synthetic_badge() if projection.get('routing_is_synthetic') else ''}</div></div>
      <div><span class="field-label">Manual review</span><div class="field-value">{_feedback_badge(projection.get('manual_review_status'))}</div></div>
      <div><span class="field-label">Qualification</span><div class="field-value">{_feedback_badge(projection.get('qualification_status'))} {' ' + _synthetic_badge() if projection.get('qualification_is_synthetic') else ''}</div></div>
      <div><span class="field-label">Commercial</span><div class="field-value">{_feedback_badge(projection.get('lead_status'))} {' ' + _synthetic_badge() if projection.get('commercial_is_synthetic') else ''}</div></div>
      <div><span class="field-label">Partner linkage</span><div class="field-value">{_bool_badge(bool(projection.get('partner_linked')), 'Linked', 'Not linked')} {' ' + _synthetic_badge() if projection.get('partner_is_synthetic') else ''}</div></div>
      <div><span class="field-label">CRM linkage</span><div class="field-value">{_bool_badge(bool(projection.get('crm_linked')), 'Linked', 'Not linked')}</div></div>
      <div class="span-2"><span class="field-label">Routing note</span><div class="field-value">{html.escape(projection.get('routing_notes') or '—')}</div></div>
      <div class="span-2"><span class="field-label">Qualification note</span><div class="field-value">{html.escape(projection.get('qualification_notes') or '—')}</div></div>
      <div class="span-2"><span class="field-label">Commercial note</span><div class="field-value">{html.escape(projection.get('commercial_notes') or '—')}</div></div>
    </div>
    '''
    events_block = '<div class="empty">No feedback events yet for this source key.</div>'
    if events:
        rows = ''.join(
            f"<tr><td>{html.escape(item.get('occurred_at') or '—')}</td><td>{_badge(_labelize(item.get('event_type') or ''), 'accent')} {' ' + _synthetic_badge() if item.get('is_synthetic') else ''}</td><td>{_feedback_event_outcome_summary(item)}</td><td>{html.escape(item.get('reason_code') or '—')}</td><td>{html.escape(item.get('notes') or '—')}</td><td><code>{html.escape(item.get('event_id') or '')}</code></td></tr>"
            for item in events
        )
        events_block = f"<table><thead><tr><th>Occurred</th><th>Event</th><th>Outcome summary</th><th>Reason</th><th>Notes</th><th>Event ID</th></tr></thead><tbody>{rows}</tbody></table>"
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Feedback detail</p><h1>Feedback timeline</h1><p class="lead">This is the downstream feedback projection and its audit trail. It remains separate from canonical intelligence.</p></div><div class="panel panel-tight"><div class="button-row">{' '.join(action_links)}</div></div></section>
    <section class="grid two"><div class="panel panel-accent"><h2>Current projection</h2>{projection_block}</div><div class="panel"><h2>Related canonical company</h2>{company_block}</div></section>
    <section class="panel"><h2>Feedback ledger for this source</h2>{events_block}</section>
    """
    return _layout('Feedback timeline', body, active='feedback')


def _feedback_events_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data['items']:
        company = item.get('company')
        company_cell = '<span class="muted">Unmatched</span>'
        company_action = '<span class="muted">No company</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or "Company")}</a>'
            company_action = f'<a class="strong-link" href="/ui/companies/{company["id"]}">Open company</a>'
        source_href = f"/ui/feedback-status/{quote(item.get('source_key') or '', safe='')}"
        synthetic = _synthetic_badge() if item.get('is_synthetic') else ''
        rows.append(
            (
                f'<tr><td><code>{html.escape(item.get("event_id") or "")}</code></td>'
                f'<td>{html.escape(item.get("occurred_at") or "—")}</td>'
                f'<td>{_badge(_labelize(item.get("event_type") or ""), "accent")} {synthetic}</td>'
                f'<td><a href="{source_href}">{html.escape(item.get("source_key") or "—")}</a></td>'
                f'<td>{company_cell}</td>'
                f'<td>{_feedback_event_outcome_summary(item)}</td>'
                f'<td>{html.escape(item.get("reason_code") or "—")}</td>'
                f'<td>{_truncate(item.get("notes") or "—", 90)}</td>'
                f'<td>{company_action}</td></tr>'
            )
        )
    filters = f"""
    <form method="get" action="/ui/feedback-events" class="toolbar">
      <input type="text" name="search" value="{html.escape(data['search'])}" placeholder="Search event id, source key, company, reason">
      <select name="event_type">{_simple_options([('', 'All event types'), ('routing_feedback', 'Routing'), ('qualification_feedback', 'Qualification'), ('partner_linkage_feedback', 'Partner linkage'), ('commercial_disposition_feedback', 'Commercial disposition')], data['event_type'])}</select>
      <select name="limit">{_simple_options([('25','25 rows'),('50','50 rows'),('100','100 rows')], str(data['limit']))}</select>
      <button type="submit">Apply</button>
    </form>
    """
    body_rows = ''.join(rows)
    if not body_rows:
        body_rows = '<tr><td colspan="9" class="muted">No feedback events match the current filters.</td></tr>'
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Feedback audit</p><h1>Feedback event ledger</h1><p class="lead">Audit-level view of the downstream feedback ledger. Synthetic/sample rows are explicitly labeled.</p></div><div class="panel panel-tight"><strong>{data['total']}</strong><span class="muted">matching events</span></div></section>
    <section class="panel">{filters}<table><thead><tr><th>Event ID</th><th>Occurred</th><th>Type</th><th>Source key</th><th>Company</th><th>Outcome summary</th><th>Reason</th><th>Notes</th><th>Action</th></tr></thead><tbody>{body_rows}</tbody></table></section>
    """
    return _layout('Feedback audit', body, active='feedback-events')


def _raw_record_detail_page(data: dict[str, Any]) -> str:
    raw = data['raw_record']
    company = data.get('company')
    action_links = ['<a class="button-link ghost" href="/ui/raw-records">Back to raw records</a>']
    company_block = '<div class="empty">This raw record is not currently correlated to a canonical company.</div>'
    if company:
        action_links.append(f'<a class="button-link ghost" href="/ui/companies/{company["id"]}">Back to company workbench</a>')
        company_block = f'<div class="detail-grid"><div><span class="field-label">Canonical company</span><div class="field-value"><a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or "Company")}</a></div></div><div><span class="field-label">Canonical key</span><div class="field-value mono">{html.escape(company.get("canonical_key") or "—")}</div></div><div><span class="field-label">City</span><div class="field-value">{html.escape(company.get("city") or "—")}</div></div><div><span class="field-label">Review status</span><div class="field-value">{_badge(_labelize(company.get("review_status") or "new"), "neutral")}</div></div></div>'
    metadata_block = f'''
    <div class="detail-grid">
      <div><span class="field-label">Raw name</span><div class="field-value">{html.escape(raw.get('company_name') or raw.get('legal_name') or '—')}</div></div>
      <div><span class="field-label">Source type</span><div class="field-value">{html.escape(raw.get('source_type') or '—')}</div></div>
      <div><span class="field-label">Source domain</span><div class="field-value">{html.escape(raw.get('source_domain') or '—')}</div></div>
      <div><span class="field-label">Scenario key</span><div class="field-value">{html.escape(raw.get('scenario_key') or '—')}</div></div>
      <div><span class="field-label">City</span><div class="field-value">{html.escape(raw.get('city') or '—')}</div></div>
      <div><span class="field-label">Fetch status</span><div class="field-value">{_badge(str(raw.get('fetch_status') or 'unknown').upper(), 'neutral')}</div></div>
      <div><span class="field-label">Parser confidence</span><div class="field-value">{_score_badge(raw.get('parser_confidence'))}</div></div>
      <div><span class="field-label">Source URL</span><div class="field-value">{_external_link(raw.get('source_url'))}</div></div>
      <div><span class="field-label">Source fingerprint</span><div class="field-value mono">{html.escape(raw.get('source_fingerprint') or '—')}</div></div>
      <div><span class="field-label">Candidate dedup fingerprint</span><div class="field-value mono">{html.escape(raw.get('candidate_dedup_fingerprint') or '—')}</div></div>
    </div>
    '''
    list_block = _dict_table({
        'categories': ', '.join(raw.get('categories') or []) or '—',
        'services': ', '.join(raw.get('services') or []) or '—',
        'products': ', '.join(raw.get('products') or []) or '—',
    })
    payload = html.escape(json.dumps(raw.get('raw_payload') or {}, ensure_ascii=False, indent=2, sort_keys=True))
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Raw record detail</p><h1>Source evidence</h1><p class="lead">Inspect the raw discovery row and jump directly back into the related company workbench when correlation exists.</p></div><div class="panel panel-tight"><div class="button-row">{' '.join(action_links)}</div></div></section>
    <section class="grid two"><div class="panel"><h2>Raw record metadata</h2>{metadata_block}</div><div class="panel"><h2>Canonical correlation</h2>{company_block}<h2 class="kicker">List fields</h2>{list_block}</div></section>
    <section class="panel"><h2>Raw payload</h2><pre>{payload}</pre></section>
    """
    return _layout('Raw record detail', body, active='raw')


def _review_queue_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        company = item.get("company")
        company_cell = '<span class="muted">Missing company</span>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or "Company")}</a><div class="muted small">{html.escape(company.get("city") or "—")}</div><div class="muted small">{html.escape(company.get("canonical_key") or "")}</div>'
        rows.append(
            f"<tr><td>{company_cell}</td><td>{_badge(_labelize(item.get('queue_name') or ''), _queue_tone(item.get('queue_name') or ''))}</td><td>{int(item.get('priority') or 0)}</td><td>{_score_badge(item.get('score'))}</td><td>{html.escape(item.get('reason') or '—')}</td><td>{_badge(_labelize(item.get('status') or 'pending'), 'neutral')}</td></tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan=6 class="muted">No queue items yet.</td></tr>'
    table = f"<table><thead><tr><th>Company</th><th>Queue</th><th>Priority</th><th>Score</th><th>Why in review</th><th>Status</th></tr></thead><tbody>{body_rows}</tbody></table>"
    body = f"""
    <section class=\"hero compact\"><div><p class=\"eyebrow\">Review queue</p><h1>Operator review workload</h1><p class=\"lead\">Everything currently queued for manual attention, with direct links back into the company workbench.</p></div><div class=\"panel panel-tight\"><strong>{data['total']}</strong><span class=\"muted\">queue rows</span></div></section>
    <section class=\"panel\">{table}</section>
    """
    return _layout("Review queue", body, active="review")


def _raw_records_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data["items"]:
        company = item.get("company")
        company_link = '<span class="muted">Unmatched</span>'
        if company:
            company_link = f'<a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or "Company")}</a>'
        rows.append(
            f"<tr><td><a class=\"strong-link\" href=\"/ui/raw-records/{int(item.get('id') or 0)}\">{html.escape(item.get('company_name') or item.get('legal_name') or '—')}</a><div class=\"muted small\">{html.escape(item.get('source_type') or '—')} / {html.escape(item.get('source_domain') or '—')}</div></td><td>{company_link}</td><td>{html.escape(item.get('city') or '—')}</td><td>{_badge(str(item.get('fetch_status') or 'unknown').upper(), 'neutral')}</td><td>{_score_badge(item.get('parser_confidence'))}</td><td>{html.escape(item.get('scenario_key') or '—')}</td><td>{_external_link(item.get('source_url'))}</td><td>{html.escape(_summarize_raw_lists(item) or 'No list fields')}</td></tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan=8 class="muted">No raw records stored yet.</td></tr>'
    table = f"<table><thead><tr><th>Raw record</th><th>Canonical company</th><th>City</th><th>Fetch</th><th>Parser conf.</th><th>Scenario</th><th>Source</th><th>Evidence summary</th></tr></thead><tbody>{body_rows}</tbody></table>"
    body = f"""
    <section class=\"hero compact\"><div><p class=\"eyebrow\">Raw records</p><h1>Source-side discovery view</h1><p class=\"lead\">Inspect raw discovery rows and move directly back into the related company workbench.</p></div><div class=\"panel panel-tight\"><strong>{data['total']}</strong><span class=\"muted\">raw rows</span></div></section>
    <section class=\"panel\">{table}</section>
    """
    return _layout("Raw records", body, active="raw")


def _scores_page(data: dict[str, Any]) -> str:
    rows = []
    for item in data['items']:
        company = item.get('company')
        company_cell = f'<code>{html.escape(item.get("company_key") or "")}</code>'
        if company:
            company_cell = f'<a class="strong-link" href="/ui/companies/{company["id"]}">{html.escape(company.get("canonical_name") or "Company")}</a><div class="muted small"><code>{html.escape(item.get("company_key") or "")}</code></div>'
        rows.append(
            f"<tr><td>{company_cell}</td><td>{_score_badge(item.get('composite_score'))}</td><td>{_score_badge(item.get('relevance_score'))}</td><td>{_score_badge(item.get('capability_fit_score'))}</td><td>{_score_badge(item.get('contactability_score'))}</td><td>{_score_badge(item.get('trust_score'))}</td><td>{_feedback_summary_badges(item.get('feedback'))}</td></tr>"
        )
    body_rows = ''.join(rows) or '<tr><td colspan=7 class="muted">No scores yet.</td></tr>'
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Scores</p><h1>Standalone scoring output</h1><p class="lead">Readable score breakdowns with direct links into the company workbench.</p></div><div class="panel panel-tight"><strong>{data['total']}</strong><span class="muted">score rows</span></div></section>
    <section class="panel"><table><thead><tr><th>Company</th><th>Composite</th><th>Relevance</th><th>Capability fit</th><th>Contactability</th><th>Trust</th><th>Feedback</th></tr></thead><tbody>{body_rows}</tbody></table></section>
    """
    return _layout("Scores", body, active='scores')


def _run_result_page(result: dict[str, Any]) -> str:
    report = result.get("pipeline_report") or {}
    counts = result.get("storage_counts") or {}
    body = f"""
    <section class=\"hero compact\"><div><p class=\"eyebrow\">Pipeline action</p><h1>Fixture pipeline run complete</h1><p class=\"lead\">Local operator action only. This executed the standalone supplier-intelligence pipeline against fixture-backed input.</p></div><div class=\"panel panel-tight\"><a class=\"button-link\" href=\"/\">Back to dashboard</a></div></section>
    <section class=\"grid two\">
      <div class=\"panel\"><h2>Run report</h2>{_dict_table(report)}</div>
      <div class=\"panel\"><h2>Storage counts</h2>{_dict_table(counts)}</div>
    </section>
    <section class=\"panel\"><p>Next steps: <a href=\"/ui/companies\">inspect companies</a>, <a href=\"/ui/review-queue\">review queue</a>, or <a href=\"/ui/raw-records\">raw records</a>.</p></section>
    """
    return _layout("Pipeline run", body, active="dashboard")


def _sample_feedback_result_page(result: dict[str, Any]) -> str:
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Feedback action</p><h1>Sample feedback loaded</h1><p class="lead">Local-only helper action. It seeds synthetic downstream feedback events so the operator panel is inspectable without waiting on external systems.</p></div><div class="panel panel-tight"><a class="button-link" href="/ui/feedback-status">Open feedback status</a></div></section>
    <section class="grid two"><div class="panel"><h2>Action result</h2>{_dict_table({'accepted': result.get('accepted'), 'generated': result.get('generated'), 'companies_used': result.get('companies_used')})}</div><div class="panel"><h2>Storage counts</h2>{_dict_table(result.get('storage_counts') or {})}</div></section>
    <section class="panel"><p>Next steps: <a href="/ui/feedback-status">inspect feedback projection</a>, <a href="/ui/feedback-events">audit the feedback ledger</a>, or <a href="/ui/companies">open companies</a>.</p></section>
    """
    return _layout('Sample feedback', body, active='feedback')


def _decision_result_page(data: dict[str, Any]) -> str:
    company = data["company"]
    result = data["result"]
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone workflow action</p><h1>Decision applied</h1><p class="lead">The standalone operations domain is now the owner of this supplier routing/qualification decision.</p></div><div class="panel panel-tight"><a class="button-link" href="/ui/companies/{int(company.get('id') or 0)}">Back to company workbench</a></div></section>
    <section class="grid two">
      <div class="panel"><h2>Company</h2>{_dict_table({"canonical_name": company.get("canonical_name"), "canonical_key": company.get("canonical_key")})}</div>
      <div class="panel"><h2>Decision result</h2>{_dict_table({"outcome": result.outcome, "reason_code": result.reason_code, "queue_name": result.queue_name, "score": result.score, "outreach_ready": result.outreach_ready, "rfq_ready": result.rfq_ready})}</div>
    </section>
    """
    return _layout("Decision applied", body, active="companies")


def _commercial_result_page(data: dict[str, Any]) -> str:
    company = data["company"]
    record = data["commercial_record"]
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone commercial action</p><h1>Commercial state saved</h1><p class="lead">This company now has standalone-owned commercial follow-up state. It is editable here and no longer needs to hide behind downstream CRM snapshots.</p></div><div class="panel panel-tight"><div class="button-row"><a class="button-link" href="/ui/companies/{int(company.get('id') or 0)}">Back to company workbench</a><a class="button-link ghost" href="/ui/commercial-pipeline">Open commercial pipeline</a></div></div></section>
    <section class="grid two">
      <div class="panel"><h2>Company</h2>{_dict_table({"canonical_name": company.get("canonical_name"), "canonical_key": company.get("canonical_key")})}</div>
      <div class="panel"><h2>Commercial state</h2>{_dict_table({"customer_status": record.get("customer_status"), "commercial_stage": record.get("commercial_stage"), "customer_reference": record.get("customer_reference"), "opportunity_reference": record.get("opportunity_reference"), "next_action": record.get("next_action"), "next_action_due_at": record.get("next_action_due_at"), "notes": record.get("notes")})}</div>
    </section>
    """
    return _layout("Commercial state saved", body, active="commercial")


def _customer_account_result_page(data: dict[str, Any]) -> str:
    company = data["company"]
    record = data["customer_account"]
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone customer account action</p><h1>Customer account saved</h1><p class="lead">The active commercial contour now has a standalone-owned customer/account identity instead of relying on Odoo partner ownership.</p></div><div class="panel panel-tight"><div class="button-row"><a class="button-link" href="/ui/companies/{int(company.get('id') or 0)}">Back to company workbench</a><a class="button-link ghost" href="/ui/opportunities?company_id={int(company.get('id') or 0)}">Open opportunities</a></div></div></section>
    <section class="grid two"><div class="panel"><h2>Company</h2>{_dict_table({"canonical_name": company.get("canonical_name"), "canonical_key": company.get("canonical_key")})}</div><div class="panel"><h2>Customer account</h2>{_dict_table({"account_name": record.get("account_name"), "account_type": record.get("account_type"), "account_status": record.get("account_status"), "primary_contact_name": record.get("primary_contact_name"), "primary_email": record.get("primary_email"), "primary_phone": record.get("primary_phone"), "billing_city": record.get("billing_city"), "external_customer_ref": record.get("external_customer_ref")})}</div></section>
    """
    return _layout("Customer account saved", body, active="commercial")


def _opportunity_result_page(data: dict[str, Any], updated: bool = False) -> str:
    company = data["company"]
    record = data["opportunity"]
    title = "Opportunity saved" if updated else "Opportunity created"
    lead = "Standalone opportunity ownership is updated here." if updated else "Standalone opportunity ownership now exists for this company without depending on Odoo CRM lead state."
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone opportunity action</p><h1>{title}</h1><p class="lead">{lead}</p></div><div class="panel panel-tight"><div class="button-row"><a class="button-link" href="/ui/companies/{int(company.get('id') or 0)}">Back to company workbench</a><a class="button-link ghost" href="/ui/opportunities/{int(record.get('id') or 0)}">Open opportunity</a><a class="button-link ghost" href="/ui/opportunities?company_id={int(company.get('id') or 0)}">Open opportunity list</a></div></div></section>
    <section class="grid two"><div class="panel"><h2>Company</h2>{_dict_table({"canonical_name": company.get("canonical_name"), "canonical_key": company.get("canonical_key")})}</div><div class="panel"><h2>Opportunity</h2>{_dict_table({"title": record.get("title"), "status": record.get("status"), "source_channel": record.get("source_channel"), "estimated_value": record.get("estimated_value"), "currency_code": record.get("currency_code"), "target_due_at": record.get("target_due_at"), "next_action": record.get("next_action"), "external_opportunity_ref": record.get("external_opportunity_ref")})}</div></section>
    """
    return _layout(title, body, active="commercial")


def _quote_intent_result_page(data: dict[str, Any], updated: bool = False) -> str:
    company = data["company"]
    record = data["quote_intent"]
    company_id = int(company.get('id') or 0) if company else 0
    company_name = company.get("canonical_name") if company else "Unmatched"
    company_key = company.get("canonical_key") if company else record.get("company_key")
    title = "Quote workflow saved" if updated else "Quote intent created"
    lead = (
        "This standalone quote workflow is updated here. It should not need an Odoo quote object just to track pricing progress."
        if updated
        else "This request is now tracked in standalone. It no longer needs to start life as an Odoo-only quote or order artifact."
    )
    company_actions = '<span class="muted">No company workbench link</span>'
    if company_id:
        company_actions = f'<a class="button-link" href="/ui/companies/{company_id}">Back to company workbench</a>'
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone quote action</p><h1>{title}</h1><p class="lead">{lead}</p></div><div class="panel panel-tight"><div class="button-row">{company_actions}<a class="button-link ghost" href="/ui/quote-intents/{int(record.get('id') or 0)}">Open quote workbench</a><a class="button-link ghost" href="/ui/quote-intents">Open quote intents</a></div></div></section>
    <section class="grid two">
      <div class="panel"><h2>Company</h2>{_dict_table({"canonical_name": company_name, "canonical_key": company_key})}</div>
      <div class="panel"><h2>Quote intent</h2>{_dict_table({"quote_type": record.get("quote_type"), "quantity_hint": record.get("quantity_hint"), "target_due_at": record.get("target_due_at"), "status": record.get("status"), "quote_reference": record.get("quote_reference"), "quoted_amount": record.get("quoted_amount"), "currency_code": record.get("currency_code"), "pricing_notes": record.get("pricing_notes"), "notes": record.get("notes")})}</div>
    </section>
    """
    return _layout(title, body, active="quotes")


def _production_handoff_result_page(data: dict[str, Any], updated: bool = False) -> str:
    company = data.get("company")
    record = data["production_handoff"]
    title = "Production handoff saved" if updated else "Production handoff created"
    lead = (
        "This execution handoff is updated in standalone. It should not require an ERP order object just to track production readiness."
        if updated
        else "This execution handoff is now tracked in standalone. It bridges quote/commercial state into delivery planning without dragging in full ERP flow."
    )
    company_link = '<span class="muted">No company workbench link</span>'
    if company:
        company_link = f'<a class="button-link" href="/ui/companies/{int(company.get("id") or 0)}">Back to company workbench</a>'
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone production action</p><h1>{title}</h1><p class="lead">{lead}</p></div><div class="panel panel-tight"><div class="button-row">{company_link}<a class="button-link ghost" href="/ui/production-handoffs/{int(record.get('id') or 0)}">Open production handoff</a><a class="button-link ghost" href="/ui/production-handoffs">Open production handoffs</a></div></div></section>
    <section class="grid two">
      <div class="panel"><h2>Handoff</h2>{_dict_table({"handoff_status": record.get("handoff_status"), "production_reference": record.get("production_reference"), "requested_ship_at": record.get("requested_ship_at"), "specification_summary": record.get("specification_summary"), "notes": record.get("notes")})}</div>
      <div class="panel"><h2>Context</h2>{_dict_table({"company_key": record.get("company_key"), "quote_intent_id": record.get("quote_intent_id")})}</div>
    </section>
    """
    return _layout(title, body, active="handoffs")


def _queue_transition_result_page(data: dict[str, Any]) -> str:
    queue_item = data.get("queue_item") or {}
    company = data.get("company")
    action = '<a class="button-link" href="/ui/review-queue">Back to review queue</a>'
    if company:
        action = f'<a class="button-link" href="/ui/companies/{int(company.get("id") or 0)}">Back to company workbench</a>'
    body = f"""
    <section class="hero compact"><div><p class="eyebrow">Standalone workflow action</p><h1>Queue transition applied</h1><p class="lead">Manual queue transition is now recorded in standalone routing audit instead of Odoo queue state.</p></div><div class="panel panel-tight">{action}</div></section>
    <section class="panel"><h2>Queue row</h2>{_dict_table(queue_item or {"status": "missing"})}</section>
    """
    return _layout("Queue transition", body, active="review")


def _layout(title: str, body: str, active: str) -> str:
    return _page(
        title,
        f"""
        <header class=\"topbar\">
          <div class=\"brand\"><a href=\"/\">MagonOS Standalone</a></div>
          <nav class=\"nav\">
            {_nav_link('dashboard', '/', 'Dashboard', active)}
            {_nav_link('companies', '/ui/companies', 'Companies', active)}
            {_nav_link('commercial', '/ui/commercial-pipeline', 'Commercial', active)}
            {_nav_link('quotes', '/ui/quote-intents', 'Quotes', active)}
            {_nav_link('handoffs', '/ui/production-handoffs', 'Handoffs', active)}
            {_nav_link('production-board', '/ui/production-board', 'Production', active)}
            {_nav_link('workforce', '/ui/workforce', 'Workforce', active)}
            {_nav_link('review', '/ui/review-queue', 'Review queue', active)}
            {_nav_link('feedback', '/ui/feedback-status', 'Feedback', active)}
            {_nav_link('feedback-events', '/ui/feedback-events', 'Feedback audit', active)}
            {_nav_link('raw', '/ui/raw-records', 'Raw records', active)}
            {_nav_link('scores', '/ui/scores', 'Scores', active)}
          </nav>
          <div class="header-tools">
            {_language_toggle()}
          </div>
        </header>
        <main class=\"main\">{body}</main>
        {_language_toggle_script()}
        """,
    )


def _page(title: str, body: str) -> str:
    localized_title = _translate_exact(title)
    localized_body = _localize_html_fragment(body)
    return (
        "<!doctype html><html lang=\""
        + html.escape(_current_locale())
        + "\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>"
        + html.escape(localized_title)
        + "</title><style>"
        + _style()
        + "</style></head><body>"
        + localized_body
        + "</body></html>"
    )


def _style() -> str:
    return """
    :root{--bg:#f6f7fb;--panel:#fff;--text:#1f2937;--muted:#6b7280;--line:#e5e7eb;--accent:#0f766e;--accent-soft:#ccfbf1;--blue:#1d4ed8;--blue-soft:#dbeafe;--amber:#b45309;--amber-soft:#fef3c7;--red:#b91c1c;--red-soft:#fee2e2;--gray-soft:#f3f4f6;--shadow:0 10px 30px rgba(15,23,42,.06)}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:inherit}code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}pre{white-space:pre-wrap;word-break:break-word;background:#0b1220;color:#dbeafe;padding:12px;border-radius:10px;overflow:auto}header.topbar{display:flex;justify-content:space-between;align-items:center;padding:18px 24px;border-bottom:1px solid var(--line);background:#fff;position:sticky;top:0;z-index:20;gap:16px}.brand a{text-decoration:none;font-weight:700;font-size:18px}.nav{display:flex;gap:10px;flex-wrap:wrap;flex:1}.nav a{text-decoration:none;padding:8px 12px;border-radius:999px;color:var(--muted);background:transparent}.nav a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}.header-tools{display:flex;align-items:center;justify-content:flex-end}.lang-toggle{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;background:#fff;padding:4px}.lang-toggle button{min-width:44px;padding:8px 12px;border:none;background:transparent;color:var(--muted);border-radius:999px;box-shadow:none}.lang-toggle button.active{background:var(--accent-soft);color:var(--accent);font-weight:700}.main{max-width:1360px;margin:0 auto;padding:24px}.hero{display:grid;grid-template-columns:1.4fr .8fr;gap:16px;align-items:start;margin-bottom:20px}.hero.compact{grid-template-columns:1fr auto}.eyebrow{margin:0 0 6px;color:var(--accent);font-weight:700;text-transform:uppercase;letter-spacing:.08em;font-size:12px}.lead{margin:8px 0 0;color:var(--muted);max-width:900px}h1{margin:0;font-size:34px;line-height:1.1}h2{margin:0 0 12px;font-size:20px}section{margin-bottom:20px}.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:var(--shadow)}.panel-accent{border-color:#bfe7e2;background:#f7fffd}.panel-tight{padding:14px}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.cards.compact{grid-template-columns:repeat(2,minmax(0,1fr))}.stat-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow)}.stat-value{font-size:28px;font-weight:700;margin:4px 0}.muted{color:var(--muted)}.small{font-size:12px}.grid.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}.link-list{margin:0;padding-left:18px}.link-list li{margin:8px 0}.toolbar{display:grid;grid-template-columns:minmax(220px,1fr) repeat(4,minmax(0,180px));gap:10px;margin-bottom:14px;align-items:end}.toolbar input,.toolbar select,.stack input,.stack select,.inline-form select{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:#fff}.stack{display:grid;gap:10px}.stack label{display:grid;gap:6px;color:var(--muted);font-size:12px}.inline-form{display:flex;gap:8px;align-items:center;min-width:240px}.button-link,button{display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:#fff;text-decoration:none;font-weight:600;cursor:pointer}.button-link{width:max-content}.button-link.ghost{background:#fff;color:var(--accent)}.button-row{display:flex;flex-wrap:wrap;gap:10px}.button-link:hover,button:hover{opacity:.95}.nav-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px;text-decoration:none;display:block}.nav-card strong{display:block;margin-bottom:6px}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);background:#fafafa;position:sticky;top:68px}.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap}.badge.neutral{background:var(--gray-soft);color:#374151}.badge.success{background:var(--accent-soft);color:var(--accent)}.badge.info{background:var(--blue-soft);color:var(--blue)}.badge.warn{background:var(--amber-soft);color:var(--amber)}.badge.danger{background:var(--red-soft);color:var(--red)}.badge.accent{background:#ede9fe;color:#6d28d9}.chips{display:flex;flex-wrap:wrap;gap:6px}.strong-link{font-weight:700;text-decoration:none}.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.detail-grid .span-2{grid-column:span 2}.field-label{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin-bottom:6px}.field-value{font-size:15px}.card-note{font-size:13px;color:var(--muted)}.activity-table td:first-child{width:120px}.empty{padding:18px;border:1px dashed var(--line);border-radius:12px;color:var(--muted);background:#fcfcfd}.kicker{margin-bottom:8px}.split{display:flex;justify-content:space-between;gap:16px;align-items:center}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}.nowrap{white-space:nowrap}@media (max-width:1100px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.toolbar{grid-template-columns:1fr 1fr}.hero,.grid.two,.cards.compact,.detail-grid{grid-template-columns:1fr}.detail-grid .span-2{grid-column:auto}.inline-form{flex-direction:column;align-items:stretch}}@media (max-width:860px){header.topbar{padding:14px 16px;align-items:flex-start;flex-direction:column}.header-tools{width:100%;justify-content:flex-start}.main{padding:16px}.cards{grid-template-columns:1fr}.toolbar{grid-template-columns:1fr}h1{font-size:28px}th{top:148px}}
    """


def _language_toggle() -> str:
    locale = _current_locale()
    ru_class = "active" if locale == "ru" else ""
    en_class = "active" if locale == "en" else ""
    return (
        f'<div class="lang-toggle" role="group" aria-label="{html.escape(_translate_exact("Interface language"))}">'
        f'<button type="button" class="{ru_class}" data-locale-switch="ru">RU</button>'
        f'<button type="button" class="{en_class}" data-locale-switch="en">EN</button>'
        "</div>"
    )


def _language_toggle_script() -> str:
    return f"""
    <script>
    document.addEventListener('click', function(event) {{
      const button = event.target.closest('[data-locale-switch]');
      if (!button) {{
        return;
      }}
      document.cookie = '{LOCALE_COOKIE_NAME}=' + button.getAttribute('data-locale-switch') + '; path=/; max-age=31536000; samesite=lax';
      window.location.reload();
    }});
    </script>
    """


def _nav_link(key: str, href: str, label: str, active: str) -> str:
    class_name = "active" if key == active else ""
    return f'<a class="{class_name}" href="{href}">{html.escape(label)}</a>'


def _nav_card(title: str, href: str, body: str) -> str:
    return f'<a class="nav-card" href="{href}"><strong>{html.escape(title)}</strong><span class="card-note">{html.escape(body)}</span></a>'


def _stat_card(title: str, value: Any, note: str) -> str:
    return f'<div class="stat-card"><div class="muted small">{html.escape(title)}</div><div class="stat-value">{html.escape(str(value))}</div><div class="card-note">{html.escape(note)}</div></div>'


def _dict_table(data: dict[str, Any]) -> str:
    if not data:
        return f'<p class="muted">{html.escape(_translate_exact("No data."))}</p>'
    rows = ''.join(f'<tr><th>{html.escape(_labelize(str(k)))}</th><td>{html.escape(str(v))}</td></tr>' for k, v in data.items())
    return f'<table><tbody>{rows}</tbody></table>'


def _chips(values: list[str], tone: str = "neutral") -> str:
    if not values:
        return ""
    return f'<div class="chips">{"".join(_badge(_labelize(v), tone) for v in values)}</div>'


def _badge(label: str, tone: str = "neutral") -> str:
    return f'<span class="badge {tone}">{html.escape(_translate_exact(label))}</span>'


def _bool_badge(value: bool, yes: str, no: str) -> str:
    return _badge(yes if value else no, 'success' if value else 'neutral')


def _score_badge(value: Any) -> str:
    if value in {None, ""}:
        return '<span class="muted">—</span>'
    try:
        score = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    if score >= 0.8:
        tone = 'success'
    elif score >= 0.6:
        tone = 'info'
    elif score >= 0.4:
        tone = 'warn'
    else:
        tone = 'danger'
    return _badge(f'{score:.2f}', tone)


def _money(value: Any, currency_code: str = "VND") -> str:
    if value in {None, ""}:
        return '<span class="muted">—</span>'
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return html.escape(str(value))
    return html.escape(f"{amount:,.0f} {currency_code}".replace(",", " "))


def _feedback_badge(value: Any) -> str:
    if not value:
        return '<span class="muted">—</span>'
    tone = 'info'
    lowered = str(value).lower()
    if any(token in lowered for token in ['approved', 'qualified', 'linked']):
        tone = 'success'
    elif any(token in lowered for token in ['reject', 'unreachable', 'not_relevant']):
        tone = 'danger'
    elif any(token in lowered for token in ['review', 'pending', 'needs']):
        tone = 'warn'
    return _badge(_labelize(str(value)), tone)


def _feedback_summary_badges(item: dict[str, Any] | None) -> str:
    if not item:
        return f'<span class="muted">{html.escape(_translate_exact("No feedback"))}</span>'
    badges = []
    if item.get('routing_outcome'):
        badges.append(_feedback_badge(item.get('routing_outcome')))
    if item.get('qualification_status'):
        badges.append(_feedback_badge(item.get('qualification_status')))
    if item.get('lead_status'):
        badges.append(_feedback_badge(item.get('lead_status')))
    if item.get('partner_linked'):
        badges.append(_badge('Partner linked', 'success'))
    if _projection_is_synthetic(item):
        badges.append(_synthetic_badge())
    return ' '.join(badges) or f'<span class="muted">{html.escape(_translate_exact("No feedback"))}</span>'


def _projection_is_synthetic(item: dict[str, Any] | None) -> bool:
    if not item:
        return False
    return any(
        bool(item.get(flag))
        for flag in ['routing_is_synthetic', 'qualification_is_synthetic', 'partner_is_synthetic', 'commercial_is_synthetic', 'last_event_is_synthetic']
    )


def _synthetic_badge() -> str:
    return _badge('Synthetic sample', 'warn')


def _feedback_event_outcome_summary(item: dict[str, Any]) -> str:
    event_type = item.get('event_type') or ''
    if event_type == 'routing_feedback':
        return ' / '.join(part for part in [_labelize(str(item.get('routing_outcome') or '')) if item.get('routing_outcome') else '', _labelize(str(item.get('manual_review_status') or '')) if item.get('manual_review_status') else ''] if part) or _translate_exact('Routing update')
    if event_type == 'qualification_feedback':
        return _labelize(str(item.get('qualification_status') or 'Qualification update'))
    if event_type == 'partner_linkage_feedback':
        return _translate_exact('Partner linked') if item.get('partner_linked') else _translate_exact('Partner linkage update')
    if event_type == 'commercial_disposition_feedback':
        return _labelize(str(item.get('lead_status') or 'Commercial update'))
    return _labelize(str(event_type or 'Feedback event'))


def _summarize_raw_lists(item: dict[str, Any]) -> str:
    parts = []
    if item.get('categories'):
        parts.append('categories: ' + ', '.join(item.get('categories')[:3]))
    if item.get('services'):
        parts.append('services: ' + ', '.join(item.get('services')[:3]))
    if item.get('products'):
        parts.append('products: ' + ', '.join(item.get('products')[:3]))
    return ' | '.join(parts)


def _queue_tone(queue_name: str) -> str:
    return {
        'qualification_review': 'success',
        'supplier_review': 'info',
        'dedup_review': 'warn',
    }.get(queue_name, 'neutral')


def _recent_activity_table(items: list[dict[str, str]]) -> str:
    if not items:
        return f'<div class="empty">{html.escape(_translate_exact("No recent activity yet."))}</div>'
    rows = ''.join(
        f'<tr><td class="nowrap">{html.escape(item.get("timestamp") or "—")}</td><td>{_badge(_labelize(item.get("kind") or "item"), "neutral")}</td><td>{_maybe_link(item.get("title") or "—", item.get("href"))}</td><td>{html.escape(item.get("detail") or "—")}</td></tr>'
        for item in items
    )
    return f'<table class="activity-table"><thead><tr><th>Time</th><th>Kind</th><th>Title</th><th>Detail</th></tr></thead><tbody>{rows}</tbody></table>'


def _commercial_audit_table(items: list[dict[str, Any]]) -> str:
    if not items:
        return f'<div class="empty">{html.escape(_translate_exact("No commercial audit yet."))}</div>'
    rows = ''.join(
        f"<tr><td>{html.escape(item.get('occurred_at') or '—')}</td><td>{_badge(_labelize(item.get('entity_type') or ''), 'neutral')}</td><td>{html.escape(item.get('action_type') or '—')}</td><td>{html.escape(item.get('previous_status') or '—')}</td><td>{html.escape(item.get('new_status') or '—')}</td><td>{html.escape(item.get('note') or '—')}</td></tr>"
        for item in items
    )
    return f'<table><thead><tr><th>When</th><th>Entity</th><th>Action</th><th>From</th><th>To</th><th>Note</th></tr></thead><tbody>{rows}</tbody></table>'


def _maybe_link(label: str, href: str | None) -> str:
    if not href:
        return html.escape(label)
    return f'<a class="strong-link" href="{html.escape(href)}">{html.escape(label)}</a>'


def _external_link(url: str | None) -> str:
    if not url:
        return '—'
    safe = html.escape(url)
    label = html.escape(_truncate(url, 44, with_markup=False))
    return f'<a href="{safe}" target="_blank" rel="noreferrer">{label}</a>'


def _truncate(value: str | None, limit: int, with_markup: bool = True) -> str:
    if not value:
        return '—' if with_markup else ''
    text = value if len(value) <= limit else value[: limit - 1] + '…'
    return html.escape(text) if with_markup else text


def _labelize(value: str) -> str:
    if not value:
        return ""
    normalized = value.strip()
    lowered = normalized.lower()
    if lowered in _UI_VALUE_LABEL_RU and _current_locale() == "ru":
        return _UI_VALUE_LABEL_RU[lowered]
    if lowered in _UI_LABEL_RU and _current_locale() == "ru":
        return _UI_LABEL_RU[lowered]
    return _translate_exact(normalized.replace('_', ' ').replace('-', ' ').strip().title())


def _query_value(query: dict[str, list[str]], key: str) -> str:
    return (query.get(key, [''])[0] or '').strip()


def _pagination(query: dict[str, list[str]]) -> dict[str, int]:
    return {'limit': max(1, min(int(query.get('limit', ['50'])[0]), 500)), 'offset': max(0, int(query.get('offset', ['0'])[0]))}


def _options(empty_label: str, values: list[str], selected: str) -> str:
    options = [f'<option value="">{html.escape(empty_label)}</option>']
    for value in values:
        is_selected = ' selected' if value == selected else ''
        options.append(f'<option value="{html.escape(value)}"{is_selected}>{html.escape(value)}</option>')
    return ''.join(options)


def _simple_options(options: list[tuple[str, str]], selected: str) -> str:
    parts = []
    for value, label in options:
        is_selected = ' selected' if value == selected else ''
        parts.append(f'<option value="{html.escape(value)}"{is_selected}>{html.escape(label)}</option>')
    return ''.join(parts)


def _workforce_input_from_json(payload: dict[str, Any]) -> WorkforceEstimateInput:
    return WorkforceEstimateInput(
        specification_id=_optional_int(payload.get("specification_id")),
        process_type=str(payload.get("process_type") or ""),
        quantity=float(payload.get("quantity") or 0.0),
        complexity_level=str(payload.get("complexity_level") or "medium"),
        target_completion_hours=_optional_float(payload.get("target_completion_hours")),
        role_demands=[WorkforceRoleDemand(**item) for item in _typed_list(payload.get("role_demands"), "role_demands")],
        shift_capacities=[ShiftCapacityInput(**item) for item in _typed_list(payload.get("shift_capacities"), "shift_capacities")],
        labor_rates=[LaborRateInput(**item) for item in _typed_list(payload.get("labor_rates"), "labor_rates")],
        policies=[LaborPolicyInput(**item) for item in _typed_list(payload.get("policies"), "policies")],
    )


def _workforce_result_to_json(result: Any) -> dict[str, Any]:
    return asdict(result)


def _typed_list(value: Any, field_name: str) -> list[dict[str, Any]]:
    if value is None or value == "":
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name}_must_be_list")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{field_name}_items_must_be_objects")
    return value


def _optional_int(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _parse_json_body(environ: dict[str, Any]) -> dict[str, Any]:
    try:
        length = int(environ.get('CONTENT_LENGTH', '0') or '0')
    except ValueError as exc:
        raise ValueError('invalid_content_length') from exc
    raw_body = environ['wsgi.input'].read(length) if length else b'{}'
    if not raw_body:
        return {}
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except json.JSONDecodeError as exc:
        raise ValueError('invalid_json_body') from exc
    if not isinstance(payload, dict):
        raise ValueError('json_body_must_be_object')
    return payload


def _parse_form_body(environ: dict[str, Any]) -> dict[str, str]:
    try:
        length = int(environ.get('CONTENT_LENGTH', '0') or '0')
    except ValueError as exc:
        raise ValueError('invalid_content_length') from exc
    raw_body = environ['wsgi.input'].read(length) if length else b''
    parsed = parse_qs(raw_body.decode('utf-8'), keep_blank_values=False)
    return {key: values[0] for key, values in parsed.items() if values}


def _sample_feedback_payloads(companies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for index, company in enumerate(companies[:3], start=1):
        source_key = company.get('canonical_key') or f'company-{index}'
        company_id = int(company.get('id') or index)
        vendor_profile_id = 1000 + index
        payloads.append({
            'event_id': f'sample-routing-{source_key}',
            'source_key': source_key,
            'source_system': 'odoo',
            'event_type': 'routing_feedback',
            'event_version': 'routing:v1',
            'occurred_at': f'2026-04-16T0{index}:00:00Z',
            'payload_hash': f'sample-routing-{source_key}',
            'company_id': company_id,
            'vendor_profile_id': vendor_profile_id,
            'routing_outcome': 'potential_supplier' if index == 1 else 'needs_review',
            'manual_review_status': 'ready_for_follow_up' if index == 1 else 'in_review',
            'reason_code': 'sample_seed',
            'notes': 'Local sample feedback seeded for operator console.',
            'is_manual_override': index != 1,
            'is_synthetic': True,
            'payload': {
                'routing_outcome': 'potential_supplier' if index == 1 else 'needs_review',
                'manual_review_status': 'ready_for_follow_up' if index == 1 else 'in_review',
                'reason_code': 'sample_seed',
                'notes': 'Local sample feedback seeded for operator console.',
                'is_manual_override': index != 1,
            },
        })
        payloads.append({
            'event_id': f'sample-qualification-{source_key}',
            'source_key': source_key,
            'source_system': 'odoo',
            'event_type': 'qualification_feedback',
            'event_version': 'qualification:v1',
            'occurred_at': f'2026-04-16T0{index}:10:00Z',
            'payload_hash': f'sample-qualification-{source_key}',
            'company_id': company_id,
            'vendor_profile_id': vendor_profile_id,
            'qualification_decision_id': 2000 + index,
            'qualification_status': 'qualified' if index == 1 else 'needs_manual_review',
            'reason_code': 'sample_seed',
            'notes': 'Qualification sample fed back from downstream ops.',
            'is_manual_override': index == 2,
            'is_synthetic': True,
            'payload': {
                'qualification_decision_id': 2000 + index,
                'qualification_status': 'qualified' if index == 1 else 'needs_manual_review',
                'reason_code': 'sample_seed',
                'notes': 'Qualification sample fed back from downstream ops.',
                'is_manual_override': index == 2,
            },
        })
        if index == 1:
            payloads.append({
                'event_id': f'sample-partner-{source_key}',
                'source_key': source_key,
                'source_system': 'odoo',
                'event_type': 'partner_linkage_feedback',
                'event_version': 'partner:v1',
                'occurred_at': '2026-04-16T01:20:00Z',
                'payload_hash': f'sample-partner-{source_key}',
                'company_id': company_id,
                'vendor_profile_id': vendor_profile_id,
                'partner_id': 3001,
                'partner_linked': True,
                'is_synthetic': True,
                'payload': {
                    'partner_id': 3001,
                    'partner_linked': True,
                },
            })
            payloads.append({
                'event_id': f'sample-commercial-{source_key}',
                'source_key': source_key,
                'source_system': 'odoo',
                'event_type': 'commercial_disposition_feedback',
                'event_version': 'commercial:v1',
                'occurred_at': '2026-04-16T01:30:00Z',
                'payload_hash': f'sample-commercial-{source_key}',
                'company_id': company_id,
                'vendor_profile_id': vendor_profile_id,
                'crm_lead_id': 4001,
                'lead_mapping_id': 5001,
                'lead_status': 'qualified',
                'crm_linked': True,
                'reason_code': 'sample_seed',
                'notes': 'Commercial disposition seeded for local inspection.',
                'is_synthetic': True,
                'payload': {
                    'crm_lead_id': 4001,
                    'lead_mapping_id': 5001,
                    'lead_status': 'qualified',
                    'crm_linked': True,
                    'reason_code': 'sample_seed',
                    'notes': 'Commercial disposition seeded for local inspection.',
                },
            })
    return payloads


def _feedback_event_from_json(payload: dict[str, Any]):
    from .contracts import FeedbackEventPayload

    if not isinstance(payload, dict):
        raise ValueError('feedback_event_must_be_object')
    event = FeedbackEventPayload(
        event_id=str(payload['event_id']),
        source_key=str(payload['source_key']),
        source_system='odoo',
        event_type=str(payload['event_type']),
        event_version=str(payload['event_version']),
        occurred_at=str(payload['occurred_at']),
        payload_hash=str(payload['payload_hash']),
        company_id=_optional_int(payload.get('company_id')),
        vendor_profile_id=_optional_int(payload.get('vendor_profile_id')),
        qualification_decision_id=_optional_int(payload.get('qualification_decision_id')),
        partner_id=_optional_int(payload.get('partner_id')),
        crm_lead_id=_optional_int(payload.get('crm_lead_id')),
        lead_mapping_id=_optional_int(payload.get('lead_mapping_id')),
        routing_outcome=_optional_str(payload.get('routing_outcome')),
        manual_review_status=_optional_str(payload.get('manual_review_status')),
        qualification_status=_optional_str(payload.get('qualification_status')),
        lead_status=_optional_str(payload.get('lead_status')),
        partner_linked=bool(payload.get('partner_linked')),
        crm_linked=bool(payload.get('crm_linked')),
        reason_code=_optional_str(payload.get('reason_code')),
        notes=_optional_str(payload.get('notes')),
        is_manual_override=bool(payload.get('is_manual_override')),
        is_synthetic=bool(payload.get('is_synthetic')),
        payload=payload.get('payload') or {},
    )
    return validate_feedback_event(event)


def _token_allowed(environ: dict[str, Any], expected_token: str | None) -> bool:
    if not expected_token:
        return True
    return environ.get('HTTP_X_INTEGRATION_TOKEN') == expected_token


def _optional_int(value: Any) -> int | None:
    return None if value in {None, '', False} else int(value)


def _optional_str(value: Any) -> str | None:
    if value in {None, '', False}:
        return None
    return str(value)


def _json_response(start_response: Callable, status_code: int, payload: dict[str, Any]) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
    start_response(f'{status_code} {_reason_phrase(status_code)}', [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(body)))])
    return [body]


def _html_response(start_response: Callable, status_code: int, body: str) -> list[bytes]:
    data = body.encode('utf-8')
    start_response(f'{status_code} {_reason_phrase(status_code)}', [('Content-Type', 'text/html; charset=utf-8'), ('Content-Length', str(len(data)))])
    return [data]


def _reason_phrase(status_code: int) -> str:
    return {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 500: 'Internal Server Error'}.get(status_code, 'OK')
