"""Deterministic, evidence-cited theory, lab, and project specialist profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.knowledge.service import knowledge_service


SpecialistType = Literal["theory", "lab", "project"]


class SpecialistRequest(BaseModel):
    course_id: str = Field(default="26ECAC401", min_length=1, max_length=80)
    specialist_type: SpecialistType
    work_item: str = Field(min_length=8, max_length=1000)
    chapter: int | None = Field(default=None, ge=1, le=14)


@dataclass(frozen=True)
class SpecialistProfile:
    specialist_type: SpecialistType
    label: str
    output_fields: tuple[str, ...]
    check_ids: tuple[str, ...]


PROFILES: dict[SpecialistType, SpecialistProfile] = {
    "theory": SpecialistProfile(
        "theory",
        "Theory Course Specialist",
        ("requested_topic", "faculty_confirmed_objectives", "evidence", "review_questions"),
        ("topic_present", "evidence_cited", "objectives_not_invented"),
    ),
    "lab": SpecialistProfile(
        "lab",
        "Practical Lab Specialist",
        ("requested_task", "procedure_scaffold", "completion_checks", "evidence"),
        ("task_present", "procedure_has_steps", "checks_are_observable", "evidence_cited"),
    ),
    "project": SpecialistProfile(
        "project",
        "Course Project Specialist",
        ("requested_deliverable", "checkpoint_scaffold", "evidence", "faculty_review_required"),
        ("deliverable_present", "checkpoints_have_outputs", "evidence_cited", "human_review_required"),
    ),
}


class SpecialistRegistry:
    """Create constrained, checkable scaffolds grounded in local course evidence."""

    @staticmethod
    def list_profiles() -> list[dict[str, Any]]:
        return [
            {
                "specialist_type": profile.specialist_type,
                "label": profile.label,
                "output_fields": list(profile.output_fields),
                "check_ids": list(profile.check_ids),
            }
            for profile in PROFILES.values()
        ]

    def run(self, request: SpecialistRequest) -> dict[str, Any]:
        profile = PROFILES[request.specialist_type]
        result = knowledge_service.search(
            request.work_item,
            course_id=request.course_id,
            chapter=request.chapter,
            top_k=4,
        )
        evidence = [
            {
                "chunk_id": match.chunk_id,
                "source_document": match.source_document,
                "source_location": match.source_location,
                "citation": match.source,
                "excerpt": match.matched_text[:700],
            }
            for match in result.matches
        ]

        if request.specialist_type == "theory":
            output = {
                "requested_topic": request.work_item,
                "faculty_confirmed_objectives": [],
                "review_questions": [
                    "Confirm the intended learning objectives.",
                    "Confirm the selected sources are approved for this course.",
                ],
                "note": "No faculty learning objectives or grading criteria were inferred.",
            }
            checks = {
                "topic_present": bool(request.work_item.strip()),
                "evidence_cited": bool(evidence),
                "objectives_not_invented": output["faculty_confirmed_objectives"] == [],
            }
        elif request.specialist_type == "lab":
            steps = [
                {"step": 1, "action": "Review the faculty-provided task and cited course material."},
                {"step": 2, "action": "Complete the requested practical work and record the result."},
                {"step": 3, "action": "Compare the result with the observable checks; request faculty clarification if ambiguous."},
            ]
            output = {
                "requested_task": request.work_item,
                "procedure_scaffold": steps,
                "completion_checks": [
                    "A result or artifact is present.",
                    "The result is linked to the requested task.",
                    "The cited source and any deviations are recorded.",
                ],
                "note": "Checks are structural examples, not a faculty rubric or safety approval.",
            }
            checks = {
                "task_present": bool(request.work_item.strip()),
                "procedure_has_steps": len(steps) >= 3,
                "checks_are_observable": bool(output["completion_checks"]),
                "evidence_cited": bool(evidence),
            }
        else:
            checkpoints = [
                {"checkpoint": 1, "output": "Faculty-defined scope and evidence plan"},
                {"checkpoint": 2, "output": "Faculty-defined prototype or interim artifact"},
                {"checkpoint": 3, "output": "Final deliverable and recorded review evidence"},
            ]
            output = {
                "requested_deliverable": request.work_item,
                "checkpoint_scaffold": checkpoints,
                "faculty_review_required": True,
                "note": "Checkpoint labels are a scaffold; dates, weights, teams, and rubric remain faculty-controlled.",
            }
            checks = {
                "deliverable_present": bool(request.work_item.strip()),
                "checkpoints_have_outputs": all(item["output"] for item in checkpoints),
                "evidence_cited": bool(evidence),
                "human_review_required": output["faculty_review_required"] is True,
            }

        return {
            "specialist_type": request.specialist_type,
            "specialist_label": profile.label,
            "generation_mode": "deterministic_evidence_cited_scaffold",
            "course_id": request.course_id,
            "output": output,
            "evidence": evidence,
            "checks": [
                {"check_id": key, "passed": passed}
                for key, passed in checks.items()
            ],
            "status": "READY_FOR_FACULTY_REVIEW" if all(checks.values()) else "INSUFFICIENT_EVIDENCE",
            "limitations": [
                "This deterministic scaffold is not an autonomous domain expert.",
                "Citations are retrieved candidates and do not establish entailment.",
                "Faculty must approve objectives, procedures, assessment criteria, and project checkpoints.",
            ],
        }


specialist_registry = SpecialistRegistry()
