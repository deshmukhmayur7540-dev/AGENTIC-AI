# CourseAgentAI: Source Code Architecture & Structure
**Course:** `26ECAC401: Agentic AI`  
**Artifact Name:** `CourseAgentAI â€” Course Project, Notes & Assignment Organizer`  

---

## 1. Directory Organization

The CourseAgentAI codebase is structured as a modular, enterprise-grade Python application:

```text
CourseAgentAI/
â”œâ”€â”€ app/                           # Core Application Package
â”‚   â”œâ”€â”€ api/                       # FastAPI REST API Routes
â”‚   â”‚   â”œâ”€â”€ routes_auth.py         # Authentication & Session Management
â”‚   â”‚   â”œâ”€â”€ routes_knowledge.py    # Document Management System (DMS) & Search
â”‚   â”‚   â”œâ”€â”€ routes_submissions.py  # Student Submissions & Faculty Grading
â”‚   â”‚   â”œâ”€â”€ routes_similarity.py   # Similarity Review & Draft Rubric Scoring
â”‚   â”‚   â”œâ”€â”€ routes_projects.py     # Course Project Milestone Tracker
â”‚   â”‚   â”œâ”€â”€ routes_system.py       # System Status & Unified Audit Log
â”‚   â”‚   â”œâ”€â”€ routes_lab1.py .. lab8 # Laboratory Modules 1 to 8 Routes
â”‚   â”‚   â”œâ”€â”€ routes_labs9_12.py     # Laboratory Modules 9 to 12 Routes
â”‚   â”‚   â””â”€â”€ routes_capstone.py     # Lab 14 Capstone Coordinator Routes
â”‚   â”œâ”€â”€ core/                      # Coordinator & Domain Business Logic
â”‚   â”‚   â”œâ”€â”€ coordinator.py         # Central Course Coordinator Agent
â”‚   â”‚   â”œâ”€â”€ security.py            # Password Hashing & Token Verification
â”‚   â”‚   â””â”€â”€ exceptions.py          # Domain-Specific Error Types
â”‚   â”œâ”€â”€ data/                      # Database & Relational Persistence
â”‚   â”‚   â”œâ”€â”€ db.py                  # SQLite Connection & Schema Migrations
â”‚   â”‚   â”œâ”€â”€ repository.py          # Data Access Layer & Scoped Queries
â”‚   â”‚   â””â”€â”€ governed_academic.db   # Governed Relational SQLite Database
â”‚   â”œâ”€â”€ knowledge/                 # Document Ingestion & RAG Subsystem
â”‚   â”‚   â”œâ”€â”€ catalog.py             # 12-Folder Hierarchical DMS Engine
â”‚   â”‚   â”œâ”€â”€ extractors.py          # PDF, DOCX, PPTX, CSV, TXT Extractors
â”‚   â”‚   â”œâ”€â”€ indexer.py             # Deterministic BM25 Inverted Index
â”‚   â”‚   â””â”€â”€ service.py             # Grounded Retrieval & Citation Formatter
â”‚   â”œâ”€â”€ labs/                      # Laboratory Modules Implementations
â”‚   â”‚   â”œâ”€â”€ lab1/                  # Clarify-Plan-Revise Syllabus Planner
â”‚   â”‚   â”œâ”€â”€ lab2/                  # ReAct Agent with 9 Typed Tools
â”‚   â”‚   â”œâ”€â”€ lab3/                  # Modular Skills Registry & Routing
â”‚   â”‚   â”œâ”€â”€ lab4/                  # Dual-Tier Memory & Local Embeddings
â”‚   â”‚   â”œâ”€â”€ lab5/                  # MCP-Style Governed Academic Connector
â”‚   â”‚   â”œâ”€â”€ lab6/                  # Resilient Runtime with Checkpointing
â”‚   â”‚   â”œâ”€â”€ lab7/                  # 10-Node Specialist Workflow Graph DAG
â”‚   â”‚   â”œâ”€â”€ lab8/                  # Asynchronous Parallel Worker Swarm
â”‚   â”‚   â”œâ”€â”€ lab9/                  # Deep Research Claim Grounding & Citations
â”‚   â”‚   â”œâ”€â”€ lab10/                 # Cloud Operations Diagnostic Agent
â”‚   â”‚   â”œâ”€â”€ lab11/                 # Agentic SDLC Code Synthesis Factory
â”‚   â”‚   â””â”€â”€ lab12/                 # Enterprise Safety, Governance & Rollback
â”‚   â”œâ”€â”€ models/                    # Pydantic v2 Data Models & Envelopes
â”‚   â”œâ”€â”€ services/                  # Shared Business Logic & Services
â”‚   â”‚   â”œâ”€â”€ audit_service.py       # Central Unified SQLite Audit Logger
â”‚   â”‚   â”œâ”€â”€ submission_service.py  # Submissions & Faculty Review Workflow
â”‚   â”‚   â”œâ”€â”€ similarity_service.py  # Pairwise Similarity & Draft Grading
â”‚   â”‚   â”œâ”€â”€ project_service.py     # Course Project Milestone Management
â”‚   â”‚   â””â”€â”€ github_validator.py    # Anti-SSRF GitHub Repository Validator
â”‚   â””â”€â”€ static/                    # Frontend Web Assets (HTML, CSS, JS)
â”‚       â”œâ”€â”€ index.html             # Single-Page Application (SPA)
â”‚       â”œâ”€â”€ style.css              # Apple Cupertino Design System
â”‚       â””â”€â”€ app.js                 # Modern Frontend Reactive Logic
â”œâ”€â”€ Assignments/                   # All 12 Laboratory Assignments Packages
â”‚   â”œâ”€â”€ Assignment-01/ .. 12/      # Assignment Specifications, Run & Test
â”œâ”€â”€ Course Project/                # Formal Submission Documentation
â”‚   â”œâ”€â”€ Problem_Statement/         # Original Problem Statement Document
â”‚   â”œâ”€â”€ Final_Report/              # Comprehensive Academic Project Report
â”‚   â””â”€â”€ Project_Documentation/     # Architecture, Setup, API & User Guides
â”œâ”€â”€ knowledge/                     # 12 Structured Course Document Folders
â”‚   â”œâ”€â”€ 01_Notes/ .. 12_Other/     # Course Textbooks, Slides, Labs & Manuals
â”œâ”€â”€ tests/                         # Automated Pytest Regression Suites
â”œâ”€â”€ config.py                      # Application Configuration & Environment
â”œâ”€â”€ run.py                         # Server Entry Point
â””â”€â”€ requirements.txt               # Production Python Dependencies
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
