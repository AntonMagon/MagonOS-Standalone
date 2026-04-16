import tempfile
import unittest
from pathlib import Path

from magon_standalone.supplier_intelligence.fixture_discovery import FixtureDiscoveryService
from magon_standalone.supplier_intelligence.normalization_service import BasicEnrichmentService, BasicNormalizationService
from magon_standalone.supplier_intelligence.operations_service import SupplierOperationsService
from magon_standalone.supplier_intelligence.pipeline import SupplierIntelligencePipeline
from magon_standalone.supplier_intelligence.routing_service import ReviewQueueRoutingService
from magon_standalone.supplier_intelligence.scoring_service import ConfigurableScoringService
from magon_standalone.supplier_intelligence.deduplication_service import HybridDeduplicationService
from magon_standalone.supplier_intelligence.sqlite_persistence import SqliteSupplierIntelligenceStore


class TestStandaloneOperations(unittest.TestCase):
    def setUp(self):
        self.fixture_path = Path(__file__).resolve().parent / "fixtures" / "vn_suppliers_raw.json"

    def test_decision_and_queue_transition_live_in_standalone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "ops.sqlite3"
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
            pipeline.run(query="printing packaging vietnam", country_code="VN")
            service = SupplierOperationsService(store)
            company = store.list_companies(limit=1)[0]

            result = service.decide(
                company_key=company["canonical_key"],
                reason_code="manual_operator_decision",
                notes="Approved in standalone",
                manual_override=True,
                forced_outcome="approved_supplier",
            )

            profile = store.get_vendor_profile(company["canonical_key"])
            decisions = store.list_qualification_decisions(company["canonical_key"])
            audit_rows = store.list_routing_audit(company["canonical_key"])
            queue_item = next(item for item in store.list_review_queue() if item["company_key"] == company["canonical_key"] and item["queue_name"] == "qualification_review")

            self.assertEqual(result.outcome, "approved_supplier")
            self.assertEqual(profile["qualification_status"], "qualified")
            self.assertEqual(profile["routing_state"], "approved_supplier")
            self.assertGreaterEqual(len(decisions), 1)
            self.assertGreaterEqual(len(audit_rows), 1)
            self.assertEqual(queue_item["status"], "done")

            store.transition_review_queue(queue_item["id"], "pending", "manual_reopen", "Reopen for follow-up", allow_reprocess=True)
            reopened = next(item for item in store.list_review_queue() if item["id"] == queue_item["id"])
            self.assertEqual(reopened["status"], "pending")
            self.assertEqual(reopened["reprocess_count"], 1)

    def test_pipeline_rerun_does_not_clobber_operator_owned_queue_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "ops.sqlite3"
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
            pipeline.run(query="printing packaging vietnam", country_code="VN")
            queue_item = store.list_review_queue()[0]
            store.transition_review_queue(queue_item["id"], "in_progress", "manual_pickup", "Picked up by operator")

            pipeline.run(query="printing packaging vietnam", country_code="VN")
            current = next(item for item in store.list_review_queue() if item["id"] == queue_item["id"])

            self.assertEqual(current["status"], "in_progress")
            self.assertEqual(current["reason_code"], "manual_pickup")
            self.assertEqual(current["reason"], "Picked up by operator")


if __name__ == "__main__":
    unittest.main()
