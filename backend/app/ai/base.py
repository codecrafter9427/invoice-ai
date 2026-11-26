"""AIProvider interface — typed stubs for Invoice AI features."""

from abc import ABC, abstractmethod

from app.core.config import get_settings
from app.schemas.common import AIRequest, AIResponse


class AIProvider(ABC):
    """Swappable AI backend. Never mutates invoices/payments without confirmation."""

    @abstractmethod
    async def invoice_extract(self, request: AIRequest) -> AIResponse:
        """Extract header/line items from OCR text — stub only; no real OCR."""
        ...

    @abstractmethod
    async def invoice_anomalies(self, request: AIRequest) -> AIResponse:
        """Invoice Anomaly Radar — explainable review signals, never fraud verdicts."""
        ...

    @abstractmethod
    async def category_suggestion(self, request: AIRequest) -> AIResponse:
        """Suggest accounting category; user must confirm."""
        ...


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider.lower() == "ollama":
        from app.ai.ollama import OllamaAIProvider

        return OllamaAIProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
    from app.ai.demo import DemoAIProvider

    return DemoAIProvider()
