"""API tests for the available project-derived Lab 9-12 tools."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.labs.lab10.cloud_ops import CloudOperationsAgent
from app.labs.lab12.governance import GovernedChangeStore, governed_change_store
from tests.conftest import AuthTestClient


@pytest.fixture
def client():
    return AuthTestClient(app)


def test_lab9_returns_cited_candidates_and_discloses_limit(client):
    response = client.post(
        "/api/lab9/grounding/verify",
        json={"claims": ["Plan Act Observe Revise agent loop"], "chapter": 1},
    )
    assert response.status_code == 200
    claim = response.json()["data"]["claims"][0]
    assert claim["status"] == "CANDIDATE_EVIDENCE_FOUND"
    assert claim["requires_human_entailment_review"] is True
    assert claim["evidence_candidates"][0]["source_document"]
    assert claim["evidence_evaluation"] == "NOT_ASSESSED"
    assert claim["evidence_candidates"][0]["evidence_id"]
    assert response.json()["data"]["retrieval_method"] == "BM25"
    assert response.json()["data"]["evidence_table"][0]["candidate_count"] > 0
    assert "not probabilities or entailment decisions" in response.json()["data"]["limitation"]


def test_lab9_never_infers_support_or_contradiction_from_claim_keywords(client):
    response = client.post(
        "/api/lab9/grounding/verify",
        json={"claims": ["Tools always guarantee 100% accurate decisions in every environment."]},
    )
    assert response.status_code == 200
    claim = response.json()["data"]["claims"][0]
    assert claim["evidence_candidates"]
    assert claim["evidence_evaluation"] == "NOT_ASSESSED"
    assert claim["requires_human_entailment_review"] is True
    assert "has not been assessed" in claim["entailment_reasoning"]


def test_lab9_reports_insufficient_evidence_without_inventing_candidates(client):
    response = client.post(
        "/api/lab9/grounding/verify",
        json={"claims": ["qzxv blergh flarn certainty"]},
    )
    assert response.status_code == 200
    claim = response.json()["data"]["claims"][0]
    assert claim["status"] == "NO_MATCHING_EVIDENCE_FOUND"
    assert claim["evidence_evaluation"] == "INSUFFICIENT_EVIDENCE"
    assert claim["evidence_candidates"] == []
    assert claim["requires_human_entailment_review"] is False


def test_lab9_validation_bounds_claims_and_chapters(client):
    assert client.post("/api/lab9/grounding/verify", json={"claims": []}).status_code == 422
    assert client.post("/api/lab9/grounding/verify", json={"claims": ["claim"], "chapter": 5}).status_code == 422
    assert client.post("/api/lab9/grounding/verify", json={"claims": ["   "]}).status_code == 422
    assert client.post("/api/lab9/grounding/verify", json={"claims": ["x" * 1001]}).status_code == 422


def test_lab10_proposes_bounded_repair_without_applying_it(client):
    assert client.post(
        "/api/lab10/validation/repair",
        json={"weights": [{"name": "A", "weight": 100}]},
    ).status_code == 403
    response = client.post(
        "/api/lab10/validation/repair",
        json={"weights": [{"name": "A", "weight": 40}, {"name": "B", "weight": 30}, {"name": "C", "weight": 20}]},
        headers={"X-User-Role": "FACULTY"},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "REPAIR_PROPOSED"
    assert result["total"] == 90
    assert result["repair_proposal"]["proposed_total"] == 100
    assert result["repair_proposal"]["requires_human_approval"] is True
    assert result["repair_proposal"]["applied_automatically"] is False


def test_lab10_simulates_targeted_repair_and_escalates_after_bounded_failures(client):
    weights = [
        {"name": "Assignments", "weight": 40},
        {"name": "Labs", "weight": 30},
        {"name": "Final project", "weight": 20},
    ]
    headers = {"X-User-Role": "FACULTY"}
    repaired = client.post(
        "/api/lab10/validation/repair",
        json={
            "weights": weights,
            "apply_simulated_repair": True,
            "repair_index": 2,
            "max_attempts": 2,
        },
        headers=headers,
    )
    assert repaired.status_code == 200
    data = repaired.json()["data"]
    assert data["status"] == "REPAIRED_PREVIEW"
    assert data["simulation_only"] is True
    assert data["persisted"] is False
    assert data["course_records_changed"] is False
    assert data["validation_passed"] is True
    assert data["original_weights"] == weights
    assert data["repaired_preview"] == [
        {"name": "Assignments", "weight": 40},
        {"name": "Labs", "weight": 30},
        {"name": "Final project", "weight": 30.0},
    ]

    exhausted = client.post(
        "/api/lab10/validation/repair",
        json={
            "weights": weights,
            "apply_simulated_repair": True,
            "repair_index": 2,
            "max_attempts": 2,
            "inject_repair_failure": True,
        },
        headers=headers,
    )
    assert exhausted.status_code == 200
    data = exhausted.json()["data"]
    assert data["status"] == "RETRY_EXHAUSTED"
    assert data["validation_passed"] is False
    assert data["escalation_required"] is True
    assert len(data["attempts"]) == 3
    assert data["repaired_preview"] is None

    unrepairable = client.post(
        "/api/lab10/validation/repair",
        json={
            "weights": [
                {"name": "Fixed", "weight": 100},
                {"name": "Selected", "weight": 5},
                {"name": "Other", "weight": 5},
            ],
            "apply_simulated_repair": True,
            "repair_index": 1,
        },
        headers=headers,
    )
    assert unrepairable.status_code == 200
    assert unrepairable.json()["data"]["status"] == "ESCALATED_UNREPAIRABLE"
    assert unrepairable.json()["data"]["repaired_preview"] is None

    invalid = client.post(
        "/api/lab10/validation/repair",
        json={"weights": weights, "apply_simulated_repair": True, "repair_index": 9},
        headers=headers,
    )
    assert invalid.status_code == 422


def test_lab10_cloud_ops_diagnoses_failed_deployment_and_bounds_repair_rollback(client):
    endpoint = "/api/lab10/cloud-ops"
    assert client.get(f"{endpoint}/diagnosis").status_code == 403
    headers = {"X-User-Role": "FACULTY"}
    diagnosis = client.get(f"{endpoint}/diagnosis", headers=headers)
    assert diagnosis.status_code == 200
    detail = diagnosis.json()["data"]
    assert detail["simulation_only"] is True
    assert detail["provider_contacted"] is False
    assert detail["deployment_status"] == "FAILED"
    assert detail["diagnosis"]["diagnostics"][0]["component_id"] == "worker-swarm"
    assert client.post(
        f"{endpoint}/repair",
        json={"approved": False},
        headers={**headers, "X-CSRF-Token": "invalid"},
    ).status_code == 403

    rejected = client.post(f"{endpoint}/repair", json={"approved": False}, headers=headers)
    assert rejected.status_code == 200
    rejected_data = rejected.json()["data"]
    assert rejected_data["result"]["applied"] is False
    assert rejected_data["worker_status"] == "DEGRADED"
    assert rejected_data["worker_replicas"] == 4
    assert rejected_data["rollback_available"] is False

    repair = client.post(f"{endpoint}/repair", json={"approved": True}, headers=headers)
    assert repair.status_code == 200
    repaired = repair.json()["data"]
    assert repaired["simulation_only"] is True
    assert repaired["provider_contacted"] is False
    assert repaired["result"]["status"] == "REMEDIATION_APPLIED_SUCCESS"
    assert repaired["worker_status"] == "HEALTHY"
    assert repaired["worker_replicas"] == 5
    assert repaired["rollback_available"] is True
    remediation_id = repaired["proposal"]["remediation_id"]

    assert client.post(
        f"{endpoint}/rollback",
        json={"remediation_id": remediation_id},
        headers={"X-User-Role": "STUDENT"},
    ).status_code == 403
    rollback = client.post(
        f"{endpoint}/rollback",
        json={"remediation_id": remediation_id},
        headers=headers,
    )
    assert rollback.status_code == 200
    restored = rollback.json()["data"]
    assert restored["simulation_only"] is True
    assert restored["provider_contacted"] is False
    assert restored["result"]["status"] == "ROLLED_BACK"
    assert restored["worker_status"] == "DEGRADED"
    assert restored["worker_replicas"] == 4
    assert client.post(
        f"{endpoint}/rollback",
        json={"remediation_id": remediation_id},
        headers=headers,
    ).status_code == 409


def test_lab10_simulator_returns_copies_and_records_each_local_decision():
    agent = CloudOperationsAgent()
    status_snapshot = agent.get_cluster_status()
    status_snapshot["cluster"]["components"]["worker-swarm"]["status"] = "HEALTHY"
    assert agent.diagnose_infrastructure()["overall_health"] == "DEGRADED"

    diagnosis = agent.diagnose_infrastructure(target_component="worker-swarm")
    assert diagnosis["issues_detected"] == 1
    with pytest.raises(ValueError, match="Unknown simulated component"):
        agent.diagnose_infrastructure(target_component="unknown")

    rejected_plan = agent.propose_remediation(actor="faculty-1")
    rejected = agent.apply_remediation(rejected_plan["remediation_id"], False, actor="faculty-1")
    assert rejected["applied"] is False

    active_plan = agent.propose_remediation(actor="faculty-2")
    agent.apply_remediation(active_plan["remediation_id"], True, actor="faculty-2")
    agent.rollback_remediation(active_plan["remediation_id"], actor="faculty-2")
    history = agent.get_cluster_status()["cluster"]["remediation_history"]
    assert [(event["action"], event["actor"]) for event in history] == [
        ("PROPOSE_REMEDIATION", "faculty-1"),
        ("REJECT_REMEDIATION", "faculty-1"),
        ("PROPOSE_REMEDIATION", "faculty-2"),
        ("APPLY_REMEDIATION", "faculty-2"),
        ("ROLLBACK_REMEDIATION", "faculty-2"),
    ]


def test_lab10_concurrent_duplicate_remediation_application_is_serialized():
    from concurrent.futures import ThreadPoolExecutor

    agent = CloudOperationsAgent()
    plan = agent.propose_remediation()

    def apply():
        try:
            return agent.apply_remediation(plan["remediation_id"], True)
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: apply(), range(2)))

    assert sum(result is not None for result in results) == 1
    assert agent.get_cluster_status()["cluster"]["components"]["worker-swarm"]["status"] == "HEALTHY"


def test_lab11_benchmark_factory_runs_existing_services(client):
    response = client.post("/api/lab11/benchmarks/run")
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["total"] == 5
    assert result["passed"] == 5
    assert result["failed"] == 0


@pytest.mark.parametrize("specialist_type", ["theory", "lab", "project"])
def test_lab13_specialist_returns_checkable_scaffold_with_source_evidence(client, specialist_type):
    response = client.post(
        "/api/lab13/specialists/run",
        json={
            "course_id": "26ECAC401",
            "specialist_type": specialist_type,
            "work_item": "Plan Act Observe Revise agent loop",
        },
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "READY_FOR_FACULTY_REVIEW"
    assert result["generation_mode"] == "deterministic_evidence_cited_scaffold"
    assert result["evidence"][0]["source_document"]
    assert result["evidence"][0]["citation"]
    assert all(check["passed"] for check in result["checks"])
    assert any("Faculty" in limitation for limitation in result["limitations"])
    if specialist_type == "theory":
        assert result["output"]["faculty_confirmed_objectives"] == []
    if specialist_type == "project":
        assert result["output"]["faculty_review_required"] is True


def test_lab13_registry_is_course_scoped_and_lab11_spec_builder_does_not_execute_code(client):
    denied = client.post(
        "/api/lab11/spec-build",
        json={
            "specialist_type": "lab",
            "requirement": "Plan Act Observe Revise agent loop",
        },
    )
    assert denied.status_code == 403
    profiles = client.get(
        "/api/lab13/specialists",
        headers={"X-User-Role": "FACULTY"},
    )
    assert profiles.status_code == 200
    assert {item["specialist_type"] for item in profiles.json()["data"]} == {
        "theory",
        "lab",
        "project",
    }

    response = client.post(
        "/api/lab11/spec-build",
        json={
            "course_id": "26ECAC401",
            "specialist_type": "lab",
            "requirement": "Plan Act Observe Revise agent loop",
        },
        headers={"X-User-Role": "FACULTY"},
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "CHECKS_PASSED"
    assert result["artifact_released"] is False
    assert "was executed" in result["execution_boundary"]
    assert all(test["passed"] for test in result["acceptance_tests"])


def test_lab12_requires_admin_session_and_rejects_without_mutation(client):
    payload = {
        "resource_id": "test-reject-resource",
        "current_value": {"mode": "draft"},
        "proposed_value": {"mode": "published"},
        "summary": "Test reject path",
    }
    assert client.post("/api/lab12/proposals", json=payload).status_code == 403
    response = client.post("/api/lab12/proposals", json=payload, headers={"X-User-Role": "ADMIN"})
    assert response.status_code == 200
    proposal_id = response.json()["data"]["proposal_id"]
    decision = client.post(
        f"/api/lab12/proposals/{proposal_id}/decision",
        json={"approved": False, "actor": "faculty-test"},
        headers={"X-User-Role": "ADMIN"},
    )
    assert decision.status_code == 200
    assert decision.json()["data"]["status"] == "REJECTED"
    assert governed_change_store.get_resource("test-reject-resource") is None
    assert client.get("/api/lab12/proposals", headers={"X-User-Role": "STUDENT"}).status_code == 403


def test_lab12_approval_and_single_rollback(client):
    payload = {
        "resource_id": "test-rollback-resource",
        "current_value": {"version": 1},
        "proposed_value": {"version": 2},
        "summary": "Test approval and rollback",
    }
    create = client.post("/api/lab12/proposals", json=payload, headers={"X-User-Role": "ADMIN"})
    assert create.status_code == 200
    proposal_id = create.json()["data"]["proposal_id"]
    decision = client.post(
        f"/api/lab12/proposals/{proposal_id}/decision",
        json={"approved": True, "actor": "admin-test"},
        headers={"X-User-Role": "ADMIN"},
    )
    assert decision.json()["data"]["status"] == "APPROVED_APPLIED"
    assert governed_change_store.get_resource("test-rollback-resource") == {"version": 2}
    rollback = client.post(
        f"/api/lab12/proposals/{proposal_id}/rollback",
        json={"actor": "admin-test"},
        headers={"X-User-Role": "ADMIN"},
    )
    assert rollback.json()["data"]["status"] == "ROLLED_BACK"
    assert governed_change_store.get_resource("test-rollback-resource") == {"version": 1}
    assert client.post(
        f"/api/lab12/proposals/{proposal_id}/rollback",
        json={"actor": "admin-test"},
        headers={"X-User-Role": "ADMIN"},
    ).status_code == 409


def test_lab12_rejects_stale_proposal_and_protects_newer_resource_value(client):
    headers = {"X-User-Role": "ADMIN"}
    base = {
        "resource_id": "test-stale-resource",
        "current_value": {"version": 1},
        "summary": "Concurrent proposal",
    }
    first = client.post(
        "/api/lab12/proposals",
        json={**base, "proposed_value": {"version": 2}},
        headers=headers,
    ).json()["data"]["proposal_id"]
    stale = client.post(
        "/api/lab12/proposals",
        json={**base, "proposed_value": {"version": 3}},
        headers=headers,
    ).json()["data"]["proposal_id"]
    approve = client.post(
        f"/api/lab12/proposals/{first}/decision",
        json={"approved": True, "actor": "faculty-test"},
        headers=headers,
    )
    assert approve.status_code == 200
    stale_decision = client.post(
        f"/api/lab12/proposals/{stale}/decision",
        json={"approved": True, "actor": "faculty-test"},
        headers=headers,
    )
    assert stale_decision.status_code == 409
    assert governed_change_store.get_resource("test-stale-resource") == {"version": 2}
    rollback = client.post(
        f"/api/lab12/proposals/{first}/rollback",
        json={"actor": "faculty-test"},
        headers=headers,
    )
    assert rollback.status_code == 200
    assert governed_change_store.get_resource("test-stale-resource") == {"version": 1}


def test_lab12_proposals_and_audit_persist_across_store_instances(tmp_path):
    database_path = tmp_path / "governance.sqlite3"
    store = GovernedChangeStore(database_path)

    approved = store.propose(
        "persistent-approved-resource",
        {"version": 1},
        {"version": 2},
        "Persist approved change",
    )
    store.decide(approved["proposal_id"], True, "faculty-demo", "Approved after review")
    store.rollback(approved["proposal_id"], "faculty-demo")

    rejected = store.propose(
        "persistent-rejected-resource",
        {"mode": "draft"},
        {"mode": "published"},
        "Persist rejected change",
    )
    store.decide(rejected["proposal_id"], False, "faculty-reviewer", "Insufficient evidence")

    restarted_store = GovernedChangeStore(database_path)
    persisted_approved = restarted_store.get(approved["proposal_id"])
    assert persisted_approved is not None
    assert persisted_approved["status"] == "ROLLED_BACK"
    assert persisted_approved["rolled_back_by"] == "faculty-demo"
    assert persisted_approved["decision_comment"] == "Approved after review"
    assert restarted_store.get_resource("persistent-approved-resource") == {"version": 1}

    persisted_rejected = restarted_store.get(rejected["proposal_id"])
    assert persisted_rejected is not None
    assert persisted_rejected["status"] == "REJECTED"
    assert persisted_rejected["decision_comment"] == "Insufficient evidence"
    assert restarted_store.get_resource("persistent-rejected-resource") is None

    events = restarted_store.get_audit_history(approved["proposal_id"])
    assert [event["action"] for event in events] == ["PROPOSED", "APPROVED", "ROLLED_BACK"]
    assert events[1]["actor"] == "faculty-demo"
    assert events[1]["comment"] == "Approved after review"
    assert events[2]["actor"] == "faculty-demo"
    assert events[2]["from_status"] == "APPROVED_APPLIED"
    assert events[2]["to_status"] == "ROLLED_BACK"

    rejected_events = restarted_store.get_audit_history(rejected["proposal_id"])
    assert [event["action"] for event in rejected_events] == ["PROPOSED", "REJECTED"]
    assert rejected_events[1]["actor"] == "faculty-reviewer"
    assert rejected_events[1]["comment"] == "Insufficient evidence"


def test_lab12_audit_endpoint_requires_admin_and_returns_real_events(client):
    headers = {"X-User-Role": "ADMIN"}
    proposal = client.post(
        "/api/lab12/proposals",
        json={
            "resource_id": "audit-endpoint-resource",
            "current_value": {"mode": "draft"},
            "proposed_value": {"mode": "published"},
            "summary": "Verify audit endpoint",
        },
        headers=headers,
    ).json()["data"]
    decision = client.post(
        f"/api/lab12/proposals/{proposal['proposal_id']}/decision",
        json={"approved": False, "actor": "reviewer-1", "comment": "Keep in draft"},
        headers=headers,
    )
    assert decision.status_code == 200

    audit = client.get(
        f"/api/lab12/proposals/{proposal['proposal_id']}/audit",
        headers=headers,
    )
    assert audit.status_code == 200
    assert [event["action"] for event in audit.json()["data"]] == ["PROPOSED", "REJECTED"]
    assert audit.json()["data"][1]["actor"] == "test-admin"
    assert audit.json()["data"][1]["comment"] == "Keep in draft"
    assert client.get(
        f"/api/lab12/proposals/{proposal['proposal_id']}/audit",
        headers={"X-User-Role": "STUDENT"},
    ).status_code == 403
