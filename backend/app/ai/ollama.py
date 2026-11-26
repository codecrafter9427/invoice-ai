"""Ollama adapter stub — optional local open model; not required for demos."""

from app.schemas.common import AIRequest, AIResponse, AISource


class OllamaAIProvider:
    """
    Placeholder for local Ollama calls.

    Does not call the network in this scaffold. Falls back to labeled stubs so
    the API remains usable before Milestone 3 wiring.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def invoice_extract(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            result={
                "provider": "ollama-stub",
                "base_url": self.base_url,
                "model": self.model,
                "status": "not_wired",
                "header": None,
                "line_items": [],
            },
            explanation=(
                "Ollama adapter stub. Milestone 3 will POST typed prompts to "
                f"{self.base_url}/api/generate with model={self.model}. "
                "No paid OCR/LLM APIs."
            ),
            sources=[],
            requires_confirmation=True,
        )

    async def invoice_anomalies(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            result={
                "provider": "ollama-stub",
                "model": self.model,
                "signals": [],
                "note": "Rules engine + Ollama explanation not wired yet",
            },
            explanation=(
                "Anomaly Radar will stay rules-first; Ollama may explain signals only."
            ),
            sources=[
                AISource(
                    type="provider",
                    id="ollama",
                    label=f"{self.model} @ {self.base_url}",
                )
            ],
            requires_confirmation=False,
        )

    async def category_suggestion(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            result={
                "provider": "ollama-stub",
                "model": self.model,
                "suggested_category": None,
            },
            explanation="Ollama category suggestion not wired; confirmation required.",
            sources=[],
            requires_confirmation=True,
        )
