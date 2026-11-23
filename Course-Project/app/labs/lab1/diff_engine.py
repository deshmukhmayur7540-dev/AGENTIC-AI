"""Diff engine computing exact atomic field-level structured diffs between plan versions."""

import copy
from typing import Any
from app.models.lab1_models import CourseWorkspacePlan, StructuredDiffItem


class DiffEngine:
    """Computes exact, field-level structured diffs by comparing two CourseWorkspacePlan objects."""

    def compute_diff(self, old_plan: CourseWorkspacePlan, new_plan: CourseWorkspacePlan) -> list[StructuredDiffItem]:
        """Compare old and new plan objects and return all atomic field alterations."""
        diffs: list[StructuredDiffItem] = []

        # 1. Compare Duration Weeks
        if old_plan.duration_weeks != new_plan.duration_weeks:
            diffs.append(
                StructuredDiffItem(
                    section="overview",
                    action="MODIFIED",
                    path="duration_weeks",
                    old_value=old_plan.duration_weeks,
                    new_value=new_plan.duration_weeks,
                    change_description=f"Updated course duration from {old_plan.duration_weeks} to {new_plan.duration_weeks} weeks.",
                )
            )

        # 2. Compare Weekly Notes & Materials
        old_mat_count = len(old_plan.materials_and_notes)
        new_mat_count = len(new_plan.materials_and_notes)

        # Check for added weeks / sections
        if new_mat_count > old_mat_count:
            for i in range(old_mat_count, new_mat_count):
                new_mat = new_plan.materials_and_notes[i]
                loc = f"Week {new_mat.week}" if new_mat.week is not None else (new_mat.section_label or "Section")
                diffs.append(
                    StructuredDiffItem(
                        section="materials_and_notes",
                        action="ADDED",
                        path=f"materials_and_notes[{i}]",
                        old_value=None,
                        new_value=new_mat.model_dump(),
                        change_description=f"Added '{new_mat.title}' module for {loc}.",
                    )
                )

        # Check modifications on existing weeks / sections
        common_mat_count = min(old_mat_count, new_mat_count)
        for i in range(common_mat_count):
            old_m = old_plan.materials_and_notes[i]
            new_m = new_plan.materials_and_notes[i]
            loc = f"Week {new_m.week}" if new_m.week is not None else (new_m.section_label or "Section")

            if old_m.title != new_m.title:
                diffs.append(
                    StructuredDiffItem(
                        section="materials_and_notes",
                        action="MODIFIED",
                        path=f"materials_and_notes[{i}].title",
                        old_value=old_m.title,
                        new_value=new_m.title,
                        change_description=f"Updated {loc} module title from '{old_m.title}' to '{new_m.title}'.",
                    )
                )

            if old_m.topics != new_m.topics:
                diffs.append(
                    StructuredDiffItem(
                        section="materials_and_notes",
                        action="MODIFIED",
                        path=f"materials_and_notes[{i}].topics",
                        old_value=old_m.topics,
                        new_value=new_m.topics,
                        change_description=f"Updated topic list for {loc} ({new_m.title}).",
                    )
                )

            if old_m.reading_materials != new_m.reading_materials:
                diffs.append(
                    StructuredDiffItem(
                        section="materials_and_notes",
                        action="MODIFIED",
                        path=f"materials_and_notes[{i}].reading_materials",
                        old_value=old_m.reading_materials,
                        new_value=new_m.reading_materials,
                        change_description=f"Updated reading materials for {loc}.",
                    )
                )

        # 3. Compare Assignments
        old_asgn_ids = {a.assignment_id for a in old_plan.assignments}
        for idx, new_a in enumerate(new_plan.assignments):
            if new_a.assignment_id not in old_asgn_ids:
                diffs.append(
                    StructuredDiffItem(
                        section="assignments",
                        action="ADDED",
                        path=f"assignments[{idx}]",
                        old_value=None,
                        new_value=new_a.model_dump(),
                        change_description=f"Added new assignment '{new_a.title}' (Due Week {new_a.due_week}).",
                    )
                )

        # Check modifications on existing assignments
        old_asgn_map = {a.assignment_id: (i, a) for i, a in enumerate(old_plan.assignments)}
        for new_idx, new_a in enumerate(new_plan.assignments):
            if new_a.assignment_id in old_asgn_map:
                old_idx, old_a = old_asgn_map[new_a.assignment_id]

                if old_a.due_week != new_a.due_week:
                    diffs.append(
                        StructuredDiffItem(
                            section="assignments",
                            action="MODIFIED",
                            path=f"assignments[{new_idx}].due_week",
                            old_value=old_a.due_week,
                            new_value=new_a.due_week,
                            change_description=f"Rescheduled '{new_a.title}' due date from Week {old_a.due_week} to Week {new_a.due_week}.",
                        )
                    )

                if old_a.deliverables != new_a.deliverables:
                    diffs.append(
                        StructuredDiffItem(
                            section="assignments",
                            action="MODIFIED",
                            path=f"assignments[{new_idx}].deliverables",
                            old_value=old_a.deliverables,
                            new_value=new_a.deliverables,
                            change_description=f"Updated deliverables for assignment '{new_a.title}'.",
                        )
                    )

                if old_a.weight_percentage != new_a.weight_percentage:
                    diffs.append(
                        StructuredDiffItem(
                            section="assignments",
                            action="MODIFIED",
                            path=f"assignments[{new_idx}].weight_percentage",
                            old_value=old_a.weight_percentage,
                            new_value=new_a.weight_percentage,
                            change_description=f"Updated weight for assignment '{new_a.title}' from {old_a.weight_percentage}% to {new_a.weight_percentage}%.",
                        )
                    )

        # 4. Compare Grade Breakdown
        old_grades_map = {g.category.lower(): (i, g) for i, g in enumerate(old_plan.grade_breakdown)}
        for new_idx, new_g in enumerate(new_plan.grade_breakdown):
            key = new_g.category.lower()
            if key in old_grades_map:
                old_idx, old_g = old_grades_map[key]
                if old_g.weight_percentage != new_g.weight_percentage:
                    diffs.append(
                        StructuredDiffItem(
                            section="grade_breakdown",
                            action="MODIFIED",
                            path=f"grade_breakdown[{new_idx}].weight_percentage",
                            old_value=old_g.weight_percentage,
                            new_value=new_g.weight_percentage,
                            change_description=f"Adjusted '{new_g.category}' grading weight from {old_g.weight_percentage}% to {new_g.weight_percentage}%.",
                        )
                    )

        # 5. Compare Staffing (TA Hours)
        if old_plan.ta_allocation_hours != new_plan.ta_allocation_hours:
            diffs.append(
                StructuredDiffItem(
                    section="overview",
                    action="MODIFIED",
                    path="ta_allocation_hours",
                    old_value=old_plan.ta_allocation_hours,
                    new_value=new_plan.ta_allocation_hours,
                    change_description=f"Adjusted weekly TA allocation from {old_plan.ta_allocation_hours}h to {new_plan.ta_allocation_hours}h.",
                )
            )

        # 6. Compare Prerequisites
        if old_plan.prerequisites != new_plan.prerequisites:
            diffs.append(
                StructuredDiffItem(
                    section="overview",
                    action="MODIFIED",
                    path="prerequisites",
                    old_value=old_plan.prerequisites,
                    new_value=new_plan.prerequisites,
                    change_description="Updated course prerequisites.",
                )
            )

        return diffs


diff_engine = DiffEngine()
