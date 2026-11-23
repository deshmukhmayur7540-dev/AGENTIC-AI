"""Evidence candidate retrieval and claim evaluation for Lab 9 (Bug 2 repair).

Distinguishes lexical retrieval matches from verified semantic entailment.
"""

from typing import Any
from app.knowledge.service import knowledge_service


class EvidenceVerifier:
    """Return bounded lexical evidence candidates without asserting entailment."""

    def verify_claims(self, claims: list[str], chapter: int | None = None) -> dict[str, Any]:
        results = []
        evidence_table = []
        for claim in claims:
            result = knowledge_service.search(
                query=claim,
                course_id="26ECAC401",
                chapter=chapter,
                top_k=3,
            )
            candidates = [
                {
                    "evidence_id": match.chunk_id,
                    "chapter": match.chapter,
                    "topic": match.topic,
                    "source_document": match.source_document,
                    "source_location": match.source_location,
                    "score": round(match.score, 3),
                    "excerpt": match.matched_text[:1000],
                }
                for match in result.matches
            ]

            if not candidates:
                verdict = "NO_MATCHING_EVIDENCE_FOUND"
                eval_detail = "INSUFFICIENT_EVIDENCE"
                reasoning = "No lexical candidate was found in the selected course-material scope."
                requires_review = False
            else:
                verdict = "CANDIDATE_EVIDENCE_FOUND"
                eval_detail = "NOT_ASSESSED"
                reasoning = (
                    "Candidates are ranked by lexical BM25 relevance. Whether they support or contradict this claim "
                    "has not been assessed and requires human or separately validated entailment review."
                )
                requires_review = True

            claim_result = {
                "claim": claim,
                "status": verdict,
                "evidence_evaluation": eval_detail,
                "entailment_reasoning": reasoning,
                "requires_human_entailment_review": requires_review,
                "evidence_candidates": candidates,
                "verdict_category": eval_detail,
                "retrieval_method": "BM25",
            }
            results.append(claim_result)
            evidence_table.append({
                "claim": claim,
                "candidate_count": len(candidates),
                "status": verdict,
                "candidates": candidates,
            })

        return {
            "course_id": "26ECAC401",
            "chapter_filter": chapter,
            "retrieval_method": "BM25",
            "claims": results,
            "evidence_table": evidence_table,
            "limitation": (
                "BM25 scores are lexical relevance scores, not probabilities or entailment decisions. "
                "Candidate retrieval does not determine support, contradiction, or truth; human review is required."
            ),
            "disclaimer": (
                "Citations identify indexed source documents and locations. This endpoint does not claim that "
                "candidate text supports or contradicts a claim."
            ),
        }


evidence_verifier = EvidenceVerifier()
