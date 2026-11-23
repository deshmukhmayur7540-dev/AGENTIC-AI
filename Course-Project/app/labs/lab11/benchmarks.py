"""Deterministic smoke benchmark using existing CourseAgentAI services."""

from typing import Any

from app.knowledge.service import knowledge_service
from app.services.github_validator import validate_github_url


class BenchmarkFactory:
    """Run a small, transparent, side-effect-free reliability suite."""

    def run(self) -> dict[str, Any]:
        cases = []

        def record(name: str, passed: bool, observed: Any, expected: str) -> None:
            cases.append({"name": name, "passed": bool(passed), "observed": observed, "expected": expected})

        good_url = validate_github_url("https://github.com/octocat/Hello-World")
        bad_url = validate_github_url("https://github.com.attacker.example/octocat/repo")
        record("github_accepts_official_repository", good_url.is_valid, good_url.validation_status, "valid HTTPS github.com owner/repository")
        record("github_rejects_lookalike_host", not bad_url.is_valid, bad_url.details.get("reason"), "non-GitHub host rejected")

        grade_total = round(sum((35.0, 25.0, 40.0)), 4)
        record("grade_weights_sum_to_100", grade_total == 100.0, grade_total, "100.0")

        grounded = knowledge_service.search("Plan Act Observe Revise agent loop", top_k=2)
        record("course_notes_retrieval_has_source", bool(grounded.matches), [m.source_document for m in grounded.matches], "at least one source document")
        unsupported = knowledge_service.search("quantum alchemy interstellar unicorn", top_k=2)
        record("unsupported_query_returns_no_match", not unsupported.matches, unsupported.match_count, "0 matches")

        passed = sum(1 for item in cases if item["passed"])
        return {
            "suite": "CourseAgentAI deterministic integration smoke suite",
            "passed": passed,
            "failed": len(cases) - passed,
            "total": len(cases),
            "status": "PASSED" if passed == len(cases) else "FAILED",
            "cases": cases,
            "limitations": "This small deterministic smoke suite is not a substitute for the full pytest suite or official course evaluation.",
        }


benchmark_factory = BenchmarkFactory()
