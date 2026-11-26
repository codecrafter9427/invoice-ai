"""Suppliers API — M1 org-scoped list; mutations Coming Soon."""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import coming_soon
from app.models import Supplier
from app.schemas.common import SupplierListItem, SupplierListResponse

router = APIRouter()


@router.get("", response_model=SupplierListResponse)
def list_suppliers(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = None,
) -> SupplierListResponse:
    """Org-scoped supplier list for demo + tenant smoke tests."""
    q = select(Supplier).where(
        Supplier.organization_id == user.organization_id,
        Supplier.archived.is_(False),
    )
    count_q = select(func.count()).select_from(Supplier).where(
        Supplier.organization_id == user.organization_id,
        Supplier.archived.is_(False),
    )
    if search:
        like = f"%{search.strip()}%"
        q = q.where(Supplier.name.ilike(like) | Supplier.code.ilike(like))
        count_q = count_q.where(
            Supplier.name.ilike(like) | Supplier.code.ilike(like)
        )
    total = db.scalar(count_q) or 0
    rows = db.scalars(
        q.order_by(Supplier.name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return SupplierListResponse(
        items=[
            SupplierListItem(
                id=s.id,
                code=s.code,
                name=s.name,
                email=s.email,
                organization_id=s.organization_id,
            )
            for s in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.api_route("", methods=["POST"])
@router.api_route("/{supplier_id}", methods=["GET", "PATCH", "DELETE"])
async def suppliers_mutations_stub(supplier_id: str | None = None) -> JSONResponse:
    return coming_soon("suppliers mutations")
