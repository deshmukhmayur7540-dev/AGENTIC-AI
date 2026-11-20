"""Deterministic validation and non-applied repair proposals for Lab 10."""

from typing import Any


class SelfHealingValidator:
    """Find grade-weight total defects and propose a bounded, reviewable repair."""

    def validate_grade_weights(self, weights: list[dict[str, Any]], target: float = 100.0) -> dict[str, Any]:
        total = round(sum(item["weight"] for item in weights), 4)
        if abs(total - target) <= 0.0001:
            return {
                "status": "VALID",
                "total": total,
                "target": target,
                "repair_proposal": None,
                "attempts": [{"attempt": 1, "total": total, "status": "VALID"}],
            }

        proposal = [dict(item) for item in weights]
        delta = round(target - total, 4)
        if proposal:
            index = max(range(len(proposal)), key=lambda i: proposal[i]["weight"])
            adjusted = round(proposal[index]["weight"] + delta, 4)
            if 0 <= adjusted <= 100:
                proposal[index]["weight"] = adjusted
            else:
                proposal = []

        if proposal:
            proposed_total = round(sum(item["weight"] for item in proposal), 4)
            repair = {
                "weights": proposal,
                "proposed_total": proposed_total,
                "changed_item": proposal[index]["name"],
                "requires_human_approval": True,
                "applied_automatically": False,
            }
            status = "REPAIR_PROPOSED"
        else:
            repair = None
            status = "UNREPAIRABLE_WITHIN_BOUNDS"

        return {
            "status": status,
            "total": total,
            "target": target,
            "repair_proposal": repair,
            "attempts": [
                {"attempt": 1, "total": total, "status": "CONSTRAINT_VIOLATION"},
                {"attempt": 2, "total": repair["proposed_total"] if repair else None, "status": status},
            ],
        }

    def simulate_bounded_repair(
        self,
        weights: list[dict[str, Any]],
        target: float,
        repair_index: int,
        max_attempts: int,
        inject_repair_failure: bool = False,
    ) -> dict[str, Any]:
        """Repair only a caller-selected draft item; never writes course records."""
        if not weights:
            raise ValueError("At least one grade-weight item is required.")
        if not 0 <= repair_index < len(weights):
            raise ValueError("repair_index must identify an item in the submitted draft.")
        if not 1 <= max_attempts <= 3:
            raise ValueError("max_attempts must be between 1 and 3.")
        if not 0 < target <= 100:
            raise ValueError("target must be greater than zero and at most 100.")
        original = [dict(item) for item in weights]
        preview = [dict(item) for item in weights]
        total = round(sum(item["weight"] for item in preview), 4)
        attempts = [{
            "attempt": 0,
            "phase": "VALIDATE",
            "total": total,
            "status": "VALID" if abs(total - target) <= 0.0001 else "CONSTRAINT_VIOLATION",
        }]

        if abs(total - target) <= 0.0001:
            return self._simulation_result("ALREADY_VALID", original, None, attempts, False)

        for attempt in range(1, max_attempts + 1):
            if inject_repair_failure:
                attempts.append({
                    "attempt": attempt,
                    "phase": "REPAIR",
                    "total": total,
                    "status": "INJECTED_REPAIR_FAILURE",
                })
                continue

            delta = round(target - total, 4)
            adjusted = round(preview[repair_index]["weight"] + delta, 4)
            if not 0 <= adjusted <= 100:
                attempts.append({
                    "attempt": attempt,
                    "phase": "REPAIR",
                    "total": total,
                    "status": "REPAIR_OUT_OF_BOUNDS",
                })
                return self._simulation_result(
                    "ESCALATED_UNREPAIRABLE",
                    original,
                    None,
                    attempts,
                    False,
                )

            preview[repair_index]["weight"] = adjusted
            total = round(sum(item["weight"] for item in preview), 4)
            valid = abs(total - target) <= 0.0001
            attempts.append({
                "attempt": attempt,
                "phase": "VALIDATE",
                "total": total,
                "status": "VALID" if valid else "CONSTRAINT_VIOLATION",
            })
            if valid:
                return self._simulation_result(
                    "REPAIRED_PREVIEW",
                    original,
                    preview,
                    attempts,
                    True,
                )

        return self._simulation_result("RETRY_EXHAUSTED", original, None, attempts, False)

    @staticmethod
    def _simulation_result(
        status: str,
        original: list[dict[str, Any]],
        repaired_preview: list[dict[str, Any]] | None,
        attempts: list[dict[str, Any]],
        validation_passed: bool,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "simulation_only": True,
            "persisted": False,
            "course_records_changed": False,
            "validation_passed": validation_passed,
            "original_weights": original,
            "repaired_preview": repaired_preview,
            "attempts": attempts,
            "escalation_required": status in {"RETRY_EXHAUSTED", "ESCALATED_UNREPAIRABLE"},
        }


self_healing_validator = SelfHealingValidator()
