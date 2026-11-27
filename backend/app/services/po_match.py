"""Purchase-order candidate matching — never auto-links; candidate only."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Invoice, PurchaseOrderReference, User
from app.services.audit import record_audit
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
                "differences": diff_invoice_vs_po(
                    invoice_po_reference=po_reference,
                    invoice_supplier_id=supplier_id,
                    invoice_total=total,
                    po=ref,
                ),
            }
        )

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:5]


def diff_invoice_vs_po(
    *,
    invoice_po_reference: str | None,
    invoice_supplier_id: UUID | None,
    invoice_total: Decimal | str | None,
    po: PurchaseOrderReference,
) -> list[dict[str, Any]]:
    """Deterministic field differences between invoice and a PO reference."""
    diffs: list[dict[str, Any]] = []
    inv_po = (invoice_po_reference or "").strip()
    if inv_po.upper() != po.po_number.upper():
        diffs.append(
            {
                "field": "po_number",
                "invoice_value": inv_po or None,
                "po_value": po.po_number,
                "match": False,
            }
        )
    else:
        diffs.append(
            {
                "field": "po_number",
                "invoice_value": inv_po,
                "po_value": po.po_number,
                "match": True,
            }
        )

    inv_sid = str(invoice_supplier_id) if invoice_supplier_id else None
    po_sid = str(po.supplier_id) if po.supplier_id else None
    diffs.append(
        {
            "field": "supplier_id",
            "invoice_value": inv_sid,
            "po_value": po_sid,
            "match": inv_sid is not None and po_sid is not None and inv_sid == po_sid,
        }
    )

    inv_total = money(invoice_total) if invoice_total is not None else None
    po_amount = money(po.amount) if po.amount is not None else None
    amount_match = (
        inv_total is not None and po_amount is not None and inv_total == po_amount
    )
    diffs.append(
        {
            "field": "amount",
            "invoice_value": str(inv_total) if inv_total is not None else None,
            "po_value": str(po_amount) if po_amount is not None else None,
            "match": amount_match,
        }
    )
    return diffs


def candidates_for_invoice(db: Session, inv: Invoice) -> list[dict[str, Any]]:
    return find_po_candidates(
        db,
        organization_id=inv.organization_id,
        po_reference=inv.po_reference,
        supplier_id=inv.supplier_id,
        invoice_total=inv.total,
    )


def confirm_po_match(
    db: Session,
    *,
    user: User,
    inv: Invoice,
    purchase_order_reference_id: UUID,
    confirmed: bool,
) -> Invoice:
    """Human-confirm a PO link. Requires confirmed=true; never auto-matches."""
    if not confirmed:
        raise ApiError(
            status_code=422,
            code="confirmation_required",
            message="PO match requires confirmed=true — never auto-linked",
        )

    po = db.get(PurchaseOrderReference, purchase_order_reference_id)
    if po is None or po.organization_id != user.organization_id:
        raise ApiError(
            status_code=404,
            code="po_not_found",
            message="Purchase order reference not found in your organization",
        )

    previous = inv.purchase_order_reference_id
    inv.purchase_order_reference_id = po.id
    if not inv.po_reference:
        inv.po_reference = po.po_number

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="po_match_confirm",
        details={
            "purchase_order_reference_id": str(po.id),
            "po_number": po.po_number,
            "previous_purchase_order_reference_id": str(previous) if previous else None,
            "confirmed": True,
            "differences": diff_invoice_vs_po(
                invoice_po_reference=inv.po_reference,
                invoice_supplier_id=inv.supplier_id,
                invoice_total=inv.total,
                po=po,
            ),
        },
    )
    return inv
