"""Suppliers CRUD — organization-scoped."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.errors import ApiError
from app.models import Supplier, User, UserRole
from app.schemas.suppliers import (
    SupplierCreate,
    SupplierListResponse,
    SupplierOut,
    SupplierUpdate,
)
from app.services.audit import record_audit

router = APIRouter()


def _get_org_supplier(db: DbSession, user: User, supplier_id: UUID) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None or supplier.archived:
        raise ApiError(status_code=404, code="not_found", message="Supplier not found")
    if supplier.organization_id != user.organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
    return supplier


@router.get("", response_model=SupplierListResponse)
def list_suppliers(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: str | None = None,
) -> SupplierListResponse:
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
        items=[SupplierOut.model_validate(s) for s in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "",
    response_model=SupplierOut,
    status_code=201,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def create_supplier(
    body: SupplierCreate,
    user: CurrentUser,
    db: DbSession,
) -> SupplierOut:
    code = body.code.strip()
    existing = db.scalar(
        select(Supplier).where(
            Supplier.organization_id == user.organization_id,
            Supplier.code == code,
            Supplier.archived.is_(False),
        )
    )
    if existing is not None:
        raise ApiError(
            status_code=409,
            code="duplicate_supplier_code",
            message="Supplier code already exists in this organization",
        )
    supplier = Supplier(
        organization_id=user.organization_id,
        code=code,
        name=body.name.strip(),
        email=body.email.strip() if body.email else None,
        phone=body.phone,
        payment_details=body.payment_details,
        is_active=body.is_active,
    )
    db.add(supplier)
    try:
        db.flush()
    except IntegrityError as exc:
        raise ApiError(
            status_code=409,
            code="duplicate_supplier_code",
            message="Supplier code already exists in this organization",
        ) from exc
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="supplier",
        entity_id=supplier.id,
        action="create",
        details={"code": supplier.code, "name": supplier.name},
    )
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> SupplierOut:
    return SupplierOut.model_validate(_get_org_supplier(db, user, supplier_id))


@router.patch(
    "/{supplier_id}",
    response_model=SupplierOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def update_supplier(
    supplier_id: UUID,
    body: SupplierUpdate,
    user: CurrentUser,
    db: DbSession,
) -> SupplierOut:
    supplier = _get_org_supplier(db, user, supplier_id)
    data = body.model_dump(exclude_unset=True)
    if "code" in data and data["code"] is not None:
        data["code"] = data["code"].strip()
    if "name" in data and data["name"] is not None:
        data["name"] = data["name"].strip()
    if "email" in data and data["email"]:
        data["email"] = data["email"].strip()
    for key, value in data.items():
        setattr(supplier, key, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(
            status_code=409,
            code="duplicate_supplier_code",
            message="Supplier code already exists in this organization",
        ) from exc
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="supplier",
        entity_id=supplier.id,
        action="update",
        details=data,
    )
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)


@router.delete(
    "/{supplier_id}",
    response_model=SupplierOut,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def archive_supplier(
    supplier_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> SupplierOut:
    supplier = _get_org_supplier(db, user, supplier_id)
    supplier.archived = True
    supplier.is_active = False
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="supplier",
        entity_id=supplier.id,
        action="archive",
    )
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier)
