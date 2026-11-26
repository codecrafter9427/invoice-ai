"""Invoices API — CRUD, line items, validation, workflow basics."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ApiError, coming_soon
from app.models import Invoice, InvoiceLine, InvoiceStatus, Supplier, User, UserRole
from app.schemas.invoices import (
    InvoiceCreate,
    InvoiceLineOut,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceOut,
    InvoiceUpdate,
    InvoiceWorkflowAction,
)
from app.services.audit import record_audit
from app.services.invoices import find_duplicate_invoices, validate_invoice_dates
from app.services.totals import compute_invoice_totals, money, validate_header_totals
from fastapi.responses import JSONResponse

router = APIRouter()
lines_router = APIRouter()

EDITABLE_STATUSES = {
    InvoiceStatus.UPLOADED,
    InvoiceStatus.PROCESSING,
    InvoiceStatus.NEEDS_REVIEW,
    InvoiceStatus.REJECTED,
}


def _line_out(line: InvoiceLine) -> InvoiceLineOut:
    return InvoiceLineOut(
        id=line.id,
        line_number=line.line_number,
        description=line.description,
        quantity=str(line.quantity),
        unit_price=str(line.unit_price),
        tax_rate=str(line.tax_rate),
        line_total=str(line.line_total),
    )


def _invoice_out(inv: Invoice, validation_issues: list[str] | None = None) -> InvoiceOut:
    issues = list(validation_issues or [])
    if inv.has_duplicate_warning and "duplicate_invoice" not in issues:
        issues.append("duplicate_invoice")
    issues.extend(
        validate_header_totals(inv.subtotal, inv.tax_total, inv.total)
    )
    issues.extend(validate_invoice_dates(inv.invoice_date, inv.due_date))
    # de-dupe while preserving order
    seen: set[str] = set()
    unique_issues: list[str] = []
    for i in issues:
        if i not in seen:
            seen.add(i)
            unique_issues.append(i)
    return InvoiceOut(
        id=inv.id,
        organization_id=inv.organization_id,
        supplier_id=inv.supplier_id,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        currency=inv.currency,
        subtotal=str(inv.subtotal),
        tax_total=str(inv.tax_total),
        total=str(inv.total),
        amount_paid=str(inv.amount_paid),
        balance_due=str(inv.balance_due),
        po_reference=inv.po_reference,
        terms=inv.terms,
        status=inv.status.value,
        has_duplicate_warning=inv.has_duplicate_warning,
        has_anomaly_signal=inv.has_anomaly_signal,
        anomaly_notes=inv.anomaly_notes,
        archived=inv.archived,
        created_by_id=inv.created_by_id,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        lines=[_line_out(ln) for ln in sorted(inv.lines, key=lambda x: x.line_number)],
        validation_issues=unique_issues,
    )


def _get_org_invoice(
    db: DbSession, user: User, invoice_id: UUID, *, with_lines: bool = True
) -> Invoice:
    q = select(Invoice).where(Invoice.id == invoice_id)
    if with_lines:
        q = q.options(selectinload(Invoice.lines))
    inv = db.scalar(q)
    if inv is None or inv.archived:
        raise ApiError(status_code=404, code="not_found", message="Invoice not found")
    if inv.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return inv


def _assert_supplier(db: DbSession, user: User, supplier_id: UUID) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.archived:
        raise ApiError(status_code=404, code="not_found", message="Supplier not found")
    if supplier.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Supplier belongs to another organization",
        )
    return supplier


def _build_lines_and_totals(
    org_id: UUID,
    line_inputs: list,
    client_subtotal: Decimal | None,
    client_tax: Decimal | None,
    client_total: Decimal | None,
) -> tuple[list[InvoiceLine], Decimal, Decimal, Decimal]:
    tuples = [(ln.quantity, ln.unit_price, ln.tax_rate) for ln in line_inputs]
    subtotal, tax_total, total, per_line = compute_invoice_totals(tuples)

    if client_subtotal is not None and money(client_subtotal) != subtotal:
        raise ApiError(
            status_code=422,
            code="total_mismatch",
            message="Provided subtotal does not match line items",
            details={"expected": str(subtotal), "provided": str(money(client_subtotal))},
        )
    if client_tax is not None and money(client_tax) != tax_total:
        raise ApiError(
            status_code=422,
            code="total_mismatch",
            message="Provided tax_total does not match line items",
            details={"expected": str(tax_total), "provided": str(money(client_tax))},
        )
    if client_total is not None and money(client_total) != total:
        raise ApiError(
            status_code=422,
            code="total_mismatch",
            message="Provided total does not equal subtotal + tax (from lines)",
            details={"expected": str(total), "provided": str(money(client_total))},
        )
    # Also catch explicit header inconsistency if all three provided
    if (
        client_subtotal is not None
        and client_tax is not None
        and client_total is not None
    ):
        issues = validate_header_totals(
            money(client_subtotal), money(client_tax), money(client_total)
        )
        if issues:
            raise ApiError(
                status_code=422,
                code="total_mismatch",
                message="subtotal + tax_total must equal total",
                details={"issues": issues},
            )

    lines: list[InvoiceLine] = []
    for idx, (ln, (_sub, _tax, line_total)) in enumerate(
        zip(line_inputs, per_line, strict=True), start=1
    ):
        lines.append(
            InvoiceLine(
                organization_id=org_id,
                line_number=idx,
                description=ln.description.strip(),
                quantity=ln.quantity,
                unit_price=money(ln.unit_price),
                tax_rate=ln.tax_rate,
                line_total=line_total,
            )
        )
    return lines, subtotal, tax_total, total


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
    has_anomaly: bool | None = None,
) -> InvoiceListResponse:
    filters = [
        Invoice.organization_id == user.organization_id,
        Invoice.archived.is_(False),
    ]
    if status:
        try:
            filters.append(Invoice.status == InvoiceStatus(status))
        except ValueError as exc:
            raise ApiError(
                status_code=422,
                code="invalid_status",
                message=f"Unknown status: {status}",
            ) from exc
    if search:
        like = f"%{search.strip()}%"
        filters.append(Invoice.invoice_number.ilike(like))
    if has_anomaly is True:
        filters.append(
            or_(
                Invoice.has_anomaly_signal.is_(True),
                Invoice.has_duplicate_warning.is_(True),
            )
        )
    elif has_anomaly is False:
        filters.append(Invoice.has_anomaly_signal.is_(False))
        filters.append(Invoice.has_duplicate_warning.is_(False))

    total = db.scalar(select(func.count()).select_from(Invoice).where(*filters)) or 0
    rows = db.scalars(
        select(Invoice)
        .where(*filters)
        .order_by(Invoice.invoice_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    supplier_ids = {r.supplier_id for r in rows}
    names: dict[UUID, str] = {}
    if supplier_ids:
        for s in db.scalars(
            select(Supplier).where(Supplier.id.in_(supplier_ids))
        ).all():
            names[s.id] = s.name

    return InvoiceListResponse(
        items=[
            InvoiceListItem(
                id=inv.id,
                invoice_number=inv.invoice_number,
                supplier_id=inv.supplier_id,
                supplier_name=names.get(inv.supplier_id),
                status=inv.status.value,
                invoice_date=inv.invoice_date,
                total=str(inv.total),
                balance_due=str(inv.balance_due),
                currency=inv.currency,
                has_duplicate_warning=inv.has_duplicate_warning,
                has_anomaly_signal=inv.has_anomaly_signal,
                organization_id=inv.organization_id,
            )
            for inv in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=InvoiceOut,
    status_code=201,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN, UserRole.STAFF, UserRole.REVIEWER, UserRole.APPROVER
            )
        )
    ],
)
def create_invoice(
    body: InvoiceCreate,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceOut:
    _assert_supplier(db, user, body.supplier_id)
    date_issues = validate_invoice_dates(body.invoice_date, body.due_date)
    if date_issues:
        raise ApiError(
            status_code=422,
            code="date_validation",
            message="Invoice dates are invalid",
            details={"issues": date_issues},
        )

    lines, subtotal, tax_total, total = _build_lines_and_totals(
        user.organization_id,
        body.lines,
        body.subtotal,
        body.tax_total,
        body.total,
    )

    duplicates = find_duplicate_invoices(
        db,
        organization_id=user.organization_id,
        supplier_id=body.supplier_id,
        invoice_number=body.invoice_number,
    )
    has_dup = len(duplicates) > 0

    status = (
        InvoiceStatus.NEEDS_REVIEW
        if body.submit_for_review
        else InvoiceStatus.UPLOADED
    )

    inv = Invoice(
        organization_id=user.organization_id,
        supplier_id=body.supplier_id,
        invoice_number=body.invoice_number.strip(),
        invoice_date=body.invoice_date,
        due_date=body.due_date,
        currency=body.currency.upper(),
        subtotal=subtotal,
        tax_total=tax_total,
        total=total,
        amount_paid=money(0),
        balance_due=total,
        po_reference=body.po_reference,
        terms=body.terms,
        status=status,
        has_duplicate_warning=has_dup,
        created_by_id=user.id,
        lines=lines,
    )
    db.add(inv)
    db.flush()

    # Mark existing duplicates as well so seed-style pairs stay consistent
    for other in duplicates:
        other.has_duplicate_warning = True

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="create",
        details={
            "invoice_number": inv.invoice_number,
            "status": inv.status.value,
            "has_duplicate_warning": has_dup,
            "total": str(total),
        },
    )
    db.commit()
    inv = _get_org_invoice(db, user, inv.id)
    return _invoice_out(inv)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceOut:
    return _invoice_out(_get_org_invoice(db, user, invoice_id))


@router.patch(
    "/{invoice_id}",
    response_model=InvoiceOut,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN, UserRole.STAFF, UserRole.REVIEWER, UserRole.APPROVER
            )
        )
    ],
)
def update_invoice(
    invoice_id: UUID,
    body: InvoiceUpdate,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceOut:
    inv = _get_org_invoice(db, user, invoice_id)
    if inv.status not in EDITABLE_STATUSES:
        raise ApiError(
            status_code=409,
            code="invoice_not_editable",
            message=f"Cannot edit invoice in status {inv.status.value}",
        )

    data = body.model_dump(exclude_unset=True)
    if "supplier_id" in data and data["supplier_id"] is not None:
        _assert_supplier(db, user, data["supplier_id"])
        inv.supplier_id = data["supplier_id"]
    if "invoice_number" in data and data["invoice_number"] is not None:
        inv.invoice_number = data["invoice_number"].strip()
    if "invoice_date" in data and data["invoice_date"] is not None:
        inv.invoice_date = data["invoice_date"]
    if "due_date" in data:
        inv.due_date = data["due_date"]
    if "currency" in data and data["currency"] is not None:
        inv.currency = data["currency"].upper()
    if "po_reference" in data:
        inv.po_reference = data["po_reference"]
    if "terms" in data:
        inv.terms = data["terms"]

    date_issues = validate_invoice_dates(inv.invoice_date, inv.due_date)
    if date_issues:
        raise ApiError(
            status_code=422,
            code="date_validation",
            message="Invoice dates are invalid",
            details={"issues": date_issues},
        )

    if "lines" in data and body.lines is not None:
        # replace lines
        inv.lines.clear()
        db.flush()
        new_lines, subtotal, tax_total, total = _build_lines_and_totals(
            user.organization_id,
            body.lines,
            body.subtotal,
            body.tax_total,
            body.total,
        )
        for ln in new_lines:
            ln.invoice_id = inv.id
            inv.lines.append(ln)
        inv.subtotal = subtotal
        inv.tax_total = tax_total
        inv.total = total
        inv.balance_due = money(total - inv.amount_paid)
    elif any(k in data for k in ("subtotal", "tax_total", "total")):
        # header-only total override must still be consistent
        sub = money(body.subtotal) if body.subtotal is not None else inv.subtotal
        tax = money(body.tax_total) if body.tax_total is not None else inv.tax_total
        tot = money(body.total) if body.total is not None else inv.total
        issues = validate_header_totals(sub, tax, tot)
        if issues:
            raise ApiError(
                status_code=422,
                code="total_mismatch",
                message="subtotal + tax_total must equal total",
                details={"issues": issues},
            )
        inv.subtotal = sub
        inv.tax_total = tax
        inv.total = tot
        inv.balance_due = money(tot - inv.amount_paid)

    duplicates = find_duplicate_invoices(
        db,
        organization_id=user.organization_id,
        supplier_id=inv.supplier_id,
        invoice_number=inv.invoice_number,
        exclude_invoice_id=inv.id,
    )
    inv.has_duplicate_warning = len(duplicates) > 0
    for other in duplicates:
        other.has_duplicate_warning = True

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="update",
        details={"fields": list(data.keys()), "has_duplicate_warning": inv.has_duplicate_warning},
    )
    db.commit()
    inv = _get_org_invoice(db, user, inv.id)
    return _invoice_out(inv)


@router.delete(
    "/{invoice_id}",
    response_model=InvoiceOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def archive_invoice(
    invoice_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceOut:
    inv = _get_org_invoice(db, user, invoice_id)
    inv.archived = True
    inv.status = InvoiceStatus.ARCHIVED
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action="archive",
    )
    db.commit()
    inv = _get_org_invoice(db, user, inv.id)
    return _invoice_out(inv)


@router.post(
    "/{invoice_id}/workflow",
    response_model=InvoiceOut,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN, UserRole.STAFF, UserRole.REVIEWER, UserRole.APPROVER
            )
        )
    ],
)
def invoice_workflow(
    invoice_id: UUID,
    body: InvoiceWorkflowAction,
    user: CurrentUser,
    db: DbSession,
) -> InvoiceOut:
    inv = _get_org_invoice(db, user, invoice_id)
    action = body.action.strip().lower()

    if action == "submit_review":
        if inv.status not in {InvoiceStatus.UPLOADED, InvoiceStatus.PROCESSING, InvoiceStatus.REJECTED}:
            raise ApiError(
                status_code=409,
                code="invalid_transition",
                message=f"Cannot submit for review from {inv.status.value}",
            )
        inv.status = InvoiceStatus.NEEDS_REVIEW
    elif action == "submit_approval":
        if user.role not in {UserRole.ADMIN, UserRole.REVIEWER}:
            raise ApiError(
                status_code=403,
                code="forbidden",
                message="Only reviewer or admin can submit for approval",
            )
        if inv.status not in {InvoiceStatus.NEEDS_REVIEW, InvoiceStatus.UPLOADED}:
            raise ApiError(
                status_code=409,
                code="invalid_transition",
                message=f"Cannot submit for approval from {inv.status.value}",
            )
        if inv.has_duplicate_warning:
            # Still allow but keep flag — review signal, not hard block
            pass
        issues = validate_header_totals(inv.subtotal, inv.tax_total, inv.total)
        if issues:
            raise ApiError(
                status_code=422,
                code="total_mismatch",
                message="Fix totals before submitting for approval",
                details={"issues": issues},
            )
        inv.status = InvoiceStatus.PENDING_APPROVAL
    else:
        raise ApiError(
            status_code=422,
            code="invalid_action",
            message="action must be submit_review or submit_approval",
        )

    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice",
        entity_id=inv.id,
        action=f"workflow_{action}",
        details={"status": inv.status.value, "notes": body.notes},
    )
    db.commit()
    inv = _get_org_invoice(db, user, inv.id)
    return _invoice_out(inv)


@lines_router.api_route("", methods=["GET", "POST"])
@lines_router.api_route("/{line_id}", methods=["GET", "PATCH", "DELETE"])
async def invoice_lines_stub(line_id: str | None = None) -> JSONResponse:
    # Lines are managed via invoice create/update in M2
    return coming_soon("standalone invoice-lines (use /invoices with nested lines)")
