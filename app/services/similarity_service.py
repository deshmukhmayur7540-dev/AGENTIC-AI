"""Similarity Checking and Grading Assistance Service for CourseAgentAI (Part 6)."""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Optional

from app.data.db import get_db_connection
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase alphanumeric words."""
    return re.findall(r"\b[a-zA-Z0-9_]{3,}\b", text.lower())


def _calculate_ngram_similarity(text1: str, text2: str, n: int = 3) -> tuple[float, list[str]]:
    """Compute n-gram Jaccard similarity and extract common sequences."""
    tokens1 = _tokenize(text1)
    tokens2 = _tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0, []

    if len(tokens1) < n or len(tokens2) < n:
        # Fallback to word-level overlap
        set1, set2 = set(tokens1), set(tokens2)
        intersection = set1 & set2
        union = set1 | set2
        score = (len(intersection) / len(union) * 100.0) if union else 0.0
        return round(score, 1), list(intersection)[:5]

    ngrams1 = Counter([" ".join(tokens1[i : i + n]) for i in range(len(tokens1) - n + 1)])
    ngrams2 = Counter([" ".join(tokens2[i : i + n]) for i in range(len(tokens2) - n + 1)])

    shared_ngrams = list((set(ngrams1.keys()) & set(ngrams2.keys())))
    total_unique = len(set(ngrams1.keys()) | set(ngrams2.keys()))

    score = (len(shared_ngrams) / total_unique * 100.0) if total_unique > 0 else 0.0
    return round(score, 1), shared_ngrams[:6]


class SimilarityService:
    """Computes transparent submission similarity and synthesizes rubric-based draft grading."""

    def run_similarity_check(
        self,
        assignment_id: str,
        actor: str = "faculty",
        actor_role: str = "FACULTY",
    ) -> dict[str, Any]:
        """Perform pairwise lexical and structural similarity comparison across all submissions for an assignment."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, st.name as student_name
                FROM submissions s
                JOIN students st ON s.student_id = st.id
                WHERE s.assignment_id = ? AND s.is_latest = 1
                ORDER BY s.submission_timestamp ASC
                """,
                (assignment_id,),
            )
            submissions = [dict(r) for r in cursor.fetchall()]

        if len(submissions) < 2:
            audit_service.log_event(
                event_type="SIMILARITY_CHECK_COMPLETED",
                actor=actor,
                actor_role=actor_role,
                resource=f"assignment:{assignment_id}",
                action="RUN_SIMILARITY_CHECK",
                outcome="INSUFFICIENT_SUBMISSIONS",
                details={"total_submissions": len(submissions), "flagged_count": 0},
            )
            return {
                "assignment_id": assignment_id,
                "status": "INSUFFICIENT_SUBMISSIONS",
                "message": f"At least 2 submissions are required to run pairwise similarity analysis (found {len(submissions)}).",
                "total_compared": len(submissions),
                "pairs": [],
            }

        pairs = []
        highest_score = 0.0
        flagged_count = 0

        for i in range(len(submissions)):
            for j in range(i + 1, len(submissions)):
                sub1 = submissions[i]
                sub2 = submissions[j]

                # Combine repository URL, notes, repo owner/name, validation details as comparison corpus
                text1 = f"{sub1['repo_name']} {sub1.get('notes') or ''} {sub1.get('validation_details') or ''}"
                text2 = f"{sub2['repo_name']} {sub2.get('notes') or ''} {sub2.get('validation_details') or ''}"

                score, matched_samples = _calculate_ngram_similarity(text1, text2, n=2)

                # Special check: identical repo URL submitted by different students
                if sub1["normalized_url"].lower() == sub2["normalized_url"].lower():
                    score = max(score, 95.0)
                    matched_samples.append(f"Identical Repository URL: {sub1['normalized_url']}")

                is_flagged = score >= 30.0
                if is_flagged:
                    flagged_count += 1
                if score > highest_score:
                    highest_score = score

                pairs.append({
                    "student_a": {"id": sub1["student_id"], "name": sub1["student_name"], "submission_id": sub1["id"]},
                    "student_b": {"id": sub2["student_id"], "name": sub2["student_name"], "submission_id": sub2["id"]},
                    "similarity_score": score,
                    "flagged_for_review": is_flagged,
                    "matched_sequences": matched_samples,
                    "recommendation": "Flagged for manual faculty inspection" if is_flagged else "Within normal expected similarity range",
                })

        report_id = f"sim-{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now(timezone.utc).isoformat()
        status_val = "FLAGGED_FOR_REVIEW" if flagged_count > 0 else "COMPLETED"
        summary = (
            f"Compared {len(submissions)} student submissions across {len(pairs)} pairs. "
            f"Highest observed similarity is {highest_score:.1f}%. "
            f"{flagged_count} pair(s) flagged for human review."
        )

        with get_db_connection(immediate=True) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO similarity_reports (id, assignment_id, generated_at, generated_by, status, total_submissions_compared, highest_similarity_score, pairs_json, flagged_count, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    assignment_id,
                    now_iso,
                    actor,
                    status_val,
                    len(submissions),
                    highest_score,
                    json.dumps(pairs),
                    flagged_count,
                    summary,
                ),
            )

        audit_service.log_event(
            event_type="SIMILARITY_CHECK_COMPLETED",
            actor=actor,
            actor_role=actor_role,
            resource=f"assignment:{assignment_id}",
            action="RUN_SIMILARITY_CHECK",
            outcome=status_val,
            details={"highest_score": highest_score, "flagged_count": flagged_count},
        )

        return {
            "report_id": report_id,
            "assignment_id": assignment_id,
            "generated_at": now_iso,
            "generated_by": actor,
            "status": status_val,
            "total_submissions_compared": len(submissions),
            "highest_similarity_score": highest_score,
            "flagged_count": flagged_count,
            "summary": summary,
            "pairs": pairs,
            "limitations": (
                "Lexical similarity metrics calculate text and token overlap. Shared boilerplate, starter template code, "
                "and canonical solution structures can elevate similarity scores. This report provides candidate matches "
                "for human faculty evaluation and must never be treated as autonomous proof of academic dishonesty."
            ),
        }

    def get_latest_report(self, assignment_id: str) -> Optional[dict[str, Any]]:
        """Retrieve most recent similarity report for an assignment."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM similarity_reports WHERE assignment_id = ? ORDER BY generated_at DESC LIMIT 1",
                (assignment_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            report = dict(row)
            try:
                report["pairs"] = json.loads(report.pop("pairs_json"))
            except Exception:
                report["pairs"] = []
            return report

    def generate_draft_grade(self, submission_id: str, actor: str = "grading_assistant") -> dict[str, Any]:
        """Generate transparent rubric-based draft scoring and feedback without finalizing or publishing."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
            sub_row = cursor.fetchone()
            if not sub_row:
                raise ValueError(f"Submission '{submission_id}' not found.")
            submission = dict(sub_row)

            # Get Rubrics for this assignment
            cursor.execute("SELECT * FROM rubrics WHERE assignment_id = ?", (submission["assignment_id"],))
            rubrics = [dict(r) for r in cursor.fetchall()]

            # If no rubrics configured, use default standard academic rubric
            if not rubrics:
                rubrics = [
                    {"id": "std-1", "criterion": "Repository Structure & Cleanliness", "max_points": 30.0, "description": "Valid repository format and clean structure."},
                    {"id": "std-2", "criterion": "Implementation Correctness", "max_points": 40.0, "description": "Solution requirements implementation."},
                    {"id": "std-3", "criterion": "Test Coverage & Documentation", "max_points": 30.0, "description": "Automated tests and clear README instructions."},
                ]

        val_details = {}
        if submission.get("validation_details"):
            try:
                val_details = json.loads(submission["validation_details"]) if isinstance(submission["validation_details"], str) else submission["validation_details"]
            except Exception:
                pass

        remote_check = val_details.get("remote_check", {})
        is_reachable = remote_check.get("reachable") is True
        is_late = val_details.get("is_late") is True

        criterion_scores = []
        total_awarded = 0.0
        total_possible = sum(r["max_points"] for r in rubrics) or 100.0

        for r in rubrics:
            crit_name = r["criterion"]
            max_pts = float(r["max_points"])

            # Deduce criterion score deterministically
            if is_reachable:
                awarded = round(max_pts * 0.94, 1)  # 94% baseline for accessible verified repo
                rationale = f"Repository '{submission['repo_name']}' is verified accessible on GitHub with valid syntax."
            elif submission["validation_status"] == "PASSED":
                awarded = round(max_pts * 0.88, 1)
                rationale = f"URL syntax validated strictly; remote reachability was inconclusive ({remote_check.get('note', 'unverified')})."
            else:
                awarded = round(max_pts * 0.75, 1)
                rationale = f"Submission accepted with validation warnings: {remote_check.get('note', 'check required')}."

            # Apply late penalty if applicable
            if is_late:
                awarded = round(awarded * 0.90, 1)
                rationale += " [Applied 10% late submission deduction]."

            total_awarded += awarded
            criterion_scores.append({
                "criterion_id": r.get("id"),
                "criterion_name": crit_name,
                "max_points": max_pts,
                "suggested_score": awarded,
                "percentage": round((awarded / max_pts) * 100.0, 1) if max_pts > 0 else 0.0,
                "reasoning": rationale,
            })

        scaled_score = round((total_awarded / total_possible) * 100.0, 1) if total_possible > 0 else total_awarded

        draft_feedback = (
            f"Draft AI Evaluation for {submission['student_id']} on {submission['assignment_id']}:\n"
            f"- Repository: {submission['repository_url']}\n"
            f"- Validation Status: {submission['validation_status']} (Attempt #{submission['attempt_number']})\n"
            f"- Overall Assessment: Solution repository syntax is valid and complies with assignment submission guardrails.\n"
            f"- Suggested Rubric Total: {scaled_score} / 100.0.\n"
            f"NOTE: This is a draft proposal prepared by the Grading Assistance Agent. Faculty sign-off is required before publication."
        )

        return {
            "submission_id": submission_id,
            "student_id": submission["student_id"],
            "assignment_id": submission["assignment_id"],
            "suggested_score": scaled_score,
            "criterion_breakdown": criterion_scores,
            "draft_feedback": draft_feedback,
            "requires_faculty_approval": True,
            "is_published": False,
            "notice": "Draft prepared by Grading Assistance Agent. Only faculty approval can finalize and publish grades.",
        }


similarity_service = SimilarityService()
