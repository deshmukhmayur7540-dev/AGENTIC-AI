"""Revision engine orchestrating the complete Lab 1 revision pipeline."""

from datetime import datetime, timezone
from typing import Any
from app.models.lab1_models import (
    CourseWorkspacePlan,
    RevisionRequest,
    PlanRevisionResponse,
    StructuredDiffItem,
)
from app.labs.lab1.intent_parser import intent_parser
from app.labs.lab1.plan_mutator import plan_mutator
from app.labs.lab1.validator import plan_validator
from app.labs.lab1.diff_engine import diff_engine


class RevisionEngine:
    """Orchestrates structured intent extraction, plan mutation, validation, and exact diffing."""

    def revise(self, current_plan: CourseWorkspacePlan, request: RevisionRequest) -> PlanRevisionResponse:
        """Apply targeted modifications to create an immutable new version of the plan with exact diff tracking."""
        prompt = request.revision_prompt.strip()

        # 1. Extract Structured Change Intents
        intents = intent_parser.parse(prompt)
        if not intents:
            raise ValueError(
                f"Unsupported or ambiguous revision request: '{prompt}'. "
                f"No actionable course modifications could be detected. "
                f"Please specify concrete changes such as course duration, adding assignments, modifying grade weights, or weekly topics."
            )

        # 2. Mutate deep-copied plan
        mutated_data = plan_mutator.mutate(current_plan, intents)

        # 3. Versioning (Increment version, e.g. 1.0 -> 1.1)
        old_version = current_plan.version
        new_version = self._increment_version(old_version)
        mutated_data["version"] = new_version
        mutated_data["updated_at"] = datetime.now(timezone.utc)

        # 4. Construct Pydantic Model
        revised_plan = CourseWorkspacePlan.model_validate(mutated_data)

        # 5. Strict Invariant & Mathematical Validation
        plan_validator.validate(revised_plan)

        # 6. Compute Exact Old-vs-New Structured Diffs
        diffs = diff_engine.compute_diff(current_plan, revised_plan)
        if not diffs:
            raise ValueError(
                f"Revision request '{prompt}' did not produce any structural field changes to the plan."
            )

        # 7. Synthesize Changelog Summary
        changelog_lines = [f"• {d.change_description}" for d in diffs]
        changelog_summary = "\n".join(changelog_lines)

        return PlanRevisionResponse(
            previous_version=old_version,
            current_version=new_version,
            revised_plan=revised_plan,
            changelog_summary=changelog_summary,
            structured_diffs=diffs,
        )

    def _increment_version(self, version_str: str) -> str:
        """Bump minor version (e.g. 1.0 -> 1.1, 1.1 -> 1.2)."""
        parts = version_str.split(".")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            major, minor = int(parts[0]), int(parts[1])
            return f"{major}.{minor + 1}"
        return f"{version_str}.1"


revision_engine = RevisionEngine()
