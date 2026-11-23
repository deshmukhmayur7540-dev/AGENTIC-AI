"""Plan validator verifying educational invariants and mathematical consistency."""

from app.models.lab1_models import CourseWorkspacePlan


class PlanValidator:
    """Validates structural and mathematical invariants of CourseWorkspacePlan."""

    def validate(self, plan: CourseWorkspacePlan) -> None:
        """Verify grade breakdown totals, duration boundaries, and assignment constraints."""
        # 1. Validate Grade Breakdown Sum = 100.0% (Only if grading is established/present)
        if plan.grade_breakdown:
            total_weight = sum(item.weight_percentage for item in plan.grade_breakdown)
            if abs(total_weight - 100.0) > 0.05:
                discrepancy = total_weight - 100.0
                raise ValueError(
                    f"Invalid grade distribution: Grade weights sum to {total_weight:.1f}%, "
                    f"but must equal exactly 100.0%. Discrepancy: {discrepancy:+.1f} percentage points."
                )

        # 2. Validate Duration Weeks (Only if duration is specified)
        if plan.duration_weeks is not None:
            if not (1 <= plan.duration_weeks <= 24):
                raise ValueError(
                    f"Invalid course duration: {plan.duration_weeks} weeks. Duration must be between 1 and 24 weeks."
                )

            # 3. Validate Materials match Duration when weekly schedule is defined
            if len(plan.materials_and_notes) != plan.duration_weeks:
                raise ValueError(
                    f"Materials count mismatch: Expected {plan.duration_weeks} weekly modules, "
                    f"but found {len(plan.materials_and_notes)}."
                )

        # 4. Validate Assignment Due Dates
        if plan.assignments and plan.duration_weeks is not None:
            for asgn in plan.assignments:
                if asgn.due_week is not None and not (1 <= asgn.due_week <= plan.duration_weeks):
                    raise ValueError(
                        f"Assignment '{asgn.title}' due week {asgn.due_week} exceeds course duration ({plan.duration_weeks} weeks)."
                    )


plan_validator = PlanValidator()
