# CourseAgentAI API Reference

The running FastAPI OpenAPI schema at `/docs` is the authoritative complete route catalog. Routes require an authenticated server-side session unless explicitly documented otherwise. Mutating cookie-authenticated requests require a trusted `Origin` and matching CSRF cookie/header.

## New specialist and capstone APIs

| Method | Path | Access | Behavior |
|---|---|---|---|
| `GET` | `/api/lab13/specialists?course_id=26ECAC401` | Authenticated course member | List registered theory/lab/project profiles and their structural checks. |
| `POST` | `/api/lab13/specialists/run` | Authenticated course member | Run deterministic specialist scaffold retrieval. Body: `course_id`, `specialist_type` (`theory`, `lab`, `project`), `work_item`, optional `chapter`. Returns candidate source citations and check statuses. |
| `POST` | `/api/lab11/spec-build` | Scoped Faculty/Admin | Build a structured artifact from `course_id`, `specialist_type`, `requirement`, and optional `chapter`; run fixed structural/provenance checks. No supplied code or test code is executed. |
| `POST` | `/api/capstone/runs` | Scoped Faculty/Admin | Build/persist a course workspace snapshot. Body: `course_id`, `assignment_id`, `request`. Returns status, package, validation checks, and run ID. Failed validation is not approvable. |
| `GET` | `/api/capstone/runs/{run_id}` | Scoped Faculty/Admin | Read a draft run and validation details. Students are denied. |
| `GET` | `/api/capstone/runs/{run_id}/audit` | Scoped Faculty/Admin | Read persistent run, decision, release, and rollback audit events. |
| `POST` | `/api/capstone/runs/{run_id}/decision` | Scoped Faculty only | Body: `approved` and optional `comment`. Rejection is recorded; approval is allowed only after all hard checks pass and creates the next course release version. |
| `GET` | `/api/capstone/releases/current?course_id=26ECAC401` | Authenticated course member | Get active published release. Student responses redact individual submissions and scores and omit similarity pairs. Faculty/Admin responses include the internal package. |
| `POST` | `/api/capstone/releases/{release_id}/rollback` | Scoped Faculty only | Deactivate the current release and restore the preceding eligible version when available. |

## Capstone validation checks

The coordinator validates:

1. At least one cited source from the authorized course retrieval index.
2. At least one database-backed course-library material.
3. The selected in-course assignment has rubric criteria.
4. At least two latest submissions exist and a similarity comparison is generated/persisted.
5. Late flags agree with submission workflow status when recorded.
6. No recorded review grade exceeds the assignment maximum.
7. Any published grade has approval and publisher attribution.
8. At least two project milestones exist for the course.

Passing these checks produces `READY_FOR_FACULTY_APPROVAL`; it does not assert repository correctness, entailment, or autonomous grading. A failed gate returns `VALIDATION_FAILED` and cannot be approved.

## Existing API groups

- `/api/auth/*`: login, session identity, logout, CSRF/session lifecycle.
- `/api/course-materials/*`: categories, nested folders, uploads, metadata, preview, downloads, replacement and deletion.
- `/api/assignments`, `/api/submissions/*`: assignment/rubric lookup, student submission, faculty review, approval, publication, and audit.
- `/api/projects/*`: projects, course/student-scoped dashboards, milestone updates and comments.
- `/api/similarity/*`: faculty/admin similarity and grading assistance.
- `/api/lab4/*` and `/api/knowledge/*`: owner/course-scoped memory and source-cited course retrieval.
- `/api/lab5/*` through `/api/lab12/*`: individual lab operations; consult the OpenAPI schema and [official compliance audit](../OFFICIAL_14_LAB_COMPLIANCE_AUDIT.md) for current scope and limitations.
