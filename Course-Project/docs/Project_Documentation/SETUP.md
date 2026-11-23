# CourseAgentAI Setup

## Requirements

- Windows PowerShell, Python 3.12+, and pip.
- Node.js is optional (only needed for the JavaScript syntax check).
- Internet access is needed for dependency installation and initial local Lab 4 model provisioning. Inference is offline after the model is downloaded.

## Install

```powershell
cd C:\Users\Lenovo\Desktop\CourseAgentAI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

For regular application development, select a disposable database and separate materials directory **before** startup:

```powershell
$env:DATABASE_PATH = Join-Path $env:TEMP "CourseAgentAI-dev\courseagentai.sqlite3"
$env:COURSEAGENTAI_MATERIALS_ROOT = Join-Path $env:TEMP "CourseAgentAI-dev\materials"
$env:COURSEAGENTAI_HOST = "127.0.0.1"
$env:COURSEAGENTAI_PORT = "8000"
$env:COURSEAGENTAI_CORS_ORIGINS = "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe run.py
```

The application startup initializes its configured schema. Importing application or database modules does not initialize a database. Never run startup or `init_database()` with an unset/default path during tests or developer checks: the default points at the protected `app\data\governed_academic.db`.

## Accounts

No default account/password is seeded. Use the authorized operator bootstrap procedure described in the README to create accounts. Faculty accounts need explicit course scopes; Student accounts are bound to an existing student record. Do not put credentials in the repository or demo output.

## Tests and disposable storage

The pytest configuration sets `DATABASE_PATH` to a new temporary database before application imports and places course uploads under that temporary directory. Do not override that value to use governed records.

```powershell
$env:LAB4_RUN_MODEL_INTEGRATION_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q app tests scripts
node --check app\static\app.js
.\.venv\Scripts\python.exe -m pip check
```

## API schema

Open `http://127.0.0.1:8000/docs` after starting the disposable local instance. Authentication is cookie-based and mutating browser requests require the CSRF token. Use the [API reference](API_REFERENCE.md) for role boundaries and the new Lab 11/13/14 flows.
