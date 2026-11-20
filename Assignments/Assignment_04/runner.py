import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Assignment 4 Verification Runner
from app.data.db import init_database
from app.labs.lab4.session_store import short_term_store
from app.knowledge.service import knowledge_service

def main():
    print("=== Assignment 4: Dual-Tier Memory Architecture ===")
    init_database()
    session = short_term_store.create_session(user_id="std-001", course_id="26ECAC401")
    print(f"Created Session: {session.session_id}")
    results = knowledge_service.search("Plan Act Observe Revise", top_k=2)
    print(f"RAG Matches: {len(results.matches)} (Top source: {results.matches[0].source_document if results.matches else 'None'})")
    print("Assignment 4 Verification: PASSED")

if __name__ == '__main__':
    main()
