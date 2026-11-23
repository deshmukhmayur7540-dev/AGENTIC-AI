# Chapter 5: Governed Model Context Protocol (MCP) and Enterprise Connectors
Course: 26ECAC401: Agentic AI
Academic Year: 2026

## 5.1 Introduction to Model Context Protocol (MCP)
The Model Context Protocol (MCP) standardizes how AI agents securely interface with external heterogeneous data sources, databases, enterprise file stores, and academic registers. Rather than writing brittle custom API adapters for each data layer, MCP establishes a client-host-server paradigm with structured capabilities.

## 5.2 Four Canonical Academic Connectors
In CourseAgentAI, the governed connector mediates four specialized sources:
1. **notes_source:** Grounded lecture notes and slides across all course chapters.
2. **sqlite_source:** Relational ACID storage for student enrollments, assignment specifications, rubrics, and submission attempts.
3. **file_source:** Worklet manuals, build books, lab instructions, and attachments.
4. **academic_api_source:** University registrar simulation for course prerequisites and enrollment quotas.

## 5.3 Role-Based Access Control (RBAC) & Governance Gates
The connector enforces four distinct permission tiers:
- **STUDENT:** Read-only access to published course notes, open assignments, and own submissions. Mutation attempts strictly blocked with HTTP 403 / ACCESS_DENIED.
- **TA (Teaching Assistant):** Read access to all submissions, draft grading capability.
- **FACULTY:** Full CRUD rights on syllabus, assignments, rubrics, and grade publication.
- **ADMIN:** Unrestricted system administration, schema migrations, and audit configuration.
All requests across the connector generate immutable append-only audit traces recording client role, operation, resource path, and outcome.