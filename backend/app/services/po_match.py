"""Purchase-order candidate matching — never auto-links; candidate only."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PurchaseOrderReference
from app.services.totals import money


def find_po_candidates(
    db: Session,
    *,
    organization_id: UUID,
    po_reference: str | None,
    supplier_id: UUID | None = None,
    invoice_total: Decimal | str | None = None,
) -> list[dict[str, Any]]:
    """Return candidate PO matches. Caller must treat as suggestions only."""
    refs = list(
        db.scalars(
            select(PurchaseOrderReference).where(
                PurchaseOrderReference.organization_id == organization_id
            )
        ).all()
    )
    if not refs:
        return []

    po_ref = (po_reference or "").strip().upper()
    total = money(invoice_total) if invoice_total is not None else None
    candidates: list[dict[str, Any]] = []

    for ref in refs:
        score = 0.0
        reasons: list[str] = []
        if po_ref and ref.po_number.upper() == po_ref:
            score += 0.7
            reasons.append("exact_po_number")
        elif po_ref and po_ref in ref.po_number.upper():
            score += 0.4
            reasons.append("partial_po_number")
        if supplier_id and ref.supplier_id == supplier_id:
            score += 0.2
            reasons.append("same_supplier")
        if total is not None and ref.amount is not None:
            if money(ref.amount) == total:
                score += 0.25
                reasons.append("amount_equals")
            elif abs(money(ref.amount) - total) <= money("50"):
                score += 0.1
                reasons.append("amount_near")

        if score <= 0:
            continue
        candidates.append(
            {
                "id": str(ref.id),
                "po_number": ref.po_number,
                "supplier_id": str(ref.supplier_id) if ref.supplier_id else None,
                "amount": str(ref.amount) if ref.amount is not None else None,
                "currency": ref.currency,
                "score": round(min(score, 1.0), 3),
                "reasons": reasons,
                "match_type": "candidate_only",
                "note": "Candidate match only — do not auto-link without user confirmation.",
            }
        )

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:5]
