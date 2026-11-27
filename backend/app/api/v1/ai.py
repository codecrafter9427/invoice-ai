"""AI endpoints — DemoAIProvider by default; optional Ollama.

Extract / category require confirmation. Anomaly Radar is rules-first and
never declares fraud. Totals remain deterministic code elsewhere.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai import get_ai_provider
from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.rate_limit import check_rate_limit
from app.models import Invoice, Supplier
from app.schemas.common import AIRequest, AIResponse
from app.services.anomaly_radar import load_and_evaluate
from app.services.category_suggest import suggest_category
from app.services.extract import explain_validation_issues
from app.services.po_match import find_po_candidates

router = APIRouter()


def _ai_rate_limit(request: Request, user: CurrentUser) -> None:
    settings = get_settings()
    check_rate_limit(
        f"ai:{user.id}:{request.url.path}",
        limit=settings.ai_rate_limit,
        window_seconds=settings.ai_rate_window_seconds,
        message="Too many AI requests — try again shortly",
    )


@router.post("/invoice-extract", response_model=AIResponse)
async def invoice_extract(
    body: AIRequest,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> AIResponse:
    """Extract header/lines from text/OCR text. OCR unverified until review."""
    _ai_rate_limit(request, user)
    payload = dict(body.input)

    # Optional: explain known validation issue codes
    issues = payload.get("validation_issues")
    if isinstance(issues, list) and issues:
        payload["validation_explanations"] = explain_validation_issues(
            [str(c) for c in issues]
        )

    # Candidate PO match only (never auto-link)
    po_ref = payload.get("po_reference")
    if not po_ref and isinstance(payload.get("header"), dict):
        po_ref = payload["header"].get("po_reference")
    supplier_id = payload.get("supplier_id")
    total = payload.get("total")
    if supplier_id or po_ref or total:
        try:
            sid = UUID(str(supplier_id)) if supplier_id else None
        except ValueError:
            sid = None
        payload["po_candidates"] = find_po_candidates(
            db,
            organization_id=user.organization_id,
            po_reference=str(po_ref) if po_ref else None,
            supplier_id=sid,
            invoice_total=Decimal(str(total)) if total is not None else None,
        )

    provider = get_ai_provider()
    request = AIRequest(
        input=payload,
        context_ids=body.context_ids,
        options=body.options,
    )
    response = await provider.invoice_extract(request)

    # After extract, enrich PO candidates from extracted header if not provided
    result = dict(response.result)
    header = result.get("header") if isinstance(result.get("header"), dict) else {}
    if not result.get("po_candidates"):
        result["po_candidates"] = find_po_candidates(
            db,
            organization_id=user.organization_id,
            po_reference=header.get("po_reference") or payload.get("po_reference"),
            supplier_id=None,
            invoice_total=header.get("total") or payload.get("total"),
        )
    result["ocr_verified"] = False
    result["requires_user_review"] = True
    return AIResponse(
        result=result,
        explanation=response.explanation,
        sources=response.sources,
        requires_confirmation=True,
    )


@router.post("/invoice-anomalies", response_model=AIResponse)
async def invoice_anomalies(
    body: AIRequest,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> AIResponse:
    """Invoice Anomaly Radar — rules-first signals; never a fraud verdict."""
    _ai_rate_limit(request, user)
    payload = dict(body.input)
    invoice_id_raw = payload.get("invoice_id") or (
        body.context_ids[0] if body.context_ids else None
    )

    if invoice_id_raw:
        try:
            invoice_id = UUID(str(invoice_id_raw))
        except ValueError as exc:
            raise ApiError(
                status_code=422,
                code="invalid_invoice_id",
                message="invoice_id must be a UUID",
            ) from exc

        inv, signals = load_and_evaluate(
            db,
            organization_id=user.organization_id,
            invoice_id=invoice_id,
            stated_payment_details=payload.get("stated_payment_details"),
        )
        if inv is None:
            raise ApiError(
                status_code=404,
                code="invoice_not_found",
                message="Invoice not found in your organization",
            )
        payload["signals"] = signals
        payload["invoice_id"] = str(inv.id)
        payload["invoice_number"] = inv.invoice_number
    else:
        # Stateless path: evaluate from provided amounts / flags
        payload.setdefault("signals", None)

    provider = get_ai_provider()
    response = await provider.invoice_anomalies(
        AIRequest(input=payload, context_ids=body.context_ids, options=body.options)
    )
    result = dict(response.result)
    result["never_declares_fraud"] = True
    result["fraud_verdict"] = None
    for s in result.get("signals", []) or []:
        if isinstance(s, dict):
            s["is_fraud_verdict"] = False
    return AIResponse(
        result=result,
        explanation=response.explanation,
        sources=response.sources,
        requires_confirmation=False,
    )


@router.post("/category-suggestion", response_model=AIResponse)
async def category_suggestion(
    body: AIRequest,
    user: CurrentUser,
    db: DbSession,
    request: Request,
) -> AIResponse:
    """Suggest accounting category; user must confirm."""
    _ai_rate_limit(request, user)
    payload = dict(body.input)
    description = str(payload.get("description") or "")
    lines = payload.get("line_descriptions") or []
    if not isinstance(lines, list):
        lines = [str(lines)]

    # If invoice_id provided, pull line descriptions from DB
    invoice_id_raw = payload.get("invoice_id")
    if invoice_id_raw:
        try:
            invoice_id = UUID(str(invoice_id_raw))
        except ValueError as exc:
            raise ApiError(
                status_code=422,
                code="invalid_invoice_id",
                message="invoice_id must be a UUID",
            ) from exc
        inv = db.scalar(
            select(Invoice)
            .where(
                Invoice.id == invoice_id,
                Invoice.organization_id == user.organization_id,
            )
            .options(selectinload(Invoice.lines))
        )
        if inv is None:
            raise ApiError(
                status_code=404,
                code="invoice_not_found",
                message="Invoice not found in your organization",
            )
        if not lines:
            lines = [ln.description for ln in inv.lines]
        if not description and inv.lines:
            description = inv.lines[0].description
        supplier = db.get(Supplier, inv.supplier_id)
        if supplier and not description:
            description = supplier.name

    suggestion = suggest_category(
        db,
        organization_id=user.organization_id,
        description=description,
        line_descriptions=[str(x) for x in lines],
    )
    payload["suggestion"] = suggestion
    payload["description"] = description
    payload["line_descriptions"] = lines

    provider = get_ai_provider()
    response = await provider.category_suggestion(
        AIRequest(input=payload, context_ids=body.context_ids, options=body.options)
    )
    return AIResponse(
        result={**dict(response.result), **suggestion, "provider": response.result.get("provider", "demo")},
        explanation=response.explanation,
        sources=response.sources,
        requires_confirmation=True,
    )
