"""Tool implementation for reading canonical course syllabi from the repository."""

from typing import Optional

from app.data.repository import CourseRepository, course_repo
from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.schemas import (
    CourseQueryInput,
    SyllabusOutput,
    ToolCategory,
)


class ReadCourseSyllabusTool(BaseTool):
    """Tool that retrieves the structured canonical syllabus for a given course ID."""

    name = "read_course_syllabus"
    description = (
        "Retrieve the canonical course syllabus including duration in weeks, "
        "weekly modules, target audience, prerequisites, and grading breakdown weights."
    )
    category = ToolCategory.READER.value
    input_model = CourseQueryInput
    output_model = SyllabusOutput

    def __init__(self, repository: Optional[CourseRepository] = None) -> None:
        self._repo = repository or course_repo

    def _run(self, typed_input: CourseQueryInput) -> SyllabusOutput:
        """Fetch the syllabus from the course repository and validate against SyllabusOutput schema."""
        raw_syllabus = self._repo.get_canonical_syllabus(typed_input.course_id)
        if raw_syllabus is None:
            raise ValueError(
                f"Course '{typed_input.course_id}' was not found in the course catalog repository."
            )
        return SyllabusOutput.model_validate(raw_syllabus)
