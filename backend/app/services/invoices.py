"""Invoice domain helpers: duplicates, payments, status transitions."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Invoice, InvoiceStatus, Payment
from app.services.totals import money


def find_duplicate_invoices(
    db: Session,
    *,
    organization_id: UUID,
    supplier_id: UUID,
    invoice_number: str,
    exclude_invoice_id: UUID | None = None,
) -> list[Invoice]:
    q = select(Invoice).where(
        Invoice.organization_id == organization_id,
        Invoice.supplier_id == supplier_id,
        Invoice.invoice_number == invoice_number.strip(),
        Invoice.archived.is_(False),
    )
    if exclude_invoice_id is not None:
        q = q.where(Invoice.id != exclude_invoice_id)
    return list(db.scalars(q).all())


def validate_invoice_dates(
    invoice_date: date,
    due_date: date | None,
) -> list[str]:
    issues: list[str] = []
    if due_date is not None and due_date < invoice_date:
        issues.append("due_before_invoice_date")
    return issues


def apply_payment_to_invoice(invoice: Invoice, payment_amount: Decimal) -> None:
    """Update amount_paid / balance_due / status after a payment is recorded."""
    amount = money(payment_amount)
    if amount <= Decimal("0.00"):
        raise ApiError(
            status_code=422,
            code="invalid_payment_amount",
            message="Payment amount must be greater than zero",
        )
    new_paid = money(invoice.amount_paid + amount)
    if new_paid > money(invoice.total):
        raise ApiError(
            status_code=422,
            code="payment_exceeds_balance",
            message="Payment would exceed invoice total",
            details={
                "total": str(invoice.total),
                "amount_paid": str(invoice.amount_paid),
                "attempted": str(amount),
            },
        )
    invoice.amount_paid = new_paid
    invoice.balance_due = money(invoice.total - new_paid)
    if invoice.balance_due == Decimal("0.00"):
        invoice.status = InvoiceStatus.PAID
    elif new_paid > Decimal("0.00"):
        invoice.status = InvoiceStatus.PARTIALLY_PAID


def recalculate_balance_from_payments(invoice: Invoice, payments: list[Payment]) -> None:
    paid = money(sum((p.amount for p in payments), Decimal("0.00")))
    invoice.amount_paid = paid
    invoice.balance_due = money(invoice.total - paid)
    if paid <= Decimal("0.00"):
        return
    if invoice.balance_due == Decimal("0.00"):
        invoice.status = InvoiceStatus.PAID
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
