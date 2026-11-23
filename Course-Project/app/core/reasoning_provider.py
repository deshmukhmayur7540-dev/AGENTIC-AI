"""Reasoning provider module supporting deterministic reasoning and live LLMs."""

import os
from typing import Any, Optional
from config import settings


class ReasoningProvider:
    """Reasoning engine producing coherent, structured educational plans and gap analyses."""

    def __init__(self):
        self.provider = settings.llm_provider
        self.gemini_key = settings.gemini_api_key
        self.openai_key = settings.openai_api_key

    def is_live_llm_enabled(self) -> bool:
        """Check if an external LLM API key is configured."""
        return bool((self.provider == "gemini" and self.gemini_key) or (self.provider == "openai" and self.openai_key))


reasoning_provider = ReasoningProvider()
