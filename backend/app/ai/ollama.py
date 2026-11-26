"""Optional Ollama adapter — falls back to DemoAIProvider when unreachable.

Not required for demos. No paid LLM/OCR APIs.
"""

from __future__ import annotations

import httpx

from app.ai.base import AIProvider
from app.ai.demo import DemoAIProvider
from app.schemas.common import AIRequest, AIResponse, AISource


class OllamaAIProvider(AIProvider):
    """
    Local open-model adapter.

    Milestone 3 keeps generation optional: ping Ollama, then enrich DemoAIProvider
    explanations. Structured extract / anomaly *rules* stay deterministic via demo.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._fallback = DemoAIProvider()

    async def _ping(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def _explain(self, prompt: str) -> str | None:
        """Best-effort local generate; None on any failure."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                if response.status_code != 200:
                    return None
                data = response.json()
                text = data.get("response")
                return text.strip() if isinstance(text, str) and text.strip() else None
        except Exception:
            return None

    async def invoice_extract(self, request: AIRequest) -> AIResponse:
        base = await self._fallback.invoice_extract(request)
        available = await self._ping()
        result = dict(base.result)
        result["provider"] = "ollama" if available else "demo-fallback"
        result["ollama_model"] = self.model
        explanation = base.explanation
        if available:
            explanation += (
                f" Ollama ({self.model}) is reachable; structured fields still come "
                "from deterministic demo extract (no paid OCR)."
            )
        else:
            explanation += " Ollama unreachable; used DemoAIProvider fallback."
        return AIResponse(
            result=result,
            explanation=explanation,
            sources=list(base.sources)
            + [
                AISource(
                    type="provider",
                    id="ollama",
                    label=f"{self.model} @ {self.base_url}",
                )
            ],
            requires_confirmation=True,
        )

    async def invoice_anomalies(self, request: AIRequest) -> AIResponse:
        # Rules stay deterministic; Ollama may only explain
        base = await self._fallback.invoice_anomalies(request)
        available = await self._ping()
        result = dict(base.result)
        result["provider"] = "ollama" if available else "demo-fallback"
        result["never_declares_fraud"] = True
        result["fraud_verdict"] = None

        explanation = base.explanation
        if available:
            codes = [s.get("code") for s in result.get("signals", []) if isinstance(s, dict)]
            llm = await self._explain(
                "In one short paragraph, explain these invoice review signals "
                f"for a finance reviewer. Do NOT say fraud. Signals: {codes}"
            )
            if llm and "fraud" not in llm.lower():
                explanation = (
                    f"{base.explanation} Local model note: {llm}"
                )
            else:
                explanation += (
                    f" Ollama ({self.model}) available for optional explain; "
                    "rules remain authoritative; never declares fraud."
                )
        else:
            explanation += " Ollama unreachable; DemoAIProvider explained rules."

        # Strip any accidental fraud verdicts from nested signals
        signals = []
        for s in result.get("signals", []):
            if isinstance(s, dict):
                item = dict(s)
                item["is_fraud_verdict"] = False
                signals.append(item)
        result["signals"] = signals

        return AIResponse(
            result=result,
            explanation=explanation,
            sources=list(base.sources)
            + [
                AISource(
                    type="provider",
                    id="ollama",
                    label=f"{self.model} @ {self.base_url}",
                )
            ],
            requires_confirmation=False,
        )

    async def category_suggestion(self, request: AIRequest) -> AIResponse:
        base = await self._fallback.category_suggestion(request)
        available = await self._ping()
        result = dict(base.result)
        result["provider"] = "ollama" if available else "demo-fallback"
        explanation = base.explanation
        if not available:
            explanation += " Ollama unreachable; used DemoAIProvider fallback."
        else:
            explanation += f" Ollama ({self.model}) optional; confirmation still required."
        return AIResponse(
            result=result,
            explanation=explanation,
            sources=list(base.sources),
            requires_confirmation=True,
        )
