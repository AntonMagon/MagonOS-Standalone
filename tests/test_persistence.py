import tempfile
import unittest
from pathlib import Path

from magon_standalone.supplier_intelligence.sqlite_persistence import SqliteSupplierIntelligenceStore


class TestSqlitePersistence(unittest.TestCase):
    # RU: SQLite store остаётся источником истины для standalone intelligence, поэтому сериализация/декодирование тестируются жёстко.
    def test_store_initializes_schema_and_lists_empty_tables(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            counts = store.snapshot_counts()

            self.assertEqual(counts['raw_records'], 0)
            self.assertEqual(counts['canonical_companies'], 0)
            self.assertEqual(counts['vendor_profiles'], 0)
            self.assertEqual(counts['qualification_decisions'], 0)
            self.assertEqual(counts['routing_audit'], 0)
            self.assertEqual(counts['commercial_records'], 0)
            self.assertEqual(counts['customer_accounts'], 0)
            self.assertEqual(counts['request_drafts'], 0)
            self.assertEqual(counts['request_intakes'], 0)
            self.assertEqual(counts['commercial_opportunities'], 0)
            self.assertEqual(counts['quote_intents'], 0)
            self.assertEqual(counts['production_handoffs'], 0)
            self.assertEqual(counts['commercial_audit_log'], 0)
            self.assertEqual(store.list_raw_records(), [])
            self.assertEqual(store.list_companies(), [])
            self.assertEqual(store.list_scores(), [])
            self.assertEqual(store.list_vendor_profiles(), [])
            self.assertEqual(store.list_commercial_records(), [])
            self.assertEqual(store.list_request_drafts(), [])
            self.assertEqual(store.list_request_intakes(), [])
            self.assertEqual(store.list_commercial_opportunities(), [])
            self.assertEqual(store.list_commercial_audit(), [])
            self.assertEqual(store.list_quote_intents(), [])
            self.assertEqual(store.list_production_handoffs(), [])
            self.assertEqual(store.list_review_queue(), [])
            self.assertEqual(store.list_feedback_events(), [])
            self.assertEqual(store.list_feedback_status(), [])

    def test_decoded_rows_do_not_leak_internal_json_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            conn = store._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO canonical_companies (
                        canonical_key, canonical_name, capabilities_json, provenance_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    ("company-1", "Example Co", '["PRINTING"]', '["fixture"]', "2026-04-16T00:00:00Z"),
                )
                conn.execute(
                    """
                    INSERT INTO raw_records (
                        source_fingerprint, company_name, raw_payload_json, phones_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    ("raw-1", "Example Co", '{"sample": true}', '["+8401"]', "2026-04-16T00:00:00Z"),
                )
                conn.execute(
                    """
                    INSERT INTO review_queue (
                        company_key, queue_name, priority, reason, reason_code, evidence_refs_json, score, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("company-1", "supplier_review", 10, "Needs review", "seed", '["e1"]', 0.5, "pending", "2026-04-16T00:00:00Z"),
                )
                conn.execute(
                    """
                    INSERT INTO feedback_events (
                        event_id, source_key, source_system, event_type, event_version, occurred_at, payload_hash, payload_json, applied_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("evt-1", "company-1", "odoo", "routing_feedback", "v1", "2026-04-16T00:00:00Z", "hash-1", '{"routing_outcome":"approved_supplier"}', "2026-04-16T00:00:01Z", "2026-04-16T00:00:01Z"),
                )
                conn.commit()
            finally:
                conn.close()

            company = store.list_companies()[0]
            raw_record = store.list_raw_records()[0]
            queue_item = store.list_review_queue()[0]
            event = store.list_feedback_events()[0]

            self.assertNotIn("capabilities_json", company)
            self.assertNotIn("provenance_json", company)
            self.assertEqual(company["capabilities"], ["PRINTING"])
            self.assertNotIn("raw_payload_json", raw_record)
            self.assertNotIn("phones_json", raw_record)
            self.assertEqual(raw_record["raw_payload"], {"sample": True})
            self.assertEqual(raw_record["phones"], ["+8401"])
            self.assertNotIn("evidence_refs_json", queue_item)
            self.assertEqual(queue_item["evidence_refs"], ["e1"])
            self.assertNotIn("payload_json", event)
            self.assertEqual(event["payload"], {"routing_outcome": "approved_supplier"})

    def test_commercial_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            record = store.upsert_commercial_record(
                company_key='cmp-1',
                customer_status='prospect',
                commercial_stage='contacting',
                customer_reference='CUST-1',
                opportunity_reference='OPP-7',
                next_action='Call buyer',
                next_action_due_at='2026-04-20',
                notes='Manual-first follow-up',
            )

            self.assertEqual(record['commercial_stage'], 'contacting')
            self.assertEqual(store.get_commercial_record('cmp-1')['next_action'], 'Call buyer')
            self.assertEqual(store.list_commercial_records()[0]['customer_reference'], 'CUST-1')

    def test_quote_intent_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            record = store.create_quote_intent(
                company_key='cmp-1',
                quote_type='rfq_packaging',
                quantity_hint='5000 boxes',
                target_due_at='2026-04-25',
                status='requested',
                notes='Urgent carton quote',
            )

            self.assertEqual(record['quote_type'], 'rfq_packaging')
            self.assertEqual(store.list_quote_intents()[0]['quantity_hint'], '5000 boxes')
            updated = store.update_quote_intent(
                quote_intent_id=record['id'],
                status='quoted',
                quote_reference='QT-100',
                quoted_amount=12500000,
                currency_code='VND',
                target_due_at='2026-04-25',
                pricing_notes='Based on carton board + print',
                notes='Sent to buyer',
            )
            self.assertEqual(updated['status'], 'quoted')
            self.assertEqual(updated['quote_reference'], 'QT-100')
            self.assertEqual(updated['quoted_amount'], 12500000)
            self.assertEqual(store.get_quote_intent(record['id'])['pricing_notes'], 'Based on carton board + print')

    def test_customer_account_and_opportunity_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            account = store.upsert_customer_account(
                company_key='cmp-1',
                account_name='Example Account',
                account_type='direct_customer',
                account_status='prospect',
                primary_contact_name='Anna Buyer',
                primary_email='anna@example.co',
                primary_phone='+840000000',
                billing_city='Ho Chi Minh City',
                notes='Primary buyer contact',
            )
            opportunity = store.create_commercial_opportunity(
                company_key='cmp-1',
                customer_account_id=account['id'],
                title='Packaging renewal 2026',
                status='qualified',
                source_channel='manual_intake',
                estimated_value=25000000,
                currency_code='VND',
                target_due_at='2026-05-01',
                next_action='Prepare RFQ',
                notes='High-priority buyer',
            )
            updated = store.update_commercial_opportunity(
                opportunity_id=opportunity['id'],
                customer_account_id=account['id'],
                title='Packaging renewal 2026',
                status='rfq_requested',
                source_channel='manual_intake',
                estimated_value=26000000,
                currency_code='VND',
                target_due_at='2026-05-02',
                next_action='Prepare quote',
                notes='RFQ requested',
            )

            self.assertEqual(store.get_customer_account('cmp-1')['account_name'], 'Example Account')
            self.assertEqual(store.get_customer_account_by_id(account['id'])['primary_email'], 'anna@example.co')
            self.assertEqual(store.get_commercial_opportunity(opportunity['id'])['title'], 'Packaging renewal 2026')
            self.assertEqual(updated['status'], 'rfq_requested')
            self.assertEqual(store.count_commercial_opportunities(company_key='cmp-1'), 1)
            audit = store.list_commercial_audit(company_key='cmp-1')
            self.assertGreaterEqual(len(audit), 3)
            self.assertIn('customer_account', {item['entity_type'] for item in audit})
            self.assertIn('commercial_opportunity', {item['entity_type'] for item in audit})

    def test_request_draft_submit_creates_request_and_updates_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            draft = store.create_request_draft(
                company_key='cmp-1',
                draft_type='rfq_packaging',
                customer_name='Anna Buyer',
                customer_email='anna@example.co',
                item_summary='5000 corrugated cartons',
                quantity_hint='5000 boxes',
                city='Ho Chi Minh City',
                requested_deadline='2026-04-25',
                file_required=True,
                file_links=['https://files.example/spec.pdf'],
                notes='Initial intake',
            )

            self.assertEqual(draft['required_fields_state'], 'ready_to_submit')
            request = store.submit_request_draft(
                draft_id=draft['id'],
                source_channel='web_form',
                customer_reference='CUST-REQ-1',
                request_status='needs_review',
                notes='Escalate for review',
            )

            updated_draft = store.get_request_draft(draft['id'])
            self.assertEqual(updated_draft['draft_status'], 'submitted')
            self.assertEqual(request['draft_id'], draft['id'])
            self.assertEqual(request['request_status'], 'needs_review')
            self.assertTrue(request['request_code'].startswith('REQ-'))
            self.assertEqual(store.count_request_drafts(company_key='cmp-1'), 1)
            self.assertEqual(store.count_request_intakes(company_key='cmp-1'), 1)
            audit = store.list_commercial_audit(company_key='cmp-1')
            self.assertIn('request_draft', {item['entity_type'] for item in audit})
            self.assertIn('request_intake', {item['entity_type'] for item in audit})

    def test_quote_intent_enforces_commercial_linkage_integrity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                },
                {
                    'canonical_key': 'cmp-2',
                    'canonical_name': 'Other Co',
                    'website': 'https://other.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-2',
                    'dedup_fingerprint': 'df-2',
                },
            ])
            account_1 = store.upsert_customer_account(company_key='cmp-1', account_name='Account 1')
            account_2 = store.upsert_customer_account(company_key='cmp-2', account_name='Account 2')
            opportunity_1 = store.create_commercial_opportunity(
                company_key='cmp-1',
                customer_account_id=account_1['id'],
                title='Company 1 opportunity',
                status='qualified',
            )
            opportunity_2 = store.create_commercial_opportunity(
                company_key='cmp-2',
                customer_account_id=account_2['id'],
                title='Company 2 opportunity',
                status='qualified',
            )

            with self.assertRaisesRegex(ValueError, 'customer_account_company_mismatch'):
                store.create_quote_intent(
                    company_key='cmp-1',
                    customer_account_id=account_2['id'],
                    quote_type='rfq_packaging',
                    status='requested',
                )
            with self.assertRaisesRegex(ValueError, 'opportunity_company_mismatch'):
                store.create_quote_intent(
                    company_key='cmp-1',
                    customer_account_id=account_1['id'],
                    opportunity_id=opportunity_2['id'],
                    quote_type='rfq_packaging',
                    status='requested',
                )

    def test_quote_intent_roundtrip_with_standalone_commercial_links(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            account = store.upsert_customer_account(company_key='cmp-1', account_name='Example Account')
            opportunity = store.create_commercial_opportunity(
                company_key='cmp-1',
                customer_account_id=account['id'],
                title='Packaging renewal 2026',
                status='rfq_requested',
            )
            quote = store.create_quote_intent(
                company_key='cmp-1',
                customer_account_id=account['id'],
                opportunity_id=opportunity['id'],
                quote_type='rfq_packaging',
                rfq_reference='RFQ-2026-001',
                quantity_hint='5000 boxes',
                target_due_at='2026-04-25',
                status='requested',
                notes='Urgent carton quote',
            )
            updated = store.update_quote_intent(
                quote_intent_id=quote['id'],
                customer_account_id=account['id'],
                opportunity_id=opportunity['id'],
                status='quoted',
                rfq_reference='RFQ-2026-001',
                quote_reference='QT-100',
                quoted_amount=12500000,
                currency_code='VND',
                target_due_at='2026-04-25',
                pricing_notes='Based on carton board + print',
                notes='Sent to buyer',
            )

            self.assertEqual(updated['customer_account_id'], account['id'])
            self.assertEqual(updated['opportunity_id'], opportunity['id'])
            self.assertEqual(updated['rfq_reference'], 'RFQ-2026-001')
            audit = store.list_commercial_audit(entity_type='quote_intent', entity_id=quote['id'])
            self.assertEqual(audit[0]['entity_type'], 'quote_intent')

    def test_production_handoff_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            quote = store.create_quote_intent(
                company_key='cmp-1',
                quote_type='rfq_packaging',
                quantity_hint='5000 boxes',
                target_due_at='2026-04-25',
                status='quoted',
                notes='Urgent carton quote',
            )
            record = store.create_production_handoff(
                company_key='cmp-1',
                quote_intent_id=quote['id'],
                handoff_status='ready_for_production',
                production_reference='JOB-2026-001',
                requested_ship_at='2026-04-30',
                specification_summary='5000 corrugated cartons, 4c print',
                notes='Ready for production board review',
            )
            self.assertEqual(record['production_reference'], 'JOB-2026-001')
            updated = store.update_production_handoff(
                handoff_id=record['id'],
                handoff_status='in_progress',
                production_reference='JOB-2026-001',
                requested_ship_at='2026-04-30',
                specification_summary='5000 corrugated cartons, 4c print',
                notes='Production started',
            )
            self.assertEqual(updated['handoff_status'], 'in_progress')
            self.assertEqual(store.get_production_handoff(record['id'])['notes'], 'Production started')

    def test_production_handoff_rejects_quote_from_another_company(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                },
                {
                    'canonical_key': 'cmp-2',
                    'canonical_name': 'Other Co',
                    'website': 'https://other.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-2',
                    'dedup_fingerprint': 'df-2',
                },
            ])
            quote = store.create_quote_intent(
                company_key='cmp-1',
                quote_type='rfq_packaging',
                quantity_hint='5000 boxes',
                target_due_at='2026-04-25',
                status='quoted',
                notes='Quote for company 1',
            )

            with self.assertRaisesRegex(ValueError, 'quote_intent_company_mismatch'):
                store.create_production_handoff(
                    company_key='cmp-2',
                    quote_intent_id=quote['id'],
                    handoff_status='ready_for_production',
                )

    def test_production_handoff_status_update_preserves_existing_fields_when_not_supplied(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / 'supplier_intelligence.sqlite3'
            store = SqliteSupplierIntelligenceStore(db_path)
            store.upsert_companies([
                {
                    'canonical_key': 'cmp-1',
                    'canonical_name': 'Example Co',
                    'website': 'https://example.co',
                    'confidence': 0.8,
                    'review_status': 'new',
                    'source_fingerprint': 'fp-1',
                    'dedup_fingerprint': 'df-1',
                }
            ])
            handoff = store.create_production_handoff(
                company_key='cmp-1',
                handoff_status='ready_for_production',
                production_reference='JOB-1',
                requested_ship_at='2026-04-30',
                specification_summary='old spec',
                notes='old notes',
            )
            store.update_production_handoff(
                handoff_id=handoff['id'],
                handoff_status='in_progress',
                production_reference='JOB-1',
                requested_ship_at='2026-05-01',
                specification_summary='new spec',
                notes='new notes',
            )

            updated = store.update_production_handoff(
                handoff_id=handoff['id'],
                handoff_status='scheduled',
            )

            self.assertEqual(updated['handoff_status'], 'scheduled')
            self.assertEqual(updated['requested_ship_at'], '2026-05-01')
            self.assertEqual(updated['specification_summary'], 'new spec')
            self.assertEqual(updated['notes'], 'new notes')


if __name__ == '__main__':
    unittest.main()
