"""Lab 4: Memory & Retrieval package."""

from app.labs.lab4.agent import lab4_agent, MemoryAndRetrievalAgent
from app.labs.lab4.knowledge_store import long_term_store, LongTermKnowledgeStore
from app.labs.lab4.session_store import short_term_store, ShortTermSessionStore
from app.core.registry import lab_registry

lab_registry.register_agent("lab4", lab4_agent)

__all__ = [
    "lab4_agent",
    "MemoryAndRetrievalAgent",
    "long_term_store",
    "LongTermKnowledgeStore",
    "short_term_store",
    "ShortTermSessionStore",
]
