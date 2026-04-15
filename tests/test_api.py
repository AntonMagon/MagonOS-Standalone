import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiServer, SupplierIntelligenceApiService


class TestStandaloneApi(unittest.TestCase):
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

    def test_health_status_and_html_pages(self):
        health = self._get_json('/health')
        status = self._get_json('/status')
        home = self._get_text('/')

        self.assertEqual(health['status'], 'ok')
        self.assertEqual(status['storage_counts']['raw_records'], 0)
        self.assertIn('MagonOS Standalone', home)
        self.assertIn('/ui/companies', home)

    def test_run_pipeline_and_read_results(self):
        run_result = self._post_json('/runs', {'fixture': str(self.fixture_path)})
        companies = self._get_json('/companies')
        scores = self._get_json('/scores')
        queue = self._get_json('/review-queue')
        companies_page = self._get_text('/ui/companies')

        self.assertEqual(run_result['pipeline_report']['raw_count'], 3)
        self.assertEqual(companies['count'], 2)
        self.assertEqual(scores['count'], 2)
        self.assertEqual(queue['count'], 2)
        self.assertIn('Canonical companies', companies_page)

    def test_missing_and_method_errors(self):
        with self.assertRaises(HTTPError) as not_found:
            self._get('/missing')
        self.assertEqual(not_found.exception.code, 404)

        with self.assertRaises(HTTPError) as bad_method:
            self._get('/runs')
        self.assertEqual(bad_method.exception.code, 405)

    def _get(self, path: str):
        return urlopen(f'{self.server.base_url}{path}', timeout=5)

    def _get_json(self, path: str) -> dict:
        with self._get(path) as response:
            return json.loads(response.read().decode('utf-8'))

    def _get_text(self, path: str) -> str:
        with self._get(path) as response:
            return response.read().decode('utf-8')

    def _post_json(self, path: str, payload: dict) -> dict:
        request = Request(
            f'{self.server.base_url}{path}',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
