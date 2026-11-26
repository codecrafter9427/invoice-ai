"""Deterministic DemoAIProvider — works without Ollama installed."""

from app.schemas.common import AIRequest, AIResponse, AISource


class DemoAIProvider:
    """Returns fixed, labeled stub payloads. No network calls. No real extraction."""

    async def invoice_extract(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            result={
                "provider": "demo",
                "status": "stub",
                "header": None,
                "line_items": [],
                "field_confidence": {},
                "note": "OCR/extraction not implemented in scaffold",
            },
            explanation=(
                "DemoAIProvider stub. Real invoice-extract will parse OCR text into "
                "typed header/line JSON with confidence scores. "
                f"Input keys: {list(request.input.keys())}."
            ),
            sources=[],
            requires_confirmation=True,
        )

    async def invoice_anomalies(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            result={
                "provider": "demo",
                "signals": [
                    {
                        "code": "scaffold_placeholder",
                        "severity": "info",
                        "message": (
                            "Anomaly Radar not wired yet. Future signals: unusual "
                            "supplier amount, duplicate-like invoice, total/tax "
                            "discrepancy, changed payment details."
                        ),
                        "is_fraud_verdict": False,
                    }
                ],
            },
            explanation=(
                "Invoice Anomaly Radar differentiator stub. Rules first; AI may "
                "explain signals but never declares fraud."
            ),
            sources=[
                AISource(
                    type="placeholder",
                    id="00000000-0000-0000-0000-000000000000",
                    label="Seed invoices not yet loaded",
                )
            ],
            requires_confirmation=False,
        )

    async def category_suggestion(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            result={
                "provider": "demo",
                "suggested_category": None,
                "candidates": [],
                "note": "Category suggestion requires seeded history",
            },
            explanation="Demo stub. User must confirm any category before save.",
            sources=[],
            requires_confirmation=True,
        )
