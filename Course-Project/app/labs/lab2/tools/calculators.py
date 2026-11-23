"""Deterministic calculator and validation tools for grading arithmetic and workload estimation."""

import math

from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.schemas import (
    GradeWeightsInput,
    GradeWeightsTotalOutput,
    RubricSumInput,
    RubricSumOutput,
    ToolCategory,
    WorkloadInput,
    WorkloadOutput,
)


class CalculateGradeBreakdownTotalTool(BaseTool):
    """Tool that calculates the total percentage of grading weights and checks if it equals 100%."""

    name = "calculate_grade_breakdown_total"
    description = (
        "Calculate the total percentage sum of grading weights, determine validity (must equal 100%), "
        "and compute the deviation delta."
    )
    category = ToolCategory.CALCULATOR.value
    input_model = GradeWeightsInput
    output_model = GradeWeightsTotalOutput

    def _run(self, typed_input: GradeWeightsInput) -> GradeWeightsTotalOutput:
        """Sum grade weights with exact arithmetic and return structured validation."""
        total = round(sum(typed_input.weights), 4)
        is_valid = math.isclose(total, 100.0, rel_tol=1e-5)
        delta = round(abs(total - 100.0), 4)
        return GradeWeightsTotalOutput(
            total_percentage=total,
            is_valid=is_valid,
            delta_from_hundred=delta,
        )


class ValidateRubricSumTool(BaseTool):
    """Tool that calculates rubric criteria points summation and verifies against maximum points."""

    name = "validate_rubric_sum"
    description = (
        "Calculate the sum of individual rubric criteria points and compare against the expected maximum points."
    )
    category = ToolCategory.CHECKER.value
    input_model = RubricSumInput
    output_model = RubricSumOutput

    def _run(self, typed_input: RubricSumInput) -> RubricSumOutput:
        """Sum criteria points and check equivalence against expected total."""
        sum_pts = round(sum(typed_input.criteria_points), 4)
        is_matching = math.isclose(sum_pts, typed_input.expected_max_points, rel_tol=1e-5)
        diff = round(abs(sum_pts - typed_input.expected_max_points), 4)
        return RubricSumOutput(
            sum_points=sum_pts,
            expected_points=typed_input.expected_max_points,
            is_matching=is_matching,
            difference=diff,
        )


class ComputeWorkloadHoursTool(BaseTool):
    """Tool that computes total grading workload hours based on enrollment and time per submission."""

    name = "compute_workload_hours"
    description = (
        "Compute total grading workload in hours based on student enrollment, assignment count, "
        "and grading minutes per submission."
    )
    category = ToolCategory.CALCULATOR.value
    input_model = WorkloadInput
    output_model = WorkloadOutput

    def _run(self, typed_input: WorkloadInput) -> WorkloadOutput:
        """Compute workload hours deterministically."""
        total_mins = (
            typed_input.enrollment
            * typed_input.assignments_count
            * typed_input.grading_minutes_per_submission
        )
        total_hours = round(total_mins / 60.0, 2)
        batch_hours = (
            round((typed_input.enrollment * typed_input.grading_minutes_per_submission) / 60.0, 2)
            if typed_input.assignments_count > 0
            else 0.0
        )
        return WorkloadOutput(
            enrollment=typed_input.enrollment,
            assignments_count=typed_input.assignments_count,
            grading_minutes_per_submission=typed_input.grading_minutes_per_submission,
            total_grading_hours=total_hours,
            hours_per_assignment=batch_hours,
        )
