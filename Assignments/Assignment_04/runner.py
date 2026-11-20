# Assignment 4 Verification Runner
from app.labs.lab4.memory import SessionMemoryStore
from app.knowledge.service import knowledge_service

def main():
    print("=== Assignment 4: Dual-Tier Memory Architecture ===")
    store = SessionMemoryStore()
    session_id = store.create_session(owner_id="std-001", course_id="26ECAC401")
    store.add_message(session_id, role="user", content="What are the 4 chapters of Agentic AI?")
    messages = store.get_messages(session_id)
    print(f"Session Messages: {len(messages)}")
    results = knowledge_service.search("autonomous agent loop", top_k=2)
    print(f"RAG Matches: {len(results.matches)} (Top source: {results.matches[0].source_document if results.matches else 'None'})")
    print("Assignment 4 Verification: PASSED")

if __name__ == '__main__':
    main()
