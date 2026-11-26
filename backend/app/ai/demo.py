"""Deterministic DemoAIProvider — works without Ollama or any paid API."""

from __future__ import annotations

from typing import Any

from app.ai.base import AIProvider
from app.schemas.common import AIRequest, AIResponse, AISource
from app.services.anomaly_radar import evaluate_anomaly_signals, summarize_radar
from app.services.extract import explain_validation_issues, extract_invoice_from_text


class DemoAIProvider(AIProvider):
    """Rules + heuristic stubs. No network. Never mutates records."""

    async def invoice_extract(self, request: AIRequest) -> AIResponse:
        text = (
            request.input.get("text")
            or request.input.get("ocr_text")
            or request.input.get("document_text")
            or ""
        )
        if not isinstance(text, str):
            text = str(text)

        extracted = extract_invoice_from_text(text)

        # Optional validation codes from caller (deterministic codes)
        extra_issues = request.input.get("validation_issues") or []
        if isinstance(extra_issues, list) and extra_issues:
            extracted["validation_explanations"] = (
                list(extracted.get("validation_explanations") or [])
                + explain_validation_issues([str(c) for c in extra_issues])
            )
            for code in extra_issues:
                if code not in extracted["validation_issues"]:
                    extracted["validation_issues"].append(str(code))

        # PO candidates may be precomputed by the API layer
        if request.input.get("po_candidates"):
            extracted["po_candidates"] = request.input["po_candidates"]

        extracted["provider"] = "demo"
        extracted["status"] = "ok"

        sources: list[AISource] = []
        if text.strip():
            sources.append(
                AISource(type="ocr_text", id="input", label="Pasted / OCR text (unverified)")
            )
        for cid in request.context_ids:
            sources.append(AISource(type="context", id=str(cid), label="Context id"))

        return AIResponse(
            result=extracted,
            explanation=(
                "Demo extract parsed invoice text with deterministic heuristics. "
                "Field confidence is approximate. OCR remains unverified until a "
                "user reviews and confirms fields. Totals must be recalculated by "
                "deterministic code, not AI. PO matches (if any) are candidates only."
            ),
            sources=sources,
            requires_confirmation=True,
        )

    async def invoice_anomalies(self, request: AIRequest) -> AIResponse:
        # Prefer precomputed signals from API (DB-backed rules)
        signals = request.input.get("signals")
        if not isinstance(signals, list):
            signals = self._signals_from_payload(request.input)

        # Harden: never allow fraud verdict
        cleaned: list[dict[str, Any]] = []
        for s in signals:
            if not isinstance(s, dict):
                continue
            item = dict(s)
            item["is_fraud_verdict"] = False
            if "fraud" in str(item.get("message", "")).lower() and "not" not in str(
                item.get("message", "")
            ).lower():
                item["message"] = (
                    "Review signal only — do not treat as a fraud determination."
                )
            cleaned.append(item)

        invoice_id = (
            request.input.get("invoice_id")
            or (request.context_ids[0] if request.context_ids else None)
        )
        sources = [
            AISource(
                type="invoice",
                id=str(invoice_id or "unknown"),
                label="Invoice under review",
            ),
            AISource(type="rules", id="anomaly-radar", label="Rules-first Anomaly Radar"),
        ]

        return AIResponse(
            result={
                "provider": "demo",
                "signals": cleaned,
                "signal_count": len(cleaned),
                "fraud_verdict": None,
                "never_declares_fraud": True,
            },
            explanation=summarize_radar(cleaned)
            + " AI may rephrase why a rule fired; it does not decide fraud.",
            sources=sources,
            requires_confirmation=False,
        )

    def _signals_from_payload(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        """Offline path when API did not precompute — uses a minimal stub invoice shape."""
        from types import SimpleNamespace

        from decimal import Decimal

        subtotal = Decimal(str(payload.get("subtotal", "0")))
        tax_total = Decimal(str(payload.get("tax_total", "0")))
        total = Decimal(str(payload.get("total", "0")))
        inv = SimpleNamespace(
            subtotal=subtotal,
            tax_total=tax_total,
            total=total,
            lines=[],
            has_duplicate_warning=bool(payload.get("has_duplicate_warning")),
            has_anomaly_signal=bool(payload.get("has_anomaly_signal")),
            anomaly_notes=payload.get("anomaly_notes"),
            supplier_id=payload.get("supplier_id"),
            invoice_number=str(payload.get("invoice_number", "")),
            id=payload.get("invoice_id"),
        )
        peers = [Decimal(str(p)) for p in payload.get("peer_totals", [])]
        supplier = None
        if payload.get("directory_payment_details"):
            supplier = SimpleNamespace(
                payment_details=payload.get("directory_payment_details")
            )
        return evaluate_anomaly_signals(
            invoice=inv,  # type: ignore[arg-type]
            supplier=supplier,  # type: ignore[arg-type]
            peer_totals=peers,
            stated_payment_details=payload.get("stated_payment_details"),
            duplicates=[],
        )

    async def category_suggestion(self, request: AIRequest) -> AIResponse:
        # Prefer API-precomputed suggestion
        suggestion = request.input.get("suggestion")
        if isinstance(suggestion, dict):
            result = {**suggestion, "provider": "demo"}
        else:
            description = str(request.input.get("description") or "")
            lines = request.input.get("line_descriptions") or []
            text = " ".join([description] + [str(x) for x in lines]).lower()
            # Offline keyword stub without DB
            code = None
            name = None
            if any(k in text for k in ("paper", "office", "stationery")):
                code, name = "OFFICE", "Office Supplies"
            elif any(k in text for k in ("electric", "utility", "water")):
                code, name = "UTIL", "Utilities"
            elif any(k in text for k in ("license", "software", "hosting", "saas")):
                code, name = "SOFT", "Software & SaaS"
            elif any(k in text for k in ("freight", "shipping", "logistics")):
                code, name = "LOGISTICS", "Freight & Logistics"
            result = {
                "provider": "demo",
                "suggested_category": (
                    {"code": code, "name": name} if code else None
                ),
                "candidates": [],
                "note": "Offline demo suggestion — confirm before save.",
            }

        return AIResponse(
            result=result,
            explanation=(
                "Accounting category suggestion from description heuristics. "
                "This is not accounting or tax advice. User must confirm before save."
            ),
            sources=[
                AISource(
                    type="heuristic",
                    id="category-keywords",
                    label="Keyword → category map",
                )
            ],
            requires_confirmation=True,
        )
