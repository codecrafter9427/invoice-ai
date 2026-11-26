"""Payments API — record partial/full payments and update balances."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ApiError
from app.models import Invoice, InvoiceStatus, Payment, PaymentMethod, User, UserRole
from app.schemas.payments import PaymentCreate, PaymentListResponse, PaymentOut
from app.services.audit import record_audit
from app.services.invoices import apply_payment_to_invoice
from app.services.totals import money

router = APIRouter()

PAYABLE_STATUSES = {
    InvoiceStatus.APPROVED,
    InvoiceStatus.PARTIALLY_PAID,
}


def _payment_out(payment: Payment, invoice: Invoice | None = None) -> PaymentOut:
    inv = invoice or payment.invoice
    return PaymentOut(
        id=payment.id,
        organization_id=payment.organization_id,
        invoice_id=payment.invoice_id,
        amount=str(payment.amount),
        payment_date=payment.payment_date,
        method=payment.method.value,
        reference=payment.reference,
        recorded_by_id=payment.recorded_by_id,
        created_at=payment.created_at,
        invoice_status=inv.status.value if inv else None,
        invoice_balance_due=str(inv.balance_due) if inv else None,
        invoice_amount_paid=str(inv.amount_paid) if inv else None,
    )


def _get_org_invoice(db: DbSession, user: User, invoice_id: UUID) -> Invoice:
    inv = db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.payments))
    )
    if inv is None or inv.archived:
        raise ApiError(status_code=404, code="not_found", message="Invoice not found")
    if inv.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return inv


@router.get("", response_model=PaymentListResponse)
def list_payments(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    invoice_id: UUID | None = None,
) -> PaymentListResponse:
    filters = [Payment.organization_id == user.organization_id]
    if invoice_id is not None:
        filters.append(Payment.invoice_id == invoice_id)
    total = db.scalar(select(func.count()).select_from(Payment).where(*filters)) or 0
    rows = db.scalars(
        select(Payment)
        .where(*filters)
        .options(selectinload(Payment.invoice))
        .order_by(Payment.payment_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaymentListResponse(
        items=[_payment_out(p) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=PaymentOut,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.APPROVER))],
)
def create_payment(
    body: PaymentCreate,
    user: CurrentUser,
    db: DbSession,
) -> PaymentOut:
    try:
        method = PaymentMethod(body.method.strip().lower())
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="invalid_payment_method",
            message=f"Unknown payment method: {body.method}",
        ) from exc

    inv = _get_org_invoice(db, user, body.invoice_id)
    if inv.status not in PAYABLE_STATUSES:
        raise ApiError(
            status_code=409,
            code="invoice_not_payable",
            message=f"Invoice status {inv.status.value} does not allow payments",
            details={"allowed": [s.value for s in PAYABLE_STATUSES]},
        )

    amount = money(body.amount)
    apply_payment_to_invoice(inv, amount)

    payment = Payment(
        organization_id=user.organization_id,
        invoice_id=inv.id,
        amount=amount,
        payment_date=body.payment_date,
        method=method,
        reference=body.reference,
        recorded_by_id=user.id,
    )
    db.add(payment)
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="payment",
        entity_id=None,
        action="record",
        details={
            "invoice_id": str(inv.id),
            "amount": str(amount),
            "method": method.value,
            "new_balance_due": str(inv.balance_due),
            "new_status": inv.status.value,
        },
    )
    db.flush()
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="payment",
        entity_id=payment.id,
        action="created",
        details={"invoice_id": str(inv.id), "amount": str(amount)},
    )
    db.commit()
    db.refresh(payment)
    return _payment_out(payment, inv)


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> PaymentOut:
    payment = db.scalar(
        select(Payment)
        .where(Payment.id == payment_id)
        .options(selectinload(Payment.invoice))
    )
    if payment is None:
        raise ApiError(status_code=404, code="not_found", message="Payment not found")
    if payment.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return _payment_out(payment)
