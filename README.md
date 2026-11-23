# CourseAgentAI

**Course:** Agentic AI (26ECAC401)  
**Institution:** KLE Technological University  
**Department:** CSE (AI)  
**Team:** TEAM-07

CourseAgentAI is an academic course operations platform that combines course knowledge management, assignment submissions and review, project milestone tracking, role-based access, and 14 progressive agentic AI laboratory workflows.

## Team Members

| Member | USN | Division |
|---|---|---|
| Mayur Deshmukh | 01FE23BCI034 | A |
| Shrivatsa R D | 01FE23BCI038 | A |
| Riya P | 01FE23BCI027 | A |
| Shakti I | 01FE23BCI011 | A |

## Main Features

- Hierarchical course knowledge catalog with PDF, DOCX, PPTX, TXT, Markdown, and CSV indexing
- Source-cited lexical retrieval and optional local embedding retrieval
- GitHub repository submission validation and versioned submission attempts
- Faculty review, rubric scoring, approval, publication, and audit trails
- Student, Faculty, and Administrator role boundaries
- Course project workspaces and weighted milestone tracking
- Labs 1–14, including planning, tools, skills, memory, connectors, runtime gates, graphs, swarms, research, governance, specialists, and capstone workflows

## Technology Stack

- Python 3.12
- FastAPI and Pydantic
- SQLite
- Argon2 password hashing
- Sentence Transformers for optional local embeddings
- HTML, CSS, and JavaScript
- Pytest

## Repository Structure

```text
AGENTIC-AI/
├── Assignments/       # 12 laboratory assignment packages
├── Course-Project/    # Application source, knowledge, tests, docs, and scripts
├── .gitignore
├── README.md
└── requirements.txt   # Convenience entry point for the application dependencies
```

Detailed application information is in [Course-Project/README.md](Course-Project/README.md).

## Installation

```powershell
cd Course-Project
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` only if you need to override a default.

## Start the Application

```powershell
cd Course-Project
python run.py
```

Open `http://127.0.0.1:8000/` and `http://127.0.0.1:8000/docs`.

## Testing

Run tests from the project directory:

```powershell
cd Course-Project
python -m pytest -q
python -m compileall -q app tests scripts
node --check app\static\app.js
python -m pip check
```

Tests use disposable SQLite databases and must not be pointed at governed or production databases.

## Submission Links

- [All 12 Assignments](Assignments/)
- [Course Project Application](Course-Project/)
- [Project Documentation](Course-Project/docs/)
- [Final Report](Course-Project/docs/Final_Report/CourseAgentAI_Final_Report.md)
- [Problem Statement](Course-Project/docs/Problem_Statement/Course_Project_Problem_Statement.md)
