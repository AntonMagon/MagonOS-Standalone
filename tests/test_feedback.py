import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiServer, SupplierIntelligenceApiService
from magon_standalone.supplier_intelligence.sqlite_persistence import SqliteSupplierIntelligenceStore


class TestFeedbackIngestion(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'supplier_intelligence.sqlite3'
        self.service = SupplierIntelligenceApiService(db_path=self.db_path, integration_token='secret-token')
        self.server = SupplierIntelligenceApiServer(self.service, host='127.0.0.1', port=0)
        self.thread = self.server.start_in_thread()
        self.routing_event = {
            'event_id': 'evt-routing-1',
            'source_key': 'cmp-1',
            'source_system': 'odoo',
            'event_type': 'routing_feedback',
            'event_version': 'routing:v1',
            'occurred_at': '2026-04-16T01:00:00Z',
            'payload_hash': 'hash-routing-1',
            'company_id': 1,
            'vendor_profile_id': 11,
            'routing_outcome': 'potential_supplier',
            'manual_review_status': 'in_review',
            'reason_code': 'manual_review',
            'notes': 'Operator marked for follow-up',
            'is_manual_override': True,
            'payload': {
                'routing_outcome': 'potential_supplier',
                'manual_review_status': 'in_review',
                'reason_code': 'manual_review',
                'notes': 'Operator marked for follow-up',
                'is_manual_override': True,
            },
        }
        self.commercial_alias_event = {
            'event_id': 'evt-commercial-1',
            'source_key': 'cmp-1',
            'source_system': 'odoo',
            'event_type': 'crm_lead_feedback',
            'event_version': 'commercial:v1',
            'occurred_at': '2026-04-16T01:05:00Z',
            'payload_hash': 'hash-commercial-1',
            'company_id': 1,
            'vendor_profile_id': 11,
            'crm_lead_id': 41,
            'lead_mapping_id': 51,
            'lead_status': 'qualified',
            'crm_linked': True,
            'reason_code': 'lead_reused',
            'notes': 'Existing qualified lead reused',
            'payload': {
                'crm_lead_id': 41,
                'lead_mapping_id': 51,
                'lead_status': 'qualified',
                'crm_linked': True,
                'reason_code': 'lead_reused',
                'notes': 'Existing qualified lead reused',
            },
        }

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.tmpdir.cleanup()

    def test_feedback_ingestion_is_token_protected_and_idempotent(self):
        with self.assertRaises(HTTPError) as forbidden:
            self._post_json('/feedback-events', {'events': [self.routing_event]})
        self.assertEqual(forbidden.exception.code, 403)

        first = self._post_json('/feedback-events', {'events': [self.routing_event]}, token='secret-token')
        second = self._post_json('/feedback-events', {'events': [self.routing_event]}, token='secret-token')
        events = self._get_json('/feedback-events')
        projection = self._get_json('/feedback-status/cmp-1')

        self.assertEqual(first['accepted'], 1)
        self.assertEqual(second['accepted'], 0)
        self.assertEqual(events['count'], 1)
        self.assertEqual(projection['item']['routing_outcome'], 'potential_supplier')

    def test_projection_stays_separate_from_canonical_company_data(self):
        store = SqliteSupplierIntelligenceStore(self.db_path)
        store.upsert_companies([
            {
                'canonical_key': 'cmp-1',
                'canonical_name': 'Standalone Canonical',
                'website': 'https://standalone.example',
                'confidence': 0.8,
                'review_status': 'new',
                'source_fingerprint': 'fp-1',
                'dedup_fingerprint': 'df-1',
            }
        ])

        self._post_json('/feedback-events', {'events': [self.routing_event, self.commercial_alias_event]}, token='secret-token')
        companies = self._get_json('/companies')
        projection = self._get_json('/feedback-status/cmp-1')

        self.assertEqual(companies['items'][0]['canonical_name'], 'Standalone Canonical')
        self.assertEqual(projection['item']['lead_status'], 'qualified')
        self.assertEqual(projection['item']['last_event_type'], 'commercial_disposition_feedback')

    def _get_json(self, path: str) -> dict:
        with urlopen(f'{self.server.base_url}{path}', timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))

    def _post_json(self, path: str, payload: dict, token: str | None = None) -> dict:
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Integration-Token'] = token
        request = Request(
            f'{self.server.base_url}{path}',
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST',
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
