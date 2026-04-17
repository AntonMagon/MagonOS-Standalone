import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiServer, SupplierIntelligenceApiService


class TestStandaloneApi(unittest.TestCase):
    # RU: Набор страхует legacy intelligence UI/API и русскую локализацию как часть рабочего операторского контура.
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'supplier_intelligence.sqlite3'
        self.fixture_path = Path(__file__).resolve().parent / 'fixtures' / 'vn_suppliers_raw.json'
        self.service = SupplierIntelligenceApiService(db_path=self.db_path)
        self.server = SupplierIntelligenceApiServer(self.service, host='127.0.0.1', port=0)
        self.thread = self.server.start_in_thread()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.tmpdir.cleanup()

    def test_dashboard_page_loads_with_operator_navigation(self):
        home = self._get_text('/')
        self.assertIn('Supplier intelligence console', home)
        self.assertIn('Run local fixture pipeline', home)
        self.assertIn('/ui/companies', home)
        self.assertIn('/ui/workforce', home)
        self.assertIn('/ui/feedback-status', home)
        self.assertIn('/ui/feedback-events', home)
        self.assertIn('Load sample feedback', home)
        self.assertIn('Recent companies', home)
        self.assertIn('Recent downstream feedback', home)

    def test_operator_pages_can_render_in_russian_with_language_cookie(self):
        home = self._get_text('/', headers={'Cookie': 'magonos-locale=ru'})
        companies_page = self._get_text('/ui/companies', headers={'Cookie': 'magonos-locale=ru'})

        self.assertIn('Консоль данных о поставщиках', home)
        self.assertIn('Язык интерфейса', home)
        self.assertIn('data-locale-switch="ru"', home)
        self.assertIn('Канонический реестр поставщиков', companies_page)
        self.assertIn('Поиск по компании, сайту, контакту или направлению', companies_page)
        self.assertNotIn('Capabilities', companies_page)
        self.assertNotIn('Raw records', home)

    def test_company_detail_renders_human_russian_labels(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']

        detail_page = self._get_text(f'/ui/companies/{company_id}', headers={'Cookie': 'magonos-locale=ru'})

        self.assertIn('Направления', detail_page)
        self.assertIn('Самоклеящиеся этикетки', detail_page)
        self.assertIn('Электронная почта', detail_page)
        self.assertIn('Отпечаток источника', detail_page)
        self.assertIn('Готово к контакту', detail_page)
        self.assertIn('Запрошен расчёт', detail_page)
        self.assertNotIn('Capabilities', detail_page)
        self.assertNotIn('Source fingerprint', detail_page)
        self.assertNotIn('Outreach ready', detail_page)
        self.assertNotIn('Label Self Adhesive', detail_page)

    def test_operator_pages_render_meaningful_content(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']

        companies_page = self._get_text('/ui/companies')
        detail_page = self._get_text(f'/ui/companies/{company_id}')
        queue_page = self._get_text('/ui/review-queue')
        raw_page = self._get_text('/ui/raw-records')
        feedback_page = self._get_text('/ui/feedback-status')
        feedback_audit_page = self._get_text('/ui/feedback-events')
        workforce_page = self._get_text(f'/ui/workforce?company_id={company_id}')
        commercial_page = self._get_text('/ui/commercial-pipeline')
        quote_page = self._get_text('/ui/quote-intents')
        handoff_page = self._get_text('/ui/production-handoffs')
        production_board = self._get_text('/ui/production-board')

        self.assertIn('Canonical supplier intelligence', companies_page)
        self.assertIn('Company workbench', detail_page)
        self.assertIn('Company overview', detail_page)
        self.assertIn('Standalone intelligence', detail_page)
        self.assertIn('Standalone workflow', detail_page)
        self.assertIn('Standalone commercial state', detail_page)
        self.assertIn('Save customer account', detail_page)
        self.assertIn('Opportunities', detail_page)
        self.assertIn('Commercial audit', detail_page)
        self.assertIn('Qualification decisions', detail_page)
        self.assertIn('Routing audit', detail_page)
        self.assertIn('Downstream feedback', detail_page)
        self.assertIn('Operator review workload', queue_page)
        self.assertIn('Source-side discovery view', raw_page)
        self.assertIn('Downstream outcome view', feedback_page)
        self.assertIn('Feedback event ledger', feedback_audit_page)
        self.assertIn('Standalone labor estimation', workforce_page)
        self.assertIn('Run workforce estimate', workforce_page)
        self.assertIn('Back to company workbench', workforce_page)
        self.assertIn('Standalone commercial follow-up', commercial_page)
        self.assertIn('Standalone RFQ / quote intake', quote_page)
        self.assertIn('Standalone execution handoff', handoff_page)
        self.assertIn('Standalone execution board', production_board)

    def test_company_filters_and_search_work(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        page = self._get_text('/ui/companies?search=Saigon&city=Ho%20Chi%20Minh%20City&capability=LABEL_SELF_ADHESIVE&has_feedback=no')
        self.assertIn('Saigon Label Print Jsc', page)
        self.assertNotIn('Minh Phat Packaging Co., Ltd', page)

    def test_local_operator_action_runs_fixture_pipeline(self):
        result_page = self._post_form('/ui/actions/run-pipeline', {'fixture': str(self.fixture_path), 'query': 'printing packaging vietnam', 'country': 'VN'})
        self.assertIn('Fixture pipeline run complete', result_page)
        self.assertIn('Canonical Companies', result_page)
        status = self._get_json('/status')
        self.assertEqual(status['storage_counts']['canonical_companies'], 2)

    def test_workforce_estimate_json_and_ui_are_usable(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']
        payload = {
            'specification_id': 999,
            'process_type': 'offset_printing',
            'quantity': 1000,
            'complexity_level': 'medium',
            'target_completion_hours': 16,
            'role_demands': [{'role_code': 'PRINT_OPERATOR', 'required_skill_codes': ['OFFSET'], 'hours_per_unit': 0.01, 'quantity_factor': 1.0}],
            'shift_capacities': [{'role_code': 'PRINT_OPERATOR', 'shift_hours': 8, 'worker_count': 2, 'absence_count': 0, 'available_skill_codes': ['OFFSET'], 'slot_available_hours': 16}],
            'labor_rates': [{'role_code': 'PRINT_OPERATOR', 'base_hourly_rate': 120000, 'overtime_multiplier': 1.5, 'overtime_threshold_hours': 8, 'currency_code': 'VND'}],
            'policies': [{'code': 'default_shift_hours', 'country_code': 'VN', 'value_float': 8.0}],
        }

        estimate = self._post_json('/workforce/estimate', payload)
        workforce_page = self._post_form(
            '/ui/actions/workforce-estimate',
            {'company_id': str(company_id), 'case': 'normal_shift', 'payload_json': json.dumps(payload)},
        )
        company_page = self._get_text(f'/ui/companies/{company_id}')

        self.assertEqual(estimate['result']['required_headcount'], 2)
        self.assertFalse(estimate['result']['overtime_required'])
        self.assertIn('Estimate summary', workforce_page)
        self.assertIn('Role breakdown', workforce_page)
        self.assertIn('PRINT_OPERATOR', workforce_page)
        self.assertIn('Back to company workbench', workforce_page)
        self.assertIn(f'/ui/workforce?company_id={company_id}', company_page)

    def test_feedback_seed_and_drilldown_pages_render(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        raw_records = self._get_json('/raw-records')

        feedback_seed = self._post_form('/ui/actions/load-sample-feedback', {})
        dashboard = self._get_text('/')
        company_detail = self._get_text(f"/ui/companies/{companies['items'][0]['id']}")
        feedback_page = self._get_text('/ui/feedback-status')
        feedback_detail = self._get_text(f"/ui/feedback-status/{companies['items'][0]['canonical_key']}")
        raw_detail = self._get_text(f"/ui/raw-records/{raw_records['items'][0]['id']}")
        feedback_events = self._get_text('/ui/feedback-events')
        scores_page = self._get_text('/ui/scores')

        self.assertIn('Sample feedback loaded', feedback_seed)
        self.assertIn('Synthetic sample', dashboard)
        self.assertIn('Downstream feedback', company_detail)
        self.assertIn('Synthetic sample', company_detail)
        company_href = f"/ui/companies/{companies['items'][0]['id']}"
        self.assertIn(company_href, feedback_page)
        self.assertIn('Feedback timeline', feedback_detail)
        self.assertIn('Back to company workbench', feedback_detail)
        self.assertIn('Raw record detail', raw_detail)
        self.assertIn('Back to company workbench', raw_detail)
        self.assertIn('Feedback event ledger', feedback_events)
        self.assertIn('Synthetic sample', feedback_events)
        self.assertIn(company_href, scores_page)

    def test_company_workflow_actions_write_standalone_state(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']
        detail_before = self._get_text(f'/ui/companies/{company_id}')
        self.assertIn('Apply standalone decision', detail_before)

        result_page = self._post_form(
            f'/ui/actions/companies/{company_id}/decide',
            {
                'outcome': 'approved_supplier',
                'reason_code': 'manual_operator_decision',
                'notes': 'Approved in standalone',
                'manual_override': 'yes',
            },
        )
        detail_after = self._get_text(f'/ui/companies/{company_id}')
        queue_page = self._get_text('/ui/review-queue')

        self.assertIn('Decision applied', result_page)
        self.assertIn('approved_supplier', result_page.lower())
        self.assertIn('Approved', detail_after)
        self.assertIn('qualified', detail_after.lower())
        self.assertIn('Routing audit', detail_after)
        self.assertIn('Approved in standalone', detail_after)
        self.assertIn('/ui/companies/', queue_page)

    def test_commercial_state_is_editable_in_standalone(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']

        result_page = self._post_form(
            f'/ui/actions/companies/{company_id}/commercial',
            {
                'customer_status': 'prospect',
                'commercial_stage': 'contacting',
                'customer_reference': 'CUST-42',
                'opportunity_reference': 'OPP-99',
                'next_action': 'Call buyer',
                'next_action_due_at': '2026-04-20',
                'notes': 'Initial commercial outreach',
            },
        )
        detail_after = self._get_text(f'/ui/companies/{company_id}')
        commercial_page = self._get_text('/ui/commercial-pipeline')

        self.assertIn('Commercial state saved', result_page)
        self.assertIn('Open commercial pipeline', result_page)
        self.assertIn('Standalone commercial state', detail_after)
        self.assertIn('Call buyer', detail_after)
        self.assertIn('CUST-42', detail_after)
        self.assertIn('Contacting', commercial_page)
        self.assertIn(f'/ui/companies/{company_id}', commercial_page)

    def test_quote_intent_is_editable_in_standalone(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']

        result_page = self._post_form(
            f'/ui/actions/companies/{company_id}/quote-intents',
            {
                'quote_type': 'rfq_packaging',
                'quantity_hint': '5000 boxes',
                'target_due_at': '2026-04-25',
                'status': 'requested',
                'notes': 'Urgent carton quote',
            },
        )
        detail_after = self._get_text(f'/ui/companies/{company_id}')
        quote_page = self._get_text('/ui/quote-intents')

        self.assertIn('Quote intent created', result_page)
        self.assertIn('Open quote intents', result_page)
        self.assertIn('Quote intents', detail_after)
        self.assertIn('5000 boxes', detail_after)
        self.assertIn('Urgent carton quote', detail_after)
        self.assertIn('Standalone RFQ / quote intake', quote_page)
        self.assertIn('rfq packaging', quote_page.lower())
        self.assertIn(f'/ui/companies/{company_id}', quote_page)
        quote_intents = self.service._store().list_quote_intents()
        detail_page = self._get_text(f"/ui/quote-intents/{quote_intents[0]['id']}")
        self.assertIn('Quote workbench', detail_page)
        self.assertIn(f'/ui/companies/{company_id}', detail_page)

    def test_request_draft_submit_flow_is_editable_in_standalone(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        company_id = companies['items'][0]['id']

        draft_result = self._post_form(
            f'/ui/actions/companies/{company_id}/request-drafts',
            {
                'draft_type': 'rfq_packaging',
                'customer_name': 'Anna Buyer',
                'customer_email': 'anna@example.co',
                'customer_phone': '+840000000',
                'item_summary': '5000 corrugated cartons',
                'quantity_hint': '5000 boxes',
                'city': 'Ho Chi Minh City',
                'requested_deadline': '2026-04-25',
                'file_required': 'yes',
                'file_links': 'https://files.example/spec.pdf',
                'notes': 'Initial intake',
            },
        )
        draft = self.service._store().list_request_drafts()[0]
        request_result = self._post_form(
            f"/ui/actions/request-drafts/{draft['id']}/submit",
            {
                'source_channel': 'web_form',
                'customer_reference': 'CUST-REQ-1',
                'request_status': 'needs_review',
                'notes': 'Escalate for operator review',
            },
        )

        company_page = self._get_text(f'/ui/companies/{company_id}')
        draft_list_page = self._get_text('/ui/request-drafts')
        request_list_page = self._get_text('/ui/requests')
        request = self.service._store().list_request_intakes()[0]
        draft_detail_page = self._get_text(f"/ui/request-drafts/{draft['id']}")
        request_detail_page = self._get_text(f"/ui/requests/{request['id']}")

        self.assertIn('Request draft created', draft_result)
        self.assertIn('Request created from draft', request_result)
        self.assertIn('Request drafts', company_page)
        self.assertIn('Requests', company_page)
        self.assertIn('5000 corrugated cartons', company_page)
        self.assertIn('needs review', request_list_page.lower())
        self.assertIn('Request drafts', draft_list_page)
        self.assertIn('REQ-', request_detail_page)
        self.assertIn('Submit into request', draft_detail_page)
        self.assertEqual(self.service._store().get_request_draft(draft['id'])['draft_status'], 'submitted')

    def test_standalone_commercial_ownership_boundary_is_editable_end_to_end(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company = self._get_json('/companies')['items'][0]
        company_id = int(company['id'])

        account_result = self._post_form(
            f'/ui/actions/companies/{company_id}/customer-account',
            {
                'account_name': 'Example Account',
                'account_type': 'direct_customer',
                'account_status': 'prospect',
                'primary_contact_name': 'Anna Buyer',
                'primary_email': 'anna@example.co',
                'primary_phone': '+840000000',
                'billing_city': 'Ho Chi Minh City',
                'external_customer_ref': 'ACC-001',
                'odoo_partner_ref': 'legacy-partner-42',
                'notes': 'Primary buyer contact',
            },
        )
        account = self.service._store().get_customer_account(company['canonical_key'])
        self.assertIsNotNone(account)

        opportunity_result = self._post_form(
            f'/ui/actions/companies/{company_id}/opportunities',
            {
                'customer_account_id': str(account['id']),
                'title': 'Packaging renewal 2026',
                'status': 'qualified',
                'source_channel': 'manual_intake',
                'estimated_value': '25000000',
                'currency_code': 'VND',
                'target_due_at': '2026-05-01',
                'next_action': 'Prepare RFQ',
                'external_opportunity_ref': 'OPP-001',
                'odoo_lead_ref': 'legacy-lead-77',
                'notes': 'High-priority buyer',
            },
        )
        opportunity = self.service._store().list_commercial_opportunities(company_key=company['canonical_key'])[0]

        quote_result = self._post_form(
            f'/ui/actions/companies/{company_id}/quote-intents',
            {
                'customer_account_id': str(account['id']),
                'opportunity_id': str(opportunity['id']),
                'quote_type': 'rfq_packaging',
                'rfq_reference': 'RFQ-2026-001',
                'quantity_hint': '5000 boxes',
                'target_due_at': '2026-04-25',
                'status': 'requested',
                'notes': 'Urgent carton quote',
            },
        )
        quote = self.service._store().list_quote_intents()[0]

        handoff_result = self._post_form(
            f'/ui/actions/companies/{company_id}/production-handoffs',
            {
                'quote_intent_id': str(quote['id']),
                'handoff_status': 'ready_for_production',
                'production_reference': 'JOB-2026-001',
                'requested_ship_at': '2026-04-30',
                'specification_summary': '5000 corrugated cartons, 4c print',
                'notes': 'Ready for production board review',
            },
        )
        handoff = self.service._store().list_production_handoffs()[0]

        company_page = self._get_text(f'/ui/companies/{company_id}')
        opportunities_page = self._get_text(f'/ui/opportunities?company_id={company_id}')
        opportunity_page = self._get_text(f"/ui/opportunities/{opportunity['id']}")
        quote_page = self._get_text(f"/ui/quote-intents/{quote['id']}")
        handoff_page = self._get_text(f"/ui/production-handoffs/{handoff['id']}")

        self.assertIn('Customer account saved', account_result)
        self.assertIn('Opportunity created', opportunity_result)
        self.assertIn('Quote intent created', quote_result)
        self.assertIn('Production handoff created', handoff_result)
        self.assertIn('Example Account', company_page)
        self.assertIn('Packaging renewal 2026', company_page)
        self.assertIn('RFQ-2026-001', company_page)
        self.assertIn('Commercial audit', company_page)
        self.assertIn('Packaging renewal 2026', opportunities_page)
        self.assertIn('Linked quote intents', opportunity_page)
        self.assertIn('RFQ-2026-001', opportunity_page)
        self.assertIn('Example Account', quote_page)
        self.assertIn('Packaging renewal 2026', quote_page)
        self.assertIn('RFQ-2026-001', quote_page)
        self.assertIn('Packaging renewal 2026', handoff_page)
        self.assertIn('Commercial audit', handoff_page)

    def test_quote_workbench_updates_status_and_pricing(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company_id = self._get_json('/companies')['items'][0]['id']
        self._post_form(
            f'/ui/actions/companies/{company_id}/quote-intents',
            {
                'quote_type': 'rfq_packaging',
                'quantity_hint': '5000 boxes',
                'target_due_at': '2026-04-25',
                'status': 'requested',
                'notes': 'Urgent carton quote',
            },
        )
        quote_intent_id = self.service._store().list_quote_intents()[0]['id']
        result_page = self._post_form(
            f'/ui/actions/quote-intents/{quote_intent_id}',
            {
                'status': 'quoted',
                'quote_reference': 'QT-100',
                'quoted_amount': '12500000',
                'currency_code': 'VND',
                'target_due_at': '2026-04-25',
                'pricing_notes': 'Based on carton board + print',
                'notes': 'Sent to buyer',
            },
        )
        detail_page = self._get_text(f'/ui/quote-intents/{quote_intent_id}')
        quote_page = self._get_text('/ui/quote-intents')

        self.assertIn('Quote workflow saved', result_page)
        self.assertIn('Open quote workbench', result_page)
        self.assertIn('QT-100', detail_page)
        self.assertIn('12 500 000 VND', detail_page)
        self.assertIn('Based on carton board + print', detail_page)
        self.assertIn('Quoted', quote_page)
        self.assertIn('QT-100', quote_page)

    def test_production_handoff_is_editable_in_standalone(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company_id = self._get_json('/companies')['items'][0]['id']
        self._post_form(
            f'/ui/actions/companies/{company_id}/quote-intents',
            {
                'quote_type': 'rfq_packaging',
                'quantity_hint': '5000 boxes',
                'target_due_at': '2026-04-25',
                'status': 'quoted',
                'notes': 'Urgent carton quote',
            },
        )
        quote_intent_id = self.service._store().list_quote_intents()[0]['id']
        result_page = self._post_form(
            f'/ui/actions/companies/{company_id}/production-handoffs',
            {
                'quote_intent_id': str(quote_intent_id),
                'handoff_status': 'ready_for_production',
                'production_reference': 'JOB-2026-001',
                'requested_ship_at': '2026-04-30',
                'specification_summary': '5000 corrugated cartons, 4c print',
                'notes': 'Ready for production board review',
            },
        )
        handoff_id = self.service._store().list_production_handoffs()[0]['id']
        detail_page = self._get_text(f'/ui/production-handoffs/{handoff_id}')
        pipeline_page = self._get_text('/ui/production-handoffs')
        board_page = self._get_text('/ui/production-board')
        update_page = self._post_form(
            f'/ui/actions/production-handoffs/{handoff_id}',
            {
                'handoff_status': 'in_progress',
                'production_reference': 'JOB-2026-001',
                'requested_ship_at': '2026-04-30',
                'specification_summary': '5000 corrugated cartons, 4c print',
                'notes': 'Production started',
            },
        )
        company_page = self._get_text(f'/ui/companies/{company_id}')

        self.assertIn('Production handoff created', result_page)
        self.assertIn('Open production handoff', result_page)
        self.assertIn('Production handoff', detail_page)
        self.assertIn('JOB-2026-001', detail_page)
        self.assertIn('Back to quote workbench', detail_page)
        self.assertIn('Standalone execution handoff', pipeline_page)
        self.assertIn(f'/ui/companies/{company_id}', pipeline_page)
        self.assertIn('Standalone execution board', board_page)
        self.assertIn(f'/ui/production-handoffs/{handoff_id}', board_page)
        self.assertIn('Move to', board_page)
        self.assertIn('Production handoff saved', update_page)
        self.assertIn('Production started', company_page)

    def test_production_board_status_move_does_not_overwrite_existing_handoff_fields(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company_id = self._get_json('/companies')['items'][0]['id']
        self._post_form(
            f'/ui/actions/companies/{company_id}/quote-intents',
            {
                'quote_type': 'rfq_packaging',
                'quantity_hint': '5000 boxes',
                'target_due_at': '2026-04-25',
                'status': 'quoted',
                'notes': 'Urgent carton quote',
            },
        )
        quote_intent_id = self.service._store().list_quote_intents()[0]['id']
        self._post_form(
            f'/ui/actions/companies/{company_id}/production-handoffs',
            {
                'quote_intent_id': str(quote_intent_id),
                'handoff_status': 'ready_for_production',
                'production_reference': 'JOB-2026-001',
                'requested_ship_at': '2026-04-30',
                'specification_summary': 'Old spec',
                'notes': 'Old notes',
            },
        )
        handoff_id = self.service._store().list_production_handoffs()[0]['id']

        self._post_form(
            f'/ui/actions/production-handoffs/{handoff_id}',
            {
                'handoff_status': 'ready_for_production',
                'production_reference': 'JOB-2026-001',
                'requested_ship_at': '2026-05-01',
                'specification_summary': 'New spec',
                'notes': 'New notes',
            },
        )

        update_page = self._post_form(
            f'/ui/actions/production-handoffs/{handoff_id}',
            {
                'handoff_status': 'scheduled',
            },
        )
        detail_page = self._get_text(f'/ui/production-handoffs/{handoff_id}')

        self.assertIn('Production handoff saved', update_page)
        self.assertIn('scheduled', detail_page)
        self.assertIn('2026-05-01', detail_page)
        self.assertIn('New spec', detail_page)
        self.assertIn('New notes', detail_page)

    def test_company_detail_keeps_related_feedback_when_global_event_volume_is_high(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company = self._get_json('/companies')['items'][0]
        company_id = int(company['id'])
        company_key = company['canonical_key']
        store = self.service._store()

        with store._connect() as conn:
            conn.execute(
                """
                INSERT INTO feedback_events (
                    event_id, source_key, source_system, event_type, event_version,
                    occurred_at, payload_hash, reason_code, payload_json, applied_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    'target-feedback-event',
                    company_key,
                    'odoo',
                    'routing_feedback',
                    'v1',
                    '2026-04-16T00:00:00Z',
                    'target-hash',
                    'target_reason',
                    '{}',
                    '2026-04-16T00:00:01Z',
                    '2026-04-16T00:00:01Z',
                ),
            )
            rows = [
                (
                    f'bulk-feedback-{idx}',
                    f'unrelated-{idx}',
                    'odoo',
                    'routing_feedback',
                    'v1',
                    '2026-04-17T00:00:00Z',
                    f'hash-{idx}',
                    'bulk_reason',
                    '{}',
                    '2026-04-17T00:00:01Z',
                    '2026-04-17T00:00:01Z',
                )
                for idx in range(5200)
            ]
            conn.executemany(
                """
                INSERT INTO feedback_events (
                    event_id, source_key, source_system, event_type, event_version,
                    occurred_at, payload_hash, reason_code, payload_json, applied_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

        detail = self.service.operator_company_detail(company_id)
        event_ids = {item['event_id'] for item in detail['feedback_events']}
        self.assertIn('target-feedback-event', event_ids)

    def test_production_handoffs_keep_quote_linkage_when_quote_volume_is_high(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company = self._get_json('/companies')['items'][0]
        company_key = company['canonical_key']
        store = self.service._store()
        quote = store.create_quote_intent(
            company_key=company_key,
            quote_type='rfq_packaging',
            quantity_hint='5000 boxes',
            target_due_at='2026-04-25',
            status='quoted',
            notes='Target quote',
        )
        handoff = store.create_production_handoff(
            company_key=company_key,
            quote_intent_id=quote['id'],
            handoff_status='ready_for_production',
            production_reference='JOB-LINK-1',
            requested_ship_at='2026-04-30',
            specification_summary='Target handoff',
            notes='Target handoff notes',
        )

        with store._connect() as conn:
            rows = [
                (
                    company_key,
                    'rfq_packaging',
                    '',
                    '',
                    'requested',
                    '',
                    None,
                    'VND',
                    '',
                    '2099-01-01T00:00:00Z',
                    '',
                    '2099-01-01T00:00:00Z',
                    '2099-01-01T00:00:00Z',
                )
                for _ in range(5200)
            ]
            conn.executemany(
                """
                INSERT INTO quote_intents (
                    company_key, quote_type, quantity_hint, target_due_at, status,
                    quote_reference, quoted_amount, currency_code, pricing_notes,
                    last_status_at, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

        data = self.service.operator_production_handoffs(limit=100, offset=0)
        row = next(item for item in data['items'] if int(item['id']) == int(handoff['id']))
        self.assertIsNotNone(row['quote_intent'])
        self.assertEqual(int(row['quote_intent']['id']), int(quote['id']))

    def test_commercial_pipeline_keeps_company_linkage_when_company_volume_is_high(self):
        self._post_json('/runs', {'fixture': str(self.fixture_path)})
        company = self._get_json('/companies')['items'][0]
        company_key = company['canonical_key']
        store = self.service._store()
        store.upsert_commercial_record(
            company_key=company_key,
            customer_status='prospect',
            commercial_stage='contacting',
            next_action='Call buyer',
            notes='Target commercial row',
        )

        with store._connect() as conn:
            rows = [
                (
                    f'bulk-company-{idx}',
                    f'Bulk Company {idx}',
                    'new',
                    'bulk-fp',
                    f'bulk-df-{idx}',
                    '2099-01-01T00:00:00Z',
                )
                for idx in range(5200)
            ]
            conn.executemany(
                """
                INSERT INTO canonical_companies (
                    canonical_key, canonical_name, review_status, source_fingerprint, dedup_fingerprint, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

        data = self.service.operator_commercial_pipeline(limit=100, offset=0)
        row = next(item for item in data['items'] if item.get('company_key') == company_key)
        self.assertIsNotNone(row['company'])
        self.assertEqual(row['company']['canonical_key'], company_key)

    def test_missing_and_method_errors(self):
        with self.assertRaises(HTTPError) as not_found:
            self._get('/missing')
        self.assertEqual(not_found.exception.code, 404)

        with self.assertRaises(HTTPError) as bad_method:
            self._get('/runs')
        self.assertEqual(bad_method.exception.code, 405)

    def _get(self, path: str, headers: dict[str, str] | None = None):
        request_headers = {'Cookie': 'magonos-locale=en'}
        if headers:
            request_headers.update(headers)
        request = Request(f'{self.server.base_url}{path}', headers=request_headers)
        return urlopen(request, timeout=5)

    def _get_json(self, path: str) -> dict:
        with self._get(path) as response:
            return json.loads(response.read().decode('utf-8'))

    def _get_text(self, path: str, headers: dict[str, str] | None = None) -> str:
        with self._get(path, headers=headers) as response:
            return response.read().decode('utf-8')

    def _post_json(self, path: str, payload: dict) -> dict:
        request = Request(
            f'{self.server.base_url}{path}',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Cookie': 'magonos-locale=en'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))

    def _post_form(self, path: str, payload: dict[str, str]) -> str:
        body = urlencode(payload).encode('utf-8')
        request = Request(
            f'{self.server.base_url}{path}',
            data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded', 'Cookie': 'magonos-locale=en'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            return response.read().decode('utf-8')


if __name__ == '__main__':
    unittest.main()
