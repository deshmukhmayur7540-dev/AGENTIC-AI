# CourseAgentAI: Source Code Architecture & Structure
**Course:** `26ECAC401: Agentic AI`  
**Artifact Name:** `CourseAgentAI — Course Project, Notes & Assignment Organizer`  

---

## 1. Directory Organization

The CourseAgentAI codebase is structured as a modular, enterprise-grade Python application:

```text
CourseAgentAI/
├── app/                           # Core Application Package
│   ├── api/                       # FastAPI REST API Routes
│   │   ├── routes_auth.py         # Authentication & Session Management
│   │   ├── routes_knowledge.py    # Document Management System (DMS) & Search
│   │   ├── routes_submissions.py  # Student Submissions & Faculty Grading
│   │   ├── routes_similarity.py   # Similarity Review & Draft Rubric Scoring
│   │   ├── routes_projects.py     # Course Project Milestone Tracker
│   │   ├── routes_system.py       # System Status & Unified Audit Log
│   │   ├── routes_lab1.py .. lab8 # Laboratory Modules 1 to 8 Routes
│   │   ├── routes_labs9_12.py     # Laboratory Modules 9 to 12 Routes
│   │   └── routes_capstone.py     # Lab 14 Capstone Coordinator Routes
│   ├── core/                      # Coordinator & Domain Business Logic
│   │   ├── coordinator.py         # Central Course Coordinator Agent
│   │   ├── security.py            # Password Hashing & Token Verification
│   │   └── exceptions.py          # Domain-Specific Error Types
│   ├── data/                      # Database & Relational Persistence
│   │   ├── db.py                  # SQLite Connection & Schema Migrations
│   │   ├── repository.py          # Data Access Layer & Scoped Queries
│   │   └── governed_academic.db   # Governed Relational SQLite Database
│   ├── knowledge/                 # Document Ingestion & RAG Subsystem
│   │   ├── catalog.py             # 12-Folder Hierarchical DMS Engine
│   │   ├── extractors.py          # PDF, DOCX, PPTX, CSV, TXT Extractors
│   │   ├── indexer.py             # Deterministic BM25 Inverted Index
│   │   └── service.py             # Grounded Retrieval & Citation Formatter
│   ├── labs/                      # Laboratory Modules Implementations
│   │   ├── lab1/                  # Clarify-Plan-Revise Syllabus Planner
│   │   ├── lab2/                  # ReAct Agent with 9 Typed Tools
│   │   ├── lab3/                  # Modular Skills Registry & Routing
│   │   ├── lab4/                  # Dual-Tier Memory & Local Embeddings
│   │   ├── lab5/                  # MCP-Style Governed Academic Connector
│   │   ├── lab6/                  # Resilient Runtime with Checkpointing
│   │   ├── lab7/                  # 10-Node Specialist Workflow Graph DAG
│   │   ├── lab8/                  # Asynchronous Parallel Worker Swarm
│   │   ├── lab9/                  # Deep Research Claim Grounding & Citations
│   │   ├── lab10/                 # Cloud Operations Diagnostic Agent
│   │   ├── lab11/                 # Agentic SDLC Code Synthesis Factory
│   │   └── lab12/                 # Enterprise Safety, Governance & Rollback
│   ├── models/                    # Pydantic v2 Data Models & Envelopes
│   ├── services/                  # Shared Business Logic & Services
│   │   ├── audit_service.py       # Central Unified SQLite Audit Logger
│   │   ├── submission_service.py  # Submissions & Faculty Review Workflow
│   │   ├── similarity_service.py  # Pairwise Similarity & Draft Grading
│   │   ├── project_service.py     # Course Project Milestone Management
│   │   └── github_validator.py    # Anti-SSRF GitHub Repository Validator
│   └── static/                    # Frontend Web Assets (HTML, CSS, JS)
│       ├── index.html             # Single-Page Application (SPA)
│       ├── style.css              # Apple Cupertino Design System
│       └── app.js                 # Modern Frontend Reactive Logic
├── Assignments/                   # All 12 Laboratory Assignments Packages
│   ├── Assignment_01/ .. 12/      # Assignment Specifications, Run & Test
├── Course Project/                # Formal Submission Documentation
│   ├── Problem_Statement/         # Original Problem Statement Document
│   ├── Final_Report/              # Comprehensive Academic Project Report
│   └── Project_Documentation/     # Architecture, Setup, API & User Guides
├── knowledge/                     # 12 Structured Course Document Folders
│   ├── 01_Notes/ .. 12_Other/     # Course Textbooks, Slides, Labs & Manuals
├── tests/                         # Automated Pytest Regression Suites
├── config.py                      # Application Configuration & Environment
├── run.py                         # Server Entry Point
└── requirements.txt               # Production Python Dependencies
```

---

## 2. Running the Application

### 2.1 Starting the Server
```powershell
# Start CourseAgentAI with hot-reloading
python run.py
```
The server will start at: `http://127.0.0.1:8000`

### 2.2 Accessing the Web Application
Open your web browser and navigate to:
- **Application Portal:** `http://127.0.0.1:8000/`
- **Interactive OpenAPI Docs:** `http://127.0.0.1:8000/docs`

---

## 3. Running Test Suites
```powershell
# Run the complete test suite (338+ passing tests)
python -m pytest tests/ -q
```
