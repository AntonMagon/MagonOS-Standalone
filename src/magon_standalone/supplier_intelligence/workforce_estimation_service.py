"""Standalone workforce and labor estimation services.

Runtime role: Provides a pure estimation engine for labor hours, headcount,
overtime, and labor cost without any Odoo runtime dependency.
Inputs: Structured role demand, capacity, rate, and policy payloads.
Outputs: WorkforceEstimateResult payloads.
Does not: schedule jobs, mutate persistence, or depend on ERP models.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .contracts import (
    LaborPolicyInput,
    LaborRateInput,
    RoleEstimateBreakdown,
    ShiftCapacityInput,
    WorkforceEstimateInput,
    WorkforceEstimateResult,
)


@dataclass(frozen=True)
class WorkforceEstimationConfig:
    complexity_multipliers: dict[str, float] = field(
        default_factory=lambda: {
            "low": 0.85,
            "medium": 1.0,
            "high": 1.25,
            "critical": 1.5,
        }
    )
    default_shift_hours: float = 8.0
    default_overtime_threshold_hours: float = 8.0
    default_overtime_multiplier: float = 1.5
    default_currency_code: str = "VND"


class WorkforceEstimationEngine:
    """Pure estimator for labor hours, headcount, overtime, and labor cost."""

    def __init__(self, config: WorkforceEstimationConfig | None = None):
        self.config = config or WorkforceEstimationConfig()

    def estimate(self, estimation_input: WorkforceEstimateInput) -> WorkforceEstimateResult:
        """Estimate one workload using explicit demand, capacity, rate, and policy inputs."""
        policy_values = self._policy_map(estimation_input.policies)
        complexity_multiplier = self.config.complexity_multipliers.get(
            estimation_input.complexity_level.lower(),
            self.config.complexity_multipliers["medium"],
        )

        capacity_map = {item.role_code: item for item in estimation_input.shift_capacities}
        rate_map = {item.role_code: item for item in estimation_input.labor_rates}

        role_breakdown: list[RoleEstimateBreakdown] = []
        missing_skill_roles: list[str] = []
        total_required_hours = 0.0
        total_standard_cost = 0.0
        total_overtime_cost = 0.0
        total_overtime_hours = 0.0
        total_required_headcount = 0
        total_remaining_hours = 0.0

        bottleneck_role_code: str | None = None
        bottleneck_remaining = float("inf")

        for demand in estimation_input.role_demands:
            required_hours = (
                float(estimation_input.quantity)
                * float(demand.hours_per_unit)
                * float(demand.quantity_factor)
                * complexity_multiplier
            )
            total_required_hours += required_hours

            capacity = capacity_map.get(
                demand.role_code,
                ShiftCapacityInput(
                    role_code=demand.role_code,
                    shift_hours=float(policy_values.get("default_shift_hours", self.config.default_shift_hours)),
                    worker_count=0,
                    absence_count=0,
                    available_skill_codes=[],
                ),
            )
            rate = rate_map.get(
                demand.role_code,
                LaborRateInput(
                    role_code=demand.role_code,
                    base_hourly_rate=float(policy_values.get("default_hourly_rate", 0.0)),
                    overtime_multiplier=float(
                        policy_values.get("default_overtime_multiplier", self.config.default_overtime_multiplier)
                    ),
                    overtime_threshold_hours=float(
                        policy_values.get(
                            "default_overtime_threshold_hours",
                            self.config.default_overtime_threshold_hours,
                        )
                    ),
                    currency_code=str(policy_values.get("currency_code", self.config.default_currency_code)),
                ),
            )

            available_headcount = max(int(capacity.worker_count) - int(capacity.absence_count), 0)
            shift_hours = max(float(capacity.shift_hours), 0.01)
            available_hours = shift_hours * available_headcount
            if capacity.slot_available_hours is not None:
                available_hours = min(available_hours, max(float(capacity.slot_available_hours), 0.0))

            standard_capacity_per_worker = min(shift_hours, float(rate.overtime_threshold_hours))
            standard_capacity_hours = available_headcount * standard_capacity_per_worker
            standard_hours = min(required_hours, standard_capacity_hours)
            overtime_hours = max(required_hours - standard_hours, 0.0)

            standard_cost = standard_hours * float(rate.base_hourly_rate)
            overtime_cost = overtime_hours * float(rate.base_hourly_rate) * float(rate.overtime_multiplier)

            estimated_headcount = max(math.ceil(required_hours / shift_hours), 1) if required_hours > 0 else 0
            remaining_hours = available_hours - required_hours
            bottleneck = remaining_hours < 0

            total_standard_cost += standard_cost
            total_overtime_cost += overtime_cost
            total_overtime_hours += overtime_hours
            total_required_headcount += estimated_headcount
            total_remaining_hours += remaining_hours

            if remaining_hours < bottleneck_remaining:
                bottleneck_remaining = remaining_hours
                bottleneck_role_code = demand.role_code

            available_skills = set(capacity.available_skill_codes or [])
            required_skills = set(demand.required_skill_codes or [])
            if required_skills and not required_skills.issubset(available_skills):
                missing_skill_roles.append(demand.role_code)

            role_breakdown.append(
                RoleEstimateBreakdown(
                    role_code=demand.role_code,
                    required_hours=round(required_hours, 4),
                    available_hours=round(available_hours, 4),
                    estimated_headcount=estimated_headcount,
                    standard_hours=round(standard_hours, 4),
                    overtime_hours=round(overtime_hours, 4),
                    standard_cost=round(standard_cost, 2),
                    overtime_cost=round(overtime_cost, 2),
                    bottleneck=bottleneck,
                )
            )

        assumptions = [
            f"complexity_multiplier={complexity_multiplier}",
            f"default_shift_hours={policy_values.get('default_shift_hours', self.config.default_shift_hours)}",
            f"default_overtime_threshold_hours={policy_values.get('default_overtime_threshold_hours', self.config.default_overtime_threshold_hours)}",
            f"default_overtime_multiplier={policy_values.get('default_overtime_multiplier', self.config.default_overtime_multiplier)}",
        ]
        if estimation_input.target_completion_hours is not None:
            assumptions.append(f"target_completion_hours={estimation_input.target_completion_hours}")
        if missing_skill_roles:
            assumptions.append(f"missing_skill_roles={','.join(sorted(set(missing_skill_roles)))}")

        return WorkforceEstimateResult(
            specification_id=estimation_input.specification_id,
            estimated_hours=round(total_required_hours, 4),
            required_headcount=total_required_headcount,
            standard_labor_cost=round(total_standard_cost, 2),
            overtime_cost=round(total_overtime_cost, 2),
            total_labor_cost=round(total_standard_cost + total_overtime_cost, 2),
            overtime_required=total_overtime_hours > 0,
            time_remaining_hours=round(total_remaining_hours, 4),
            bottleneck_role_code=bottleneck_role_code,
            missing_skill_roles=sorted(set(missing_skill_roles)),
            role_breakdown=role_breakdown,
            assumptions=assumptions,
        )

    @staticmethod
    def _policy_map(policies: list[LaborPolicyInput]) -> dict[str, float | int | str]:
        result: dict[str, float | int | str] = {}
        for policy in policies:
            if policy.value_float is not None:
                result[policy.code] = policy.value_float
            elif policy.value_int is not None:
                result[policy.code] = policy.value_int
            elif policy.value_text is not None:
                result[policy.code] = policy.value_text
        return result
