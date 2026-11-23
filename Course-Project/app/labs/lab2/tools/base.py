"""BaseTool abstract base class enforcing typed contract execution and recording."""

from abc import ABC, abstractmethod
import time
import uuid
from typing import Any, Type, Optional
from pydantic import BaseModel, ValidationError

from app.models.lab2_models import ToolCallRecord, ToolExecutionStatus
from app.labs.lab2.tools.schemas import ToolDefinition, ToolCategory


class BaseTool(ABC):
    """Abstract base class for all typed agent tools in CourseAgentAI.

    Enforces the pipeline:
    raw input -> input validation -> typed input -> tool execution -> typed output validation -> ToolCallRecord
    """

    name: str
    description: str
    category: str = ToolCategory.READER.value
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]

    def get_definition(self) -> ToolDefinition:
        """Return the declarative JSON schema definition for this tool."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=str(self.category),
            input_schema=self.input_model.model_json_schema(),
            output_schema=self.output_model.model_json_schema(),
        )

    def execute(self, raw_params: dict[str, Any]) -> ToolCallRecord:
        """Execute the tool with strict runtime validation and audit recording.

        Never raises unhandled exceptions to the caller; records errors in the ToolCallRecord.
        """
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        start_time = time.perf_counter()

        # Step 1: Input Validation
        if not isinstance(raw_params, dict):
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolCallRecord(
                call_id=call_id,
                tool_name=self.name,
                validated_input={},
                output_data=None,
                status=ToolExecutionStatus.VALIDATION_ERROR,
                execution_duration_ms=round(duration_ms, 3),
                error=f"Invalid parameter format: expected dict, got {type(raw_params).__name__}",
            )

        try:
            typed_input = self.input_model.model_validate(raw_params)
            validated_input_dict = typed_input.model_dump()
        except (ValidationError, TypeError, ValueError) as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolCallRecord(
                call_id=call_id,
                tool_name=self.name,
                validated_input=raw_params if isinstance(raw_params, dict) else {},
                output_data=None,
                status=ToolExecutionStatus.VALIDATION_ERROR,
                execution_duration_ms=round(duration_ms, 3),
                error=f"Input validation error: {str(exc)}",
            )

        # Step 2: Tool Execution
        try:
            raw_output = self._run(typed_input)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolCallRecord(
                call_id=call_id,
                tool_name=self.name,
                validated_input=validated_input_dict,
                output_data=None,
                status=ToolExecutionStatus.EXECUTION_ERROR,
                execution_duration_ms=round(duration_ms, 3),
                error=f"Execution error: {str(exc)}",
            )

        # Step 3: Typed Output Validation
        try:
            if isinstance(raw_output, self.output_model):
                typed_output = raw_output
            elif isinstance(raw_output, dict):
                typed_output = self.output_model.model_validate(raw_output)
            else:
                raise ValueError(
                    f"Output must be an instance of {self.output_model.__name__} or dict, "
                    f"got {type(raw_output).__name__}"
                )

            output_dict = typed_output.model_dump()
        except (ValidationError, TypeError, ValueError) as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolCallRecord(
                call_id=call_id,
                tool_name=self.name,
                validated_input=validated_input_dict,
                output_data=None,
                status=ToolExecutionStatus.EXECUTION_ERROR,
                execution_duration_ms=round(duration_ms, 3),
                error=f"Output validation error: {str(exc)}",
            )

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ToolCallRecord(
            call_id=call_id,
            tool_name=self.name,
            validated_input=validated_input_dict,
            output_data=output_dict,
            status=ToolExecutionStatus.SUCCESS,
            execution_duration_ms=round(duration_ms, 3),
            error=None,
        )

    @abstractmethod
    def _run(self, typed_input: Any) -> Any:
        """Subclass implementation that executes the tool logic."""
        raise NotImplementedError("Tools must implement _run")
