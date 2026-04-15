import json
import tempfile
import unittest
from pathlib import Path

from magon_standalone.supplier_intelligence.deduplication_service import HybridDeduplicationService
from magon_standalone.supplier_intelligence.fixture_discovery import FixtureDiscoveryService
from magon_standalone.supplier_intelligence.normalization_service import BasicEnrichmentService, BasicNormalizationService
from magon_standalone.supplier_intelligence.pipeline import SupplierIntelligencePipeline
from magon_standalone.supplier_intelligence.routing_service import ReviewQueueRoutingService
from magon_standalone.supplier_intelligence.scoring_service import ConfigurableScoringService
from magon_standalone.supplier_intelligence.sqlite_persistence import SqliteSupplierIntelligenceStore


class TestStandalonePipeline(unittest.TestCase):
    def setUp(self):
        self.fixture_path = Path(__file__).resolve().parent / 'fixtures' / 'vn_suppliers_raw.json'

    def test_compute_services_work_without_odoo(self):
        rows = json.loads(self.fixture_path.read_text())
        normalized = BasicNormalizationService().normalize(rows)
        enriched = BasicEnrichmentService().enrich(normalized)
        deduped, decisions = HybridDeduplicationService().deduplicate(enriched)
        scores = ConfigurableScoringService().score(deduped)

        self.assertEqual(len(rows), 3)
        self.assertEqual(len(normalized), 3)
        self.assertEqual(len(deduped), 2)
        self.assertGreaterEqual(len(decisions), 1)
        self.assertEqual(len(scores), 2)

    def test_pipeline_persists_results_to_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            pipeline = SupplierIntelligencePipeline(
                discovery=FixtureDiscoveryService(self.fixture_path),
                normalization=BasicNormalizationService(),
                enrichment=BasicEnrichmentService(),
                deduplication=HybridDeduplicationService(),
                scoring=ConfigurableScoringService(),
                routing=ReviewQueueRoutingService(),
                repository=store,
            )

            report = pipeline.run(query='printing packaging vietnam', country_code='VN')
            counts = store.snapshot_counts()

            self.assertEqual(report.raw_count, 3)
            self.assertEqual(counts['raw_records'], 3)
            self.assertEqual(counts['canonical_companies'], 2)
            self.assertEqual(counts['vendor_scores'], 2)
            self.assertEqual(counts['review_queue'], 2)


if __name__ == '__main__':
    unittest.main()
