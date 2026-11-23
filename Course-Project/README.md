# CourseAgentAI Course Project

CourseAgentAI is a local academic course operations system built for 26ECAC401: Agentic AI.

## Problem Statement

Academic course information is fragmented across notes, slides, submissions, grading records, and project trackers. Students need authenticated access to course materials and source-cited answers; faculty need structured review and approval workflows; administrators need governance and audit visibility. Repository submission validation is also needed before a submission record is accepted.

The project addresses these needs with a FastAPI application, a course-scoped SQLite database, deterministic agent and lab workflows, and a role-aware browser interface.

## Objectives

- Provide a hierarchical course knowledge repository
- Retrieve grounded course passages with source citations
- Record versioned assignment submissions
- Validate repository URL syntax and apply SSRF defenses
- Separate draft grading, faculty approval, and student publication
- Track course projects and weighted milestones
- Demonstrate bounded, auditable agentic AI workflows
- Preserve clear limitations for deterministic simulations and partial integrations

## Architecture

- **Presentation:** Responsive HTML, CSS, and JavaScript SPA
- **API:** FastAPI routes mounted in `app/main.py`
- **Services:** Authentication, submissions, similarity, projects, notifications, audit, and course materials
- **Labs:** Modular implementations in `app/labs/`
- **Data:** SQLite through `app/data/db.py`
- **Knowledge:** Recursive catalog, extractors, BM25 indexing, and optional local embeddings

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

## Agent Workflows

Labs 1–14 provide the progressive workflows:

1. Clarify-plan-revise planning
2. Typed tool-using agent and trace auditing
3. Reusable skills registry
4. Session memory and grounded retrieval
5. Governed source connector
6. Budgeted runtime and checkpointing
7. Specialist DAG with an approval gate
8. Parallel swarm and fan-in
9. Lexical evidence candidate retrieval
10. Bounded local cloud-operations simulation
11. Fixed application smoke checks and structured artifact builder
12. Persistent governance proposals, approval, and rollback
13. Theory, lab, and project specialist scaffolds
14. Persistent capstone run and versioned release workflow

## Roles

- **Student:** Read authorized course materials, submit a repository URL, view own submissions and published grades, and view published capstone releases with private details redacted.
- **Faculty:** Organize course materials, review course submissions, create draft grades, approve or publish results, prepare capstone runs, and publish or roll back releases.
- **Administrator:** Inspect authorized administration views and governance data. Administrators do not replace scoped course-faculty approval for capstone releases.

## Main Features

- Knowledge folders and source-cited search
- Assignment and rubric management
- GitHub URL normalization and anti-SSRF checks
- Submission attempt history and late-status metadata
- Lexical similarity candidate reports
- Draft rubric scoring with faculty publication gates
- Project milestones and activity
- Notifications and course announcements
- Session and role authorization
- SQLite audit and governance records

Similarity reports are candidate indicators for human review. Repository source code is not fetched or analyzed for similarity.

## Technology Stack

- Python 3.12
- FastAPI
- Pydantic
- SQLite
- Argon2
- Sentence Transformers and local BM25 retrieval
- HTML, CSS, and JavaScript
- Pytest and TestClient

## Installation

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For optional local embeddings:

```powershell
python -m pip install -r requirements-embeddings.txt
python scripts\download_lab4_embedding_model.py
```

## Environment Setup

Copy `.env.example` to `.env` and change only values required for the local environment.

Important defaults:

- `COURSEAGENTAI_HOST=127.0.0.1`
- `COURSEAGENTAI_PORT=8000`
- `DATABASE_PATH=app/data/governed_academic.db`
- `KNOWLEDGE_ROOT=knowledge`
- `COURSEAGENTAI_CORS_ORIGINS` must match the exact browser origin

Never place credentials or production database paths in the committed environment template.

## Safe Database Setup

The application initializes its configured SQLite database at startup. Use a disposable database for tests, demonstrations, migrations, and account provisioning:

```powershell
$env:DATABASE_PATH = (Join-Path $env:TEMP 'CourseAgentAI-demo.db')
$env:COURSEAGENTAI_CORS_ORIGINS = 'http://127.0.0.1:8000'
python run.py
```

Do not run setup or tests against `app/data/governed_academic.db`.

## Safe Administrator Provisioning

Set credentials only through process environment variables and initialize them in a disposable database:

```powershell
$env:DATABASE_PATH = (Join-Path $env:TEMP 'CourseAgentAI-demo.db')
$env:COURSEAGENTAI_INIT_EMAIL = 'operator@example.invalid'
$env:COURSEAGENTAI_INIT_PASSWORD = 'Use-A-Strong-Unique-Password'
$env:COURSEAGENTAI_INIT_ROLE = 'ADMIN'
$env:COURSEAGENTAI_INIT_USER_ID = 'operator-admin'
$env:COURSEAGENTAI_INIT_DISPLAY_NAME = 'Course Administrator'
python -m scripts.initialize_auth_user
```

The password must not be committed or shared in screenshots.

## Start

```powershell
python run.py
```

Open:

- Application: `http://127.0.0.1:8000/`
- API documentation: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/health`

## API and Testing

The complete route catalog is available from `/docs` and in [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

```powershell
python -m pytest -q
python -m compileall -q app tests scripts
node --check app\static\app.js
python -m pip check
```

The test suite overrides database paths with disposable SQLite databases.

## Limitations

- Labs 9 and 13 return lexical evidence candidates and scaffolds; they do not prove semantic entailment or replace faculty judgment.
- Lab 10 is a local cloud-operations simulation.
- Lab 11 runs fixed application smoke checks and creates a structured artifact; it does not generate arbitrary source code.
- Several lab histories remain process-local unless documented otherwise.
- GitHub validation checks URL safety and reachability; it does not establish authorship or analyze repository source code.
- External institutional identity, LMS, cloud providers, and faculty acceptance are not represented as live integrations.
