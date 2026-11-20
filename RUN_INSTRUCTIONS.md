# CourseAgentAI — Local Run and Verification

**Course:** 26ECAC401: Agentic AI  
**Runtime:** Python 3.12+, FastAPI, SQLite. Detailed official handouts for Labs 9–12 were not found; see the README for the available tools and their exact scope.

## Setup and startup

From the project root, install dependencies:

`pip install -r requirements.txt`

Canonical startup command:

`python run.py`

Default local URL: `http://127.0.0.1:8000/`  
API docs: `http://127.0.0.1:8000/docs`  
Liveness only: `http://127.0.0.1:8000/api/health`

If port 8000 is occupied, stop a process you own or set `COURSEAGENTAI_PORT` to an available port before launching. When changing the port, set `COURSEAGENTAI_CORS_ORIGINS` to the exact browser origin (for example `http://127.0.0.1:8037`); browser login and unsafe requests reject untrusted or missing Origins. The database defaults to `app/data/governed_academic.db`; override via `DATABASE_PATH`. The notes root defaults to `knowledge/`; override via `KNOWLEDGE_ROOT`. Back up SQLite before migrations or demo/testing writes.

## Tests

`python -m pytest -q`

`node --check app/static/app.js`

See [TEST_RESULTS.md](TEST_RESULTS.md) for the exact results executed in this audit, including browser evidence, warning, and limitations. A passing test suite does not establish that the available Lab 9–12 tools meet every official course requirement or that the demo is production-secure.

## Knowledge notes

The Knowledge catalog recursively lists allowed originals. Default RAG discovery recursively processes extractable DOCX, PPTX, TXT, Markdown, PDF, and CSV files in chapter 1–4 paths under `knowledge/agentic_ai`; unsupported or unextractable files and other knowledge subtrees are skipped. Listing/downloading a file does not prove that it is indexed. The index is in-memory lexical BM25, not persistent vector/hybrid search; see [PROJECT_COMPLETION_AUDIT.md](PROJECT_COMPLETION_AUDIT.md).

## Authentication and authorization

Protected API operations derive user identity and role from a verified database-backed session; `X-Student-Id` and `X-User-Role` are not identity credentials. Faculty grading is faculty-only and course-scoped; governance administration is separate. Unsafe requests require an exact configured trusted Origin, and cookie-authenticated mutations require the CSRF cookie/header pair. These controls are covered by automated tests but do not replace institutional identity lifecycle controls or a production security review. No demo credentials are seeded; use only accounts provisioned by an authorized operator. Submitted repositories are not executed.

Lab 12 governance data persists in configured SQLite, while several lab run/session histories remain process-local. Back up the database before intentional application writes or schema changes.

Automated tests override `DATABASE_PATH` with a disposable database and disable GitHub reachability requests. Do not run the test suite against a production or user database.

## Troubleshooting

- Backend unavailable: start from the repository root and verify the port is free.
- Missing static UI: verify `app/static/index.html`, `app/static/app.js`, and `app/static/style.css` exist.
- Missing downloadable notes: verify the configured root and file extensions; unreadable/missing files are skipped or return 404.
- Knowledge search has no results: verify the source is an extractable DOCX, PPTX, TXT, Markdown, PDF, or CSV file in a chapter 1–4 path under the default `knowledge/agentic_ai` root; a cataloged/downloadable file may not be indexed.
- Private GitHub repository: syntax validation does not prove public access; network/privacy issues may produce an unverified warning.
- Pytest deprecation warning: Starlette's TestClient integration with installed `httpx` is deprecated; this warning remains visible and is not suppressed.
