"""Tool implementation for searching structured course notes and materials."""

from typing import Optional

from app.data.repository import CourseRepository, course_repo
from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.schemas import (
    CourseNotesOutput,
    CourseNotesQueryInput,
    ToolCategory,
)


class SearchCourseNotesTool(BaseTool):
    """Tool that searches structured course lecture notes, topics, and materials."""

    name = "search_course_notes"
    description = (
        "Search structured course lecture notes, reading materials, and weekly topics by query keywords."
    )
    category = ToolCategory.READER.value
    input_model = CourseNotesQueryInput
    output_model = CourseNotesOutput

    def __init__(self, repository: Optional[CourseRepository] = None) -> None:
        self._repo = repository or course_repo

    def _run(self, typed_input: CourseNotesQueryInput) -> CourseNotesOutput:
        """Search course notes from repository and validate output schema."""
        raw_results = self._repo.search_canonical_notes(typed_input.course_id, typed_input.query)
        if raw_results is None:
            raise ValueError(
                f"Course '{typed_input.course_id}' was not found in the course notes repository."
            )
        return CourseNotesOutput.model_validate(raw_results)
