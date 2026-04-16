import json
import unittest
from pathlib import Path

from magon_standalone.supplier_intelligence.contracts import (
    LaborPolicyInput,
    LaborRateInput,
    ShiftCapacityInput,
    WorkforceEstimateInput,
    WorkforceRoleDemand,
)
from magon_standalone.supplier_intelligence.workforce_estimation_service import WorkforceEstimationEngine


class TestWorkforceEstimation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "workforce_cases_vn.json"
        cls.cases = json.loads(fixture_path.read_text())

    def setUp(self):
        self.engine = WorkforceEstimationEngine()

    def _build_input(self, key: str) -> WorkforceEstimateInput:
        row = self.cases[key]["input"]
        return WorkforceEstimateInput(
            specification_id=row.get("specification_id"),
            process_type=row["process_type"],
            quantity=row["quantity"],
            complexity_level=row["complexity_level"],
            target_completion_hours=row.get("target_completion_hours"),
            role_demands=[WorkforceRoleDemand(**item) for item in row.get("role_demands", [])],
            shift_capacities=[ShiftCapacityInput(**item) for item in row.get("shift_capacities", [])],
            labor_rates=[LaborRateInput(**item) for item in row.get("labor_rates", [])],
            policies=[LaborPolicyInput(**item) for item in row.get("policies", [])],
        )

    def test_normal_shift_case(self):
        result = self.engine.estimate(self._build_input("normal_shift"))
        self.assertAlmostEqual(result.estimated_hours, 10.0, places=4)
        self.assertEqual(result.required_headcount, 2)
        self.assertFalse(result.overtime_required)
        self.assertAlmostEqual(result.standard_labor_cost, 1200000.0, places=2)
        self.assertAlmostEqual(result.overtime_cost, 0.0, places=2)
        self.assertAlmostEqual(result.time_remaining_hours, 6.0, places=4)

    def test_overloaded_shift_case(self):
        result = self.engine.estimate(self._build_input("overloaded_shift"))
        self.assertTrue(result.overtime_required)
        self.assertEqual(result.required_headcount, 3)
        self.assertLess(result.time_remaining_hours, 0)
        self.assertEqual(result.bottleneck_role_code, "LABEL_OPERATOR")
        self.assertGreater(result.overtime_cost, 0.0)

    def test_missing_skill_case(self):
        result = self.engine.estimate(self._build_input("missing_skill"))
        self.assertIn("PACK_OPERATOR", result.missing_skill_roles)
        self.assertFalse(result.overtime_required)
        self.assertEqual(result.bottleneck_role_code, "PACK_OPERATOR")

    def test_overtime_case(self):
        result = self.engine.estimate(self._build_input("overtime_case"))
        self.assertTrue(result.overtime_required)
        self.assertAlmostEqual(result.estimated_hours, 12.0, places=4)
        self.assertAlmostEqual(result.overtime_cost, 936000.0, places=2)
        self.assertAlmostEqual(result.total_labor_cost, 1976000.0, places=2)
        self.assertAlmostEqual(result.time_remaining_hours, 0.0, places=4)

    def test_absence_impact_case(self):
        result = self.engine.estimate(self._build_input("absence_impact"))
        self.assertTrue(result.overtime_required)
        self.assertAlmostEqual(result.time_remaining_hours, -4.0, places=4)
        self.assertEqual(result.bottleneck_role_code, "PROMO_OPERATOR")
        self.assertIn("complexity_multiplier=1.0", result.assumptions)


if __name__ == "__main__":
    unittest.main()
