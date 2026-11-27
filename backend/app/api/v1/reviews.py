"""Standalone invoice-reviews queue API — list, create, resolve."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ApiError
from app.models import Invoice, InvoiceReview, InvoiceStatus, ReviewFlag, User, UserRole
from app.schemas.reviews import (
    InvoiceReviewCreate,
    InvoiceReviewListResponse,
    InvoiceReviewOut,
    InvoiceReviewUpdate,
    ReviewQueueItem,
    ReviewQueueResponse,
)
from app.services.audit import record_audit

router = APIRouter()


def _parse_flag(raw: str | None) -> ReviewFlag:
    if raw is None:
        return ReviewFlag.NONE
    try:
        return ReviewFlag(raw.strip().lower())
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="invalid_flag",
            message=f"flag must be one of: {[f.value for f in ReviewFlag]}",
        ) from exc


def _review_out(
    review: InvoiceReview, inv: Invoice | None = None
) -> InvoiceReviewOut:
    invoice = inv or review.invoice
    return InvoiceReviewOut(
        id=review.id,
        organization_id=review.organization_id,
        invoice_id=review.invoice_id,
        invoice_number=invoice.invoice_number if invoice else None,
        invoice_status=invoice.status.value if invoice else None,
        reviewer_id=review.reviewer_id,
        flag=review.flag.value,
        notes=review.notes,
        is_resolved=review.is_resolved,
        created_at=review.created_at,
        updated_at=review.updated_at,
        has_duplicate_warning=invoice.has_duplicate_warning if invoice else None,
        has_anomaly_signal=invoice.has_anomaly_signal if invoice else None,
    )


def _get_org_invoice(db: DbSession, user: User, invoice_id: UUID) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if inv is None or inv.archived:
        raise ApiError(status_code=404, code="not_found", message="Invoice not found")
    if inv.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return inv


@router.get("/queue", response_model=ReviewQueueResponse)
def review_queue(
    user: CurrentUser,
    db: DbSession,
) -> ReviewQueueResponse:
    """Invoices in needs_review for the current org (standalone queue)."""
    rows = list(
        db.scalars(
            select(Invoice)
            .where(
                Invoice.organization_id == user.organization_id,
                Invoice.status == InvoiceStatus.NEEDS_REVIEW,
                Invoice.archived.is_(False),
            )
            .options(
                selectinload(Invoice.supplier),
                selectinload(Invoice.reviews),
            )
            .order_by(Invoice.invoice_date.desc())
        ).all()
    )
    items: list[ReviewQueueItem] = []
    for inv in rows:
        unresolved = [r for r in inv.reviews if not r.is_resolved]
        latest = unresolved[0] if unresolved else (inv.reviews[0] if inv.reviews else None)
        items.append(
            ReviewQueueItem(
                invoice_id=inv.id,
                invoice_number=inv.invoice_number,
                supplier_id=inv.supplier_id,
                supplier_name=inv.supplier.name if inv.supplier else None,
                status=inv.status.value,
                total=str(inv.total),
                balance_due=str(inv.balance_due),
                currency=inv.currency,
                has_duplicate_warning=inv.has_duplicate_warning,
                has_anomaly_signal=inv.has_anomaly_signal,
                unresolved_review_count=len(unresolved),
                latest_flag=latest.flag.value if latest else None,
                latest_notes=latest.notes if latest else None,
            )
        )
    return ReviewQueueResponse(items=items, total=len(items))


@router.get("", response_model=InvoiceReviewListResponse)
def list_reviews(
    user: CurrentUser,
    db: DbSession,
    invoice_id: UUID | None = None,
    unresolved_only: bool = Query(False),
) -> InvoiceReviewListResponse:
    filters = [InvoiceReview.organization_id == user.organization_id]
    if invoice_id is not None:
        filters.append(InvoiceReview.invoice_id == invoice_id)
    if unresolved_only:
        filters.append(InvoiceReview.is_resolved.is_(False))

    total = (
        db.scalar(select(func.count()).select_from(InvoiceReview).where(*filters)) or 0
    )
    rows = list(
        db.scalars(
            select(InvoiceReview)
            .where(*filters)
            .options(selectinload(InvoiceReview.invoice))
            .order_by(InvoiceReview.created_at.desc())
            .limit(200)
        ).all()
    )
    return InvoiceReviewListResponse(
        items=[_review_out(r) for r in rows],
        total=total,
    )


@router.post(
    "",
    response_model=InvoiceReviewOut,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER))],
)
def create_review(
    body: InvoiceReviewCreate,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceReviewOut:
    inv = _get_org_invoice(db, user, body.invoice_id)
    flag = _parse_flag(body.flag)
    review = InvoiceReview(
        organization_id=user.organization_id,
        invoice_id=inv.id,
        reviewer_id=user.id,
        flag=flag,
        notes=body.notes,
        is_resolved=False,
    )
    db.add(review)
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice_review",
        entity_id=None,
        action="review_create",
        details={
            "invoice_id": str(inv.id),
            "flag": flag.value,
            "notes": body.notes,
        },
    )
    db.commit()
    db.refresh(review)
    return _review_out(review, inv)


@router.get("/{review_id}", response_model=InvoiceReviewOut)
def get_review(
    review_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceReviewOut:
    review = db.scalar(
        select(InvoiceReview)
        .where(InvoiceReview.id == review_id)
        .options(selectinload(InvoiceReview.invoice))
    )
    if review is None:
        raise ApiError(status_code=404, code="not_found", message="Review not found")
    if review.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return _review_out(review)


@router.patch(
    "/{review_id}",
    response_model=InvoiceReviewOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.REVIEWER))],
)
def update_review(
    review_id: UUID,
    body: InvoiceReviewUpdate,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceReviewOut:
    review = db.scalar(
        select(InvoiceReview)
        .where(InvoiceReview.id == review_id)
        .options(selectinload(InvoiceReview.invoice))
    )
    if review is None:
        raise ApiError(status_code=404, code="not_found", message="Review not found")
    if review.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )

    if body.flag is not None:
        review.flag = _parse_flag(body.flag)
    if body.notes is not None:
        review.notes = body.notes
    if body.is_resolved is not None:
        review.is_resolved = body.is_resolved
    review.reviewer_id = user.id

    action = "review_resolve" if body.is_resolved else "review_update"
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice_review",
        entity_id=review.id,
        action=action,
        details={
            "invoice_id": str(review.invoice_id),
            "flag": review.flag.value,
            "is_resolved": review.is_resolved,
            "notes": review.notes,
        },
    )
    db.commit()
    db.refresh(review)
    return _review_out(review)
