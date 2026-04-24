from __future__ import annotations

import importlib
import unittest

from magon_standalone.supplier_intelligence.evaluation import SupplierParsingEvaluator
from magon_standalone.supplier_intelligence.scenario_config import ScenarioConfig


class TestSupplierParsingEvaluation(unittest.TestCase):
    # RU: Eval-контур обязан предпочитать реально совпавшую supplier row, а не первый попавшийся record из страницы directory.
    def test_best_record_match_prefers_matching_identity(self) -> None:
        evaluator = SupplierParsingEvaluator(ScenarioConfig(defaults={}, domain_overrides={}))
        expected = {
            "supplier_name": "Minh Phat Packaging",
            "website": "https://minhphatpack.vn",
            "phone": "+84 28 1111 0001",
            "email": "sales@minhphatpack.vn",
            "address": "Thu Duc, Ho Chi Minh City",
        }
        records = [
            {
                "company_name": "Wrong Supplier",
                "website": "https://wrong.example.com",
                "phones": ["+84123456789"],
                "emails": ["hello@wrong.example.com"],
                "address_text": "Ha Noi",
                "source_url": "https://directory.example.com/wrong",
            },
            {
                "company_name": "Minh Phat Packaging Co., Ltd.",
                "website": "https://minhphatpack.vn",
                "phones": ["+84 28 1111 0001"],
                "emails": ["sales@minhphatpack.vn"],
                "address_text": "Thu Duc, Ho Chi Minh City",
                "source_url": "https://directory.example.com/minh-phat",
            },
        ]

        best = evaluator._best_record_match(records, expected)

        self.assertIsNotNone(best)
        self.assertEqual(best["website"], "https://minhphatpack.vn")

    def test_field_scores_report_exact_and_partial_matches(self) -> None:
        evaluator = SupplierParsingEvaluator(ScenarioConfig(defaults={}, domain_overrides={}))
        record = {
            "company_name": "Saigon Label Print Joint Stock Company",
            "website": "https://saigonlabel.vn",
            "phones": ["+84 28 3777 0001"],
            "emails": ["hello@saigonlabel.vn"],
            "address_text": "District 7, Ho Chi Minh City",
            "city": "Ho Chi Minh City",
            "categories": ["label"],
            "labels": ["self adhesive label"],
            "services": ["offset"],
            "products": [],
            "capabilities_text": "label; offset",
        }
        expected = {
            "supplier_name": "Saigon Label Print",
            "website": "saigonlabel.vn",
            "phone": "028 3777 0001",
            "email": "sales@saigonlabel.vn",
            "address": "District 7, Ho Chi Minh City",
            "city_region": "Ho Chi Minh City",
            "category": "LABEL_SELF_ADHESIVE",
            "capabilities": ["LABEL_SELF_ADHESIVE", "PRINT_OFFSET"],
        }

        scores = evaluator._field_scores(record, expected)

        self.assertTrue(scores["supplier_name"].partial_match)
        self.assertTrue(scores["website"].exact_match)
        self.assertTrue(scores["phone"].partial_match)
        self.assertTrue(scores["email"].partial_match)
        self.assertTrue(scores["address"].exact_match)
        self.assertTrue(scores["city_region"].exact_match)
        self.assertTrue(scores["category"].partial_match)
        self.assertTrue(scores["capabilities"].exact_match)

    # RU: Address exact-match в acceptance gate не должен ломаться на безопасных сокращениях P./Q./TP. и каноническом порядке служебных токенов.
    def test_address_score_normalizes_admin_abbreviations(self) -> None:
        evaluator = SupplierParsingEvaluator(ScenarioConfig(defaults={}, domain_overrides={}))
        record = {
            "company_name": "AP Labels",
            "address_text": "Số 211 Đường số 9, P. Phước Bình, Q.9, TP.HCM",
            "city": "Ho Chi Minh City",
        }
        expected = {
            "supplier_name": "AP Labels",
            "address": "Số 211, Đường Số 9, Phường Phước Bình, Quận 9, TP. Hồ Chí Minh (TPHCM)",
            "city_region": "Ho Chi Minh City",
        }

        scores = evaluator._field_scores(record, expected)

        self.assertTrue(scores["address"].exact_match)
        self.assertTrue(scores["city_region"].exact_match)

    # RU: Eval summary обязан явно перечислять проваленные samples по class/scenario, иначе quality gate нельзя использовать как жёсткий acceptance-контур.
    def test_summary_includes_failed_samples_and_company_site_breakdown(self) -> None:
        evaluator = SupplierParsingEvaluator(ScenarioConfig(defaults={}, domain_overrides={}))
        results = [
            {
                "sample_id": "site-a",
                "source_class": "simple_supplier_site",
                "scenario_key": "COMPANY_SITE",
                "browser_used": False,
                "extraction_success": False,
                "failed_fields": ["address", "supplier_name"],
                "field_scores": {
                    "supplier_name": {"expected": "A", "coverage": True, "exact_match": False, "partial_match": False},
                    "website": {"expected": "a.example.com", "coverage": True, "exact_match": True, "partial_match": True},
                    "phone": {"expected": "", "coverage": False, "exact_match": False, "partial_match": False},
                    "email": {"expected": "", "coverage": False, "exact_match": False, "partial_match": False},
                    "address": {"expected": "Addr A", "coverage": True, "exact_match": False, "partial_match": True},
                    "city_region": {"expected": "Ho Chi Minh City", "coverage": True, "exact_match": True, "partial_match": True},
                    "category": {"expected": "", "coverage": False, "exact_match": False, "partial_match": False},
                    "capabilities": {"expected": [], "coverage": False, "exact_match": False, "partial_match": False},
                },
                "evidence_path": "/tmp/site-a.json",
            },
            {
                "sample_id": "dir-a",
                "source_class": "directory_listing",
                "scenario_key": "SIMPLE_DIRECTORY",
                "browser_used": False,
                "extraction_success": True,
                "failed_fields": [],
                "field_scores": {
                    "supplier_name": {"expected": "Dir A", "coverage": True, "exact_match": True, "partial_match": True},
                    "website": {"expected": "dir.example.com", "coverage": True, "exact_match": True, "partial_match": True},
                    "phone": {"expected": "", "coverage": False, "exact_match": False, "partial_match": False},
                    "email": {"expected": "", "coverage": False, "exact_match": False, "partial_match": False},
                    "address": {"expected": "Addr Dir", "coverage": True, "exact_match": True, "partial_match": True},
                    "city_region": {"expected": "Ho Chi Minh City", "coverage": True, "exact_match": True, "partial_match": True},
                    "category": {"expected": "", "coverage": False, "exact_match": False, "partial_match": False},
                    "capabilities": {"expected": [], "coverage": False, "exact_match": False, "partial_match": False},
                },
                "evidence_path": "/tmp/dir-a.json",
            },
        ]

        summary = evaluator._summarize(results)

        self.assertEqual(len(summary["failed_samples"]), 1)
        self.assertEqual(summary["failed_samples"][0]["sample_id"], "site-a")
        self.assertEqual(summary["company_site_breakdown"]["sample_count"], 1)
        self.assertEqual(summary["failed_samples_by_class"]["simple_supplier_site"][0]["failed_fields"], ["address", "supplier_name"])


class TestFoundationIntegrationImports(unittest.TestCase):
    # RU: Этот тест фиксирует реальный runtime-regression: supplier parsing не должен падать от циклического импорта integrations.foundation при простом импорте LLM submodule.
    def test_llm_submodule_import_is_cycle_safe(self) -> None:
        module = importlib.import_module("magon_standalone.integrations.foundation.llm")

        self.assertTrue(hasattr(module, "get_llm_adapter"))


if __name__ == "__main__":
    unittest.main()
