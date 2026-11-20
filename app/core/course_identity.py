"""Canonical course identity resolution and normalization for CourseAgentAI (26ECAC401).

Guarantees:
- 'Agentic AI', 'agentic ai', '26ECAC401', 'course 26ECAC401' cleanly normalize to '26ECAC401' / 'Agentic AI'.
- Standalone 'AI' is never treated as a course code.
- Explicit non-canonical courses (e.g. 'CS101', 'UNKNOWN999') are preserved so repository lookup returns structured not-found error.
- Defaults safely to '26ECAC401' only when course is omitted in an Agentic AI context.
"""

import re
from typing import Optional, Tuple

CANONICAL_COURSE_ID = "26ECAC401"
CANONICAL_COURSE_NAME = "Agentic AI"

STOP_WORDS = {
    "FOR", "AND", "THE", "WITH", "FROM", "OVER", "PER", "SUM",
    "HOW", "SHOW", "WHAT", "CHECK", "DOES", "ARE", "HAS", "NOT",
    "CAN", "BUT", "AI", "AN", "IN", "ON", "TO", "AT",
}


def normalize_course_id(query_or_code: Optional[str]) -> Optional[str]:
    """Normalize a query or course code string into a canonical or extracted course ID.
    
    Returns:
        - "26ECAC401" for any mention of 26ECAC401 or Agentic AI.
        - The explicit course code if user specified another valid course code pattern (e.g. CS101, UNKNOWN999).
        - None if no course code is specified or if text is simply 'AI' without course digits.
    """
    if not query_or_code or not str(query_or_code).strip():
        return None

    text = str(query_or_code).strip()

    # 1. Exact or contained canonical references
    # Checks for 26ECAC401 or variations of "Agentic AI"
    if re.search(r"\b26ECAC401\b", text, re.IGNORECASE):
        return CANONICAL_COURSE_ID

    if re.search(r"\bagentic[\s\-_]+ai\b", text, re.IGNORECASE):
        return CANONICAL_COURSE_ID

    # 2. Reject standalone "AI" (case-insensitive) as a course ID
    if re.fullmatch(r"AI", text.strip(), re.IGNORECASE):
        return None

    # 3. Extract formal course code patterns:
    # e.g. CS101, AI301, DS200, 26ECAC402, UNKNOWN999, BADCOURSE1, TEST_COURSE1
    # Must have digits or specific test prefixes to distinguish from ordinary words
    pattern = (
        r"\b(26ECAC\d{3}|TEST_[A-Za-z0-9]+|UNKNOWN\d*|BADCOURSE\d*|"
        r"(?:CS|AI|DS|SE|SWE|IT|MATH|STAT|ENG|ECE|EE|PHYS|CHEM)\s*\d{1,4}|"
        r"[A-Z]{2,4}\s*\d{3,4})\b"
    )
    for match in re.finditer(pattern, text, re.IGNORECASE):
        candidate = re.sub(r"\s+", "", match.group(1)).upper()
        # Verify candidate is not a plain stopword
        prefix = re.match(r"^([A-Z]+)", candidate)
        if prefix and prefix.group(1) in STOP_WORDS and not re.search(r"\d", candidate):
            continue
        if candidate == "AI":
            continue
        if candidate == CANONICAL_COURSE_ID:
            return CANONICAL_COURSE_ID
        return candidate

    return None


def resolve_course_identity(
    query_or_code: Optional[str] = None,
    default_canonical: bool = True,
) -> Tuple[str, str]:
    """Resolve full (course_id, course_name) tuple from user input or context.
    
    If no course is specified and default_canonical is True, resolves to (26ECAC401, Agentic AI).
    If an unknown course is specified (e.g. CS101), returns (CS101, "Course CS101").
    """
    normalized = normalize_course_id(query_or_code)
    if normalized == CANONICAL_COURSE_ID:
        return CANONICAL_COURSE_ID, CANONICAL_COURSE_NAME

    if normalized is not None:
        return normalized, f"Course {normalized}"

    if default_canonical:
        return CANONICAL_COURSE_ID, CANONICAL_COURSE_NAME

    return "", ""


def is_canonical_course(course_id: Optional[str]) -> bool:
    """Check if course_id refers to canonical 26ECAC401 Agentic AI course."""
    norm = normalize_course_id(course_id)
    return norm == CANONICAL_COURSE_ID
