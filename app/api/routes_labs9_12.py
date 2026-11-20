"""Project APIs for Labs 9-12.

The repository contains no official handouts for these labs. These routes implement
only the bounded scopes documented in the lab registry and associated project notes.
"""

from typing import Any, Self

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from app.auth import AuthenticatedUser, get_current_user, require_course_access, require_roles
from app.labs.lab9.agent import evidence_verifier
from app.labs.lab10.cloud_ops import cloud_ops_agent
from app.labs.lab10.validator import self_healing_validator
from app.labs.lab11.benchmarks import benchmark_factory
from app.labs.lab12.governance import governed_change_store
from app.labs.lab13.specialists import SpecialistRequest, specialist_registry
from app.models.common import APIEnvelope

router = APIRouter(prefix="/api", tags=["Labs 9-12"])


class EvidenceRequest(BaseModel):
    claims: list[str] = Field(min_length=1, max_length=10)
    chapter: int | None = Field(default=None, ge=1, le=4)

    @field_validator("claims")
    @classmethod
    def validate_claim_text(cls, claims: list[str]) -> list[str]:
        cleaned = [claim.strip() for claim in claims]
        if any(not claim for claim in cleaned):
            raise ValueError("Claims must contain non-whitespace text.")
        if any(len(claim) > 1000 for claim in cleaned):
            raise ValueError("Each claim must be at most 1,000 characters.")
        return cleaned


class GradeWeight(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    weight: float = Field(ge=0, le=100)


class ValidationRequest(BaseModel):
    weights: list[GradeWeight] = Field(min_length=1, max_length=12)
    target: float = Field(default=100, gt=0, le=100)
    apply_simulated_repair: bool = False
    repair_index: int | None = Field(default=None, ge=0)
    max_attempts: int = Field(default=3, ge=1, le=3)
    inject_repair_failure: bool = False

    @model_validator(mode="after")
    def validate_repair_options(self) -> Self:
        if self.apply_simulated_repair:
            if self.repair_index is None or self.repair_index >= len(self.weights):
                raise ValueError("A valid repair_index is required for simulated repair.")
        elif self.repair_index is not None or self.inject_repair_failure:
            raise ValueError("Repair options require apply_simulated_repair=true.")
        return self


class CloudOpsRepairRequest(BaseModel):
    approved: bool


class CloudOpsRollbackRequest(BaseModel):
    remediation_id: str = Field(min_length=1, max_length=40)


class GovernanceProposalRequest(BaseModel):
    resource_id: str = Field(min_length=1, max_length=120)
    current_value: dict[str, Any]
    proposed_value: dict[str, Any]
    summary: str = Field(min_length=3, max_length=500)


class GovernanceDecisionRequest(BaseModel):
    approved: bool
    actor: str = Field(min_length=1, max_length=120)
    comment: str | None = Field(default=None, max_length=1000)


class GovernanceRollbackRequest(BaseModel):
    actor: str = Field(min_length=1, max_length=120)


class SpecBuildRequest(BaseModel):
    course_id: str = Field(default="26ECAC401", min_length=1, max_length=80)
    specialist_type: str = Field(pattern="^(theory|lab|project)$")
    requirement: str = Field(min_length=8, max_length=1000)
    chapter: int | None = Field(default=None, ge=1, le=14)


@router.post("/lab9/grounding/verify", response_model=APIEnvelope[dict[str, Any]])
async def verify_claim_evidence(
    request: EvidenceRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    require_course_access(user, "26ECAC401")
    result = evidence_verifier.verify_claims(request.claims, chapter=request.chapter)
    return APIEnvelope(success=True, data=result, trace_id="lab9-evidence")


@router.post("/lab10/validation/repair", response_model=APIEnvelope[dict[str, Any]])
async def validate_and_propose_repair(
    request: ValidationRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    require_course_access(user, "26ECAC401")
    weights = [item.model_dump() for item in request.weights]
    if request.apply_simulated_repair:
        if request.repair_index is None:
            raise HTTPException(status_code=422, detail="A valid repair_index is required for simulated repair.")
        result = self_healing_validator.simulate_bounded_repair(
            weights,
            target=request.target,
            repair_index=request.repair_index,
            max_attempts=request.max_attempts,
            inject_repair_failure=request.inject_repair_failure,
        )
    else:
        result = self_healing_validator.validate_grade_weights(weights, target=request.target)
    return APIEnvelope(success=True, data=result, trace_id="lab10-validation")


@router.get("/lab10/cloud-ops/diagnosis", response_model=APIEnvelope[dict[str, Any]])
async def diagnose_simulated_deployment(
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    require_course_access(user, "26ECAC401")
    status = cloud_ops_agent.get_cluster_status()
    diagnosis = cloud_ops_agent.diagnose_infrastructure()
    return APIEnvelope(
        success=True,
        data={
            "simulation_only": True,
            "provider_contacted": False,
            "deployment_status": "FAILED" if diagnosis["overall_health"] == "DEGRADED" else "HEALTHY",
            "environment": status["cluster"]["environment"],
            "diagnosis": diagnosis,
            "disclosure": status["disclosure"],
        },
        trace_id="lab10-cloud-ops-diagnosis",
    )


@router.post("/lab10/cloud-ops/repair", response_model=APIEnvelope[dict[str, Any]])
async def repair_simulated_deployment(
    request: CloudOpsRepairRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    require_course_access(user, "26ECAC401")
    try:
        plan = cloud_ops_agent.propose_remediation(actor=user.user_id)
        result = cloud_ops_agent.apply_remediation(plan["remediation_id"], request.approved, actor=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    cluster = cloud_ops_agent.get_cluster_status()["cluster"]
    worker = cluster["components"]["worker-swarm"]
    return APIEnvelope(
        success=True,
        data={
            "simulation_only": True,
            "provider_contacted": False,
            "proposal": plan,
            "result": result,
            "worker_status": worker["status"],
            "worker_replicas": worker["replicas"],
            "rollback_available": result.get("applied", False),
        },
        trace_id=f"lab10-cloud-ops-{plan['remediation_id']}",
    )


@router.post("/lab10/cloud-ops/rollback", response_model=APIEnvelope[dict[str, Any]])
async def rollback_simulated_deployment(
    request: CloudOpsRollbackRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    require_course_access(user, "26ECAC401")
    try:
        result = cloud_ops_agent.rollback_remediation(request.remediation_id, actor=user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    worker = cloud_ops_agent.get_cluster_status()["cluster"]["components"]["worker-swarm"]
    return APIEnvelope(
        success=True,
        data={
            "simulation_only": True,
            "provider_contacted": False,
            "result": result,
            "worker_status": worker["status"],
            "worker_replicas": worker["replicas"],
        },
        trace_id=f"lab10-cloud-ops-{request.remediation_id}-rollback",
    )


@router.get("/lab11/benchmarks", response_model=APIEnvelope[dict[str, Any]])
@router.post("/lab11/benchmarks/run", response_model=APIEnvelope[dict[str, Any]])
async def run_benchmarks(user: AuthenticatedUser = Depends(get_current_user)):
    require_course_access(user, "26ECAC401")
    return APIEnvelope(success=True, data=benchmark_factory.run(), trace_id="lab11-benchmarks")


@router.post("/lab11/spec-build", response_model=APIEnvelope[dict[str, Any]])
async def build_from_spec(
    request: SpecBuildRequest,
    user: AuthenticatedUser = Depends(require_roles("FACULTY", "ADMIN")),
):
    """Build and check a bounded structured artifact; this endpoint never executes generated code."""
    require_course_access(user, request.course_id)
    specialist_result = specialist_registry.run(
        SpecialistRequest(
            course_id=request.course_id,
            specialist_type=request.specialist_type,
            work_item=request.requirement,
            chapter=request.chapter,
        )
    )
    tests = [
        {
            "test_id": "artifact_is_structured",
            "passed": isinstance(specialist_result.get("output"), dict)
            and bool(specialist_result["output"]),
        },
        {
            "test_id": "required_checks_present",
            "passed": bool(specialist_result.get("checks"))
            and all("passed" in check for check in specialist_result["checks"]),
        },
        {
            "test_id": "source_provenance_present",
            "passed": bool(specialist_result.get("evidence"))
            and all(item.get("source_document") and item.get("citation") for item in specialist_result["evidence"]),
        },
        {
            "test_id": "specialist_checks_pass",
            "passed": all(check["passed"] for check in specialist_result.get("checks", [])),
        },
    ]
    passed = all(test["passed"] for test in tests)
    return APIEnvelope(
        success=True,
        data={
            "status": "CHECKS_PASSED" if passed else "CHECKS_FAILED",
            "artifact_type": "structured_course_work_item",
            "artifact": specialist_result,
            "acceptance_tests": tests,
            "artifact_released": False,
            "release_requires_faculty_approval": True,
            "execution_boundary": "No generated code or user-supplied test code was executed.",
            "limitations": [
                "This is a constrained structured-artifact builder, not a general requirement-to-source-code generator.",
                "Checks validate artifact structure and evidence presence, not correctness of domain conclusions.",
            ],
        },
        trace_id="lab11-spec-build",
    )


@router.get("/lab13/specialists", response_model=APIEnvelope[list[dict[str, Any]]])
async def list_specialist_profiles(
    course_id: str = "26ECAC401",
    user: AuthenticatedUser = Depends(get_current_user),
):
    require_course_access(user, course_id)
    return APIEnvelope(
        success=True,
        data=specialist_registry.list_profiles(),
        trace_id="lab13-specialists",
    )


@router.post("/lab13/specialists/run", response_model=APIEnvelope[dict[str, Any]])
async def run_specialist(
    request: SpecialistRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    require_course_access(user, request.course_id)
    result = specialist_registry.run(request)
    return APIEnvelope(success=True, data=result, trace_id=f"lab13-{request.specialist_type}")


@router.get("/lab12/proposals", response_model=APIEnvelope[list[dict[str, Any]]])
async def list_governance_proposals(user: AuthenticatedUser = Depends(require_roles("ADMIN"))):
    return APIEnvelope(success=True, data=governed_change_store.list(), trace_id="lab12-proposals")


@router.get("/lab12/proposals/{proposal_id}", response_model=APIEnvelope[dict[str, Any]])
async def get_governance_proposal(
    proposal_id: str,
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
):
    proposal = governed_change_store.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Governance proposal was not found.")
    return APIEnvelope(success=True, data=proposal, trace_id=f"lab12-{proposal_id}")


@router.get("/lab12/proposals/{proposal_id}/audit", response_model=APIEnvelope[list[dict[str, Any]]])
async def get_governance_audit(
    proposal_id: str,
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
):
    if not governed_change_store.get(proposal_id):
        raise HTTPException(status_code=404, detail="Governance proposal was not found.")
    return APIEnvelope(
        success=True,
        data=governed_change_store.get_audit_history(proposal_id),
        trace_id=f"lab12-{proposal_id}-audit",
    )


@router.post("/lab12/proposals", response_model=APIEnvelope[dict[str, Any]])
async def create_governance_proposal(
    request: GovernanceProposalRequest,
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
):
    try:
        proposal = governed_change_store.propose(
            request.resource_id,
            request.current_value,
            request.proposed_value,
            request.summary,
            actor=user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return APIEnvelope(success=True, data=proposal, trace_id=f"lab12-{proposal['proposal_id']}")


@router.post("/lab12/proposals/{proposal_id}/decision", response_model=APIEnvelope[dict[str, Any]])
async def decide_governance_proposal(
    proposal_id: str,
    request: GovernanceDecisionRequest,
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
):
    try:
        proposal = governed_change_store.decide(proposal_id, request.approved, user.user_id, request.comment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return APIEnvelope(success=True, data=proposal, trace_id=f"lab12-{proposal_id}-decision")


@router.post("/lab12/proposals/{proposal_id}/rollback", response_model=APIEnvelope[dict[str, Any]])
async def rollback_governance_proposal(
    proposal_id: str,
    request: GovernanceRollbackRequest,
    user: AuthenticatedUser = Depends(require_roles("ADMIN")),
):
    try:
        proposal = governed_change_store.rollback(proposal_id, user.user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return APIEnvelope(success=True, data=proposal, trace_id=f"lab12-{proposal_id}-rollback")
