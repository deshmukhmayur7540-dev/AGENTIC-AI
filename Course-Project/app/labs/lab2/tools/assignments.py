"""Tool implementations for retrieving assignment specifications and rubric breakdowns."""

from typing import Optional

from app.data.repository import CourseRepository, course_repo
from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.schemas import (
    AssignmentQueryInput,
    AssignmentSpecOutput,
    RubricBreakdownOutput,
    ToolCategory,
)


class GetAssignmentSpecTool(BaseTool):
    """Tool that retrieves structured assignment specifications."""

    name = "get_assignment_spec"
    description = (
        "Retrieve structured assignment specifications including due week, "
        "deliverables, maximum points, and submission requirements."
    )
    category = ToolCategory.READER.value
    input_model = AssignmentQueryInput
    output_model = AssignmentSpecOutput

    def __init__(self, repository: Optional[CourseRepository] = None) -> None:
        self._repo = repository or course_repo

    def _run(self, typed_input: AssignmentQueryInput) -> AssignmentSpecOutput:
        """Fetch assignment spec from repository and validate output schema."""
        raw_spec = self._repo.get_canonical_assignment(typed_input.course_id, typed_input.assignment_id)
        if raw_spec is None:
            raise ValueError(
                f"Assignment '{typed_input.assignment_id}' for course '{typed_input.course_id}' was not found in the repository."
            )
        return AssignmentSpecOutput.model_validate(raw_spec)


class GetRubricBreakdownTool(BaseTool):
    """Tool that retrieves rubric criteria, point distributions, and evidence standards."""

    name = "get_rubric_breakdown"
    description = (
        "Retrieve the grading rubric breakdown with individual criteria points, "
        "descriptions, and total points for a given assignment."
    )
    category = ToolCategory.READER.value
    input_model = AssignmentQueryInput
    output_model = RubricBreakdownOutput

    def __init__(self, repository: Optional[CourseRepository] = None) -> None:
        self._repo = repository or course_repo

    def _run(self, typed_input: AssignmentQueryInput) -> RubricBreakdownOutput:
        """Fetch rubric criteria from repository and validate output schema."""
        raw_rubric = self._repo.get_canonical_rubric(typed_input.course_id, typed_input.assignment_id)
        if raw_rubric is None:
            raise ValueError(
                f"Rubric for assignment '{typed_input.assignment_id}' in course '{typed_input.course_id}' was not found in the repository."
            )
        return RubricBreakdownOutput.model_validate(raw_rubric)
