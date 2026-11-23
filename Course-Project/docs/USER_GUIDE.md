# CourseAgentAI User Guide

## Sign in and navigate

Sign in with an operator-provisioned account. The application uses server-issued sessions; a role selector or request header is not a way to acquire privileges. Tabs expose the labs, materials, submissions, projects, and announcements available in the interface. Backend authorization remains authoritative.

## Student

- Browse course materials, folders, descriptions, and source files; search and download are read-only.
- Use the assignment list and submit a GitHub repository URL only for the signed-in student identity. A syntactically valid URL does not establish repository accessibility or authorship.
- View only the student's own submission/review details and published grades.
- Update project milestones only for projects to which the student belongs.
- View a published capstone release using Lab 14; individual submissions, scores, review records, and similarity pairs are redacted from student release reads.

## Faculty

- Create and organize course folders and upload supported materials. Uploads are course-scoped and validated by content as well as file extension.
- Review course-scoped submissions; draft grading, approval, and publication are distinct transitions.
- Use Lab 13 to produce a theory, lab, or project scaffold. The result is deterministic, cites candidate local source passages, and requires faculty review. The service does not invent an official rubric.
- Use Lab 11's bounded structured-artifact builder to produce a cited output and run fixed structural checks. It does not execute generated code or student code.
- Use Lab 14 to prepare a persistent course workspace run. Provide an assignment ID and request; the coordinator snapshots available materials/evidence, assignment/rubric, submissions, similarity candidate report, and course project checkpoint state. The validation report identifies exactly which prerequisites are missing.
- A run must pass all gates before its course Faculty may approve/publish it. Approval creates a versioned release; a Faculty rollback deactivates the current release and restores the preceding non-rolled-back version where available.

## Administrator

Administrators can use administrative APIs and inspect course snapshots but are not accepted as the course-Faculty approver for Lab 14 releases. They cannot act as a substitute for a scoped Faculty review.

## Interpreting agent and evidence outputs

- Labs 9 and 13 citations are retrieval provenance, not proof of entailment.
- Similarity reports compare stored metadata/text and may flag candidates for manual inspection. Repository source code is not fetched or analyzed.
- Lab 10 Cloud Operations is a local simulation; no cloud provider is contacted.
- Lab 11 produces a structured artifact, not general source code.
- Lab 14 release approval is not automated grading. The workspace records existing review states and never publishes an individual grade by itself.

## Failure handling

If Lab 14 validation fails, do not approve the run. Review its failed checks and address the missing real course data (such as indexed course evidence, uploaded materials, rubric, milestones, multiple submissions for similarity analysis, or inconsistent recorded workflow state), then create a new run. Every run and release is stored in the configured SQLite database; database backups and operational access remain the operator's responsibility.
