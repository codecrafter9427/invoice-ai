"""Invoices API — M1 org-scoped list; mutations Coming Soon."""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import coming_soon
from app.models import Invoice
from app.schemas.common import InvoiceListItem, InvoiceListResponse

router = APIRouter()
lines_router = APIRouter()


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> InvoiceListResponse:
    """Org-scoped invoice list for demo + tenant smoke tests."""
    base = select(Invoice).where(
        Invoice.organization_id == user.organization_id,
        Invoice.archived.is_(False),
    )
    total = (
        db.scalar(
            select(func.count()).select_from(Invoice).where(
                Invoice.organization_id == user.organization_id,
                Invoice.archived.is_(False),
            )
        )
        or 0
    )
    rows = db.scalars(
        base.order_by(Invoice.invoice_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return InvoiceListResponse(
        items=[
            InvoiceListItem(
                id=inv.id,
                invoice_number=inv.invoice_number,
                supplier_id=inv.supplier_id,
                status=inv.status.value,
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


@router.api_route("", methods=["POST"])
@router.api_route("/{invoice_id}", methods=["GET", "PATCH", "DELETE"])
async def invoices_mutations_stub(invoice_id: str | None = None) -> JSONResponse:
    return coming_soon("invoices mutations")


@lines_router.api_route("", methods=["GET", "POST"])
@lines_router.api_route("/{line_id}", methods=["GET", "PATCH", "DELETE"])
async def invoice_lines_stub(line_id: str | None = None) -> JSONResponse:
    return coming_soon("invoice-lines")
