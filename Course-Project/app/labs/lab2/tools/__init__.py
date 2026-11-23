"""Tools package for Lab 2 (Tool-Using Agent)."""

from app.labs.lab2.tools.assignments import GetAssignmentSpecTool, GetRubricBreakdownTool
from app.labs.lab2.tools.base import BaseTool
from app.labs.lab2.tools.calculators import (
    CalculateGradeBreakdownTotalTool,
    ComputeWorkloadHoursTool,
    ValidateRubricSumTool,
)
from app.labs.lab2.tools.notes import SearchCourseNotesTool
from app.labs.lab2.tools.policy import GetCourseConfigTool, GetTAPolicyTool
from app.labs.lab2.tools.registry import ToolRegistry, tool_registry
from app.labs.lab2.tools.schemas import (
    AssignmentQueryInput,
    AssignmentSpecOutput,
    CourseConfigOutput,
    CourseNotesOutput,
    CourseNotesQueryInput,
    CourseQueryInput,
    GradeWeightsInput,
    GradeWeightsTotalOutput,
    RubricBreakdownOutput,
    RubricCriterion,
    RubricSumInput,
    RubricSumOutput,
    SyllabusGradeWeight,
    SyllabusModule,
    SyllabusOutput,
    TAPolicyOutput,
    TAPolicyQueryInput,
    ToolCategory,
    ToolDefinition,
    WorkloadInput,
    WorkloadOutput,
)
from app.labs.lab2.tools.syllabus import ReadCourseSyllabusTool


def create_default_registry() -> ToolRegistry:
    """Create and register all default Lab 2 typed tools."""
    registry = ToolRegistry()
    registry.register(ReadCourseSyllabusTool())
    registry.register(SearchCourseNotesTool())
    registry.register(GetAssignmentSpecTool())
    registry.register(GetRubricBreakdownTool())
    registry.register(GetCourseConfigTool())
    registry.register(GetTAPolicyTool())
    registry.register(CalculateGradeBreakdownTotalTool())
    registry.register(ValidateRubricSumTool())
    registry.register(ComputeWorkloadHoursTool())
    return registry


# Re-populate default global tool_registry
for tool in [
    ReadCourseSyllabusTool(),
    SearchCourseNotesTool(),
    GetAssignmentSpecTool(),
    GetRubricBreakdownTool(),
    GetCourseConfigTool(),
    GetTAPolicyTool(),
    CalculateGradeBreakdownTotalTool(),
    ValidateRubricSumTool(),
    ComputeWorkloadHoursTool(),
]:
    if tool_registry.get_tool(tool.name) is None:
        tool_registry.register(tool)


__all__ = [
    "BaseTool",
    "ToolRegistry",
    "tool_registry",
    "create_default_registry",
    "ToolCategory",
    "ToolDefinition",
    "CourseQueryInput",
    "SyllabusModule",
    "SyllabusGradeWeight",
    "SyllabusOutput",
    "ReadCourseSyllabusTool",
    "CourseNotesQueryInput",
    "CourseNotesOutput",
    "SearchCourseNotesTool",
    "AssignmentQueryInput",
    "AssignmentSpecOutput",
    "GetAssignmentSpecTool",
    "RubricCriterion",
    "RubricBreakdownOutput",
    "GetRubricBreakdownTool",
    "CourseConfigOutput",
    "GetCourseConfigTool",
    "TAPolicyQueryInput",
    "TAPolicyOutput",
    "GetTAPolicyTool",
    "GradeWeightsInput",
    "GradeWeightsTotalOutput",
    "CalculateGradeBreakdownTotalTool",
    "RubricSumInput",
    "RubricSumOutput",
    "ValidateRubricSumTool",
    "WorkloadInput",
    "WorkloadOutput",
    "ComputeWorkloadHoursTool",
]
