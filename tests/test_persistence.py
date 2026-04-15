import tempfile
import unittest
from pathlib import Path

from magon_standalone.supplier_intelligence.sqlite_persistence import SqliteSupplierIntelligenceStore


class TestSqlitePersistence(unittest.TestCase):
    def test_store_initializes_schema_and_lists_empty_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            counts = store.snapshot_counts()

            self.assertEqual(counts['raw_records'], 0)
            self.assertEqual(counts['canonical_companies'], 0)
            self.assertEqual(store.list_raw_records(), [])
            self.assertEqual(store.list_companies(), [])
            self.assertEqual(store.list_scores(), [])
            self.assertEqual(store.list_review_queue(), [])
            self.assertEqual(store.list_feedback_events(), [])
            self.assertEqual(store.list_feedback_status(), [])


if __name__ == '__main__':
    unittest.main()
