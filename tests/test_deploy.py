import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from magon_standalone.supplier_intelligence.api import SupplierIntelligenceApiServer


class TestDeployEntrypoint(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'deploy.sqlite3'
        os.environ['MAGON_STANDALONE_DB_PATH'] = str(self.db_path)
        os.environ['MAGON_STANDALONE_DEFAULT_QUERY'] = 'deploy smoke'
        os.environ['MAGON_STANDALONE_DEFAULT_COUNTRY'] = 'VN'
        sys.modules.pop('magon_standalone.wsgi', None)
        module = importlib.import_module('magon_standalone.wsgi')
        self.app = module.app
        self.service = module.service
        self.server = SupplierIntelligenceApiServer(self.service, host='127.0.0.1', port=0)
        self.thread = self.server.start_in_thread()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        for key in ['MAGON_STANDALONE_DB_PATH', 'MAGON_STANDALONE_DEFAULT_QUERY', 'MAGON_STANDALONE_DEFAULT_COUNTRY']:
            os.environ.pop(key, None)
        self.tmpdir.cleanup()

    def test_wsgi_service_uses_env_config(self):
        self.assertEqual(self.service.default_query, 'deploy smoke')
        self.assertEqual(self.service.default_country, 'VN')
        self.assertEqual(Path(self.service.db_path), self.db_path)

    def test_wsgi_app_serves_health(self):
        with urlopen(f'{self.server.base_url}/health', timeout=5) as response:
            body = response.read().decode('utf-8')
        self.assertIn('magon-standalone', body)
        self.assertIn(str(self.db_path), body)


if __name__ == '__main__':
    unittest.main()
