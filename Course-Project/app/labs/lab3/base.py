"""BaseSkill abstract class defining typed contracts, schema discovery, and execution timing."""

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel, ValidationError

from app.models.lab3_models import SkillExecutionRecord, SkillMetadata


class BaseSkill(ABC):
    """Abstract base class for all schema-typed, reusable agent skills."""

    name: str
    title: str
    description: str
    category: str
    version: str = "1.0.0"
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]

    def get_metadata(self) -> SkillMetadata:
        """Inspect and return schema metadata for dynamic discovery."""
        return SkillMetadata(
            name=self.name,
            title=self.title,
            description=self.description,
            category=self.category,
            version=self.version,
            input_schema=self.input_model.model_json_schema(),
            output_schema=self.output_model.model_json_schema(),
        )

    def execute(self, parameters: dict[str, Any]) -> SkillExecutionRecord:
        """Execute the skill with input/output validation, error handling, and performance timing."""
        execution_id = f"skexec-{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()

        # Step 1: Validate input against input_model
        try:
            validated_input = self.input_model.model_validate(parameters)
        except ValidationError as val_err:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return SkillExecutionRecord(
                execution_id=execution_id,
                skill_name=self.name,
                status="VALIDATION_ERROR",
                input_parameters=parameters,
                output_data=None,
                duration_ms=elapsed_ms,
                error=f"Input validation error: {str(val_err)}",
            )

        # Step 2: Execute domain skill logic
        try:
            result_model = self._run(validated_input)
            # Step 3: Validate output against output_model
            validated_output = self.output_model.model_validate(result_model)
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            return SkillExecutionRecord(
                execution_id=execution_id,
                skill_name=self.name,
                status="SUCCESS",
                input_parameters=validated_input.model_dump(),
                output_data=validated_output.model_dump(),
                duration_ms=elapsed_ms,
                error=None,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return SkillExecutionRecord(
                execution_id=execution_id,
                skill_name=self.name,
                status="EXECUTION_ERROR",
                input_parameters=parameters,
                output_data=None,
                duration_ms=elapsed_ms,
                error=f"Skill execution exception: {str(exc)}",
            )

    @abstractmethod
    def _run(self, validated_input: Any) -> Any:
        """Subclasses implement domain logic taking validated input and returning output model."""
        raise NotImplementedError
