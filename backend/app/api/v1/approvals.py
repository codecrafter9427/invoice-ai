"""Approvals API — role-checked approve/reject with audit."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ApiError
from app.models import (
    ApprovalDecision,
    ApprovalStep,
    Invoice,
    InvoiceStatus,
    User,
    UserRole,
)
from app.schemas.approvals import ApprovalDecide, ApprovalListResponse, ApprovalStepOut
from app.services.audit import record_audit

router = APIRouter()


def _get_org_invoice(db: DbSession, user: User, invoice_id: UUID) -> Invoice:
    inv = db.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(selectinload(Invoice.approval_steps))
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


def _step_out(step: ApprovalStep) -> ApprovalStepOut:
    return ApprovalStepOut(
        id=step.id,
        invoice_id=step.invoice_id,
        step_order=step.step_order,
        approver_id=step.approver_id,
        decision=step.decision.value,
        comment=step.comment,
        decided_at=step.decided_at,
        created_at=step.created_at,
    )


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    user: CurrentUser,
    db: DbSession,
    invoice_id: UUID | None = None,
    pending_only: bool = Query(False),
) -> ApprovalListResponse:
    filters = [ApprovalStep.organization_id == user.organization_id]
    if invoice_id is not None:
        filters.append(ApprovalStep.invoice_id == invoice_id)
    if pending_only:
        # Pending approvals = invoices awaiting decision
        inv_ids = db.scalars(
            select(Invoice.id).where(
                Invoice.organization_id == user.organization_id,
                Invoice.status == InvoiceStatus.PENDING_APPROVAL,
                Invoice.archived.is_(False),
            )
        ).all()
        if not inv_ids:
            return ApprovalListResponse(items=[], total=0)
        filters.append(ApprovalStep.invoice_id.in_(list(inv_ids)))

    total = (
        db.scalar(select(func.count()).select_from(ApprovalStep).where(*filters)) or 0
    )
    rows = db.scalars(
        select(ApprovalStep)
        .where(*filters)
        .order_by(ApprovalStep.created_at.desc())
        .limit(100)
    ).all()
    return ApprovalListResponse(items=[_step_out(r) for r in rows], total=total)


@router.get("/pending-invoices")
def list_pending_approval_invoices(
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Convenience list of invoices in pending_approval for the Approvals UI."""
    rows = db.scalars(
        select(Invoice)
        .where(
            Invoice.organization_id == user.organization_id,
            Invoice.status == InvoiceStatus.PENDING_APPROVAL,
            Invoice.archived.is_(False),
        )
        .order_by(Invoice.invoice_date.desc())
    ).all()
    return {
        "items": [
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "supplier_id": str(inv.supplier_id),
                "status": inv.status.value,
                "total": str(inv.total),
                "balance_due": str(inv.balance_due),
                "currency": inv.currency,
                "has_duplicate_warning": inv.has_duplicate_warning,
            }
            for inv in rows
        ],
        "total": len(rows),
    }


@router.post(
    "",
    response_model=ApprovalStepOut,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.APPROVER))],
)
def decide_approval(
    body: ApprovalDecide,
    user: CurrentUser,
    db: DbSession,
    invoice_id: UUID = Query(..., description="Invoice to approve or reject"),
) -> ApprovalStepOut:
    decision_raw = body.decision.strip().lower()
    if decision_raw not in {"approved", "rejected"}:
        raise ApiError(
            status_code=422,
            code="invalid_decision",
            message="decision must be approved or rejected",
        )
    if decision_raw == "rejected" and not (body.comment and body.comment.strip()):
        raise ApiError(
            status_code=422,
            code="rejection_reason_required",
            message="Rejection requires a comment/reason",
        )

    inv = _get_org_invoice(db, user, invoice_id)
    if inv.status != InvoiceStatus.PENDING_APPROVAL:
        raise ApiError(
            status_code=409,
            code="invalid_transition",
            message=f"Invoice must be pending_approval (currently {inv.status.value})",
        )

    decision = (
        ApprovalDecision.APPROVED
        if decision_raw == "approved"
        else ApprovalDecision.REJECTED
    )
    step_order = len(inv.approval_steps) + 1
    step = ApprovalStep(
        organization_id=user.organization_id,
        invoice_id=inv.id,
        step_order=step_order,
        approver_id=user.id,
        decision=decision,
        comment=body.comment,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(step)

    if decision == ApprovalDecision.APPROVED:
        inv.status = InvoiceStatus.APPROVED
    else:
        inv.status = InvoiceStatus.REJECTED

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action=f"approval_{decision_raw}",
        details={
            "decision": decision_raw,
            "comment": body.comment,
            "step_order": step_order,
        },
    )
    db.commit()
    db.refresh(step)
    return _step_out(step)


@router.get("/{approval_id}", response_model=ApprovalStepOut)
def get_approval(
    approval_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ApprovalStepOut:
    step = db.get(ApprovalStep, approval_id)
    if step is None:
        raise ApiError(status_code=404, code="not_found", message="Approval not found")
    if step.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return _step_out(step)
