"""AI provider factory — DemoAIProvider by default; optional Ollama stub."""

from app.ai.base import AIProvider, get_ai_provider

__all__ = ["AIProvider", "get_ai_provider"]
