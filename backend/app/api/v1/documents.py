"""Invoice document metadata — local path registration only (no OCR SaaS)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ApiError
from app.models import Invoice, InvoiceDocument
from app.services.audit import record_audit

router = APIRouter()


class DocumentCreate(BaseModel):
    invoice_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(default="application/pdf", max_length=100)
    storage_path: str = Field(min_length=1, max_length=500)
    byte_size: int = Field(default=0, ge=0)
    ocr_text: str | None = None  # optional pasted text — not from paid OCR


class DocumentOut(BaseModel):
    id: UUID
    invoice_id: UUID
    filename: str
    content_type: str
    storage_path: str
    byte_size: int
    has_ocr_text: bool
    organization_id: UUID


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int = 1
    page_size: int = 50


def _out(doc: InvoiceDocument) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        invoice_id=doc.invoice_id,
        filename=doc.filename,
        content_type=doc.content_type,
        storage_path=doc.storage_path,
        byte_size=doc.byte_size,
        has_ocr_text=bool(doc.ocr_text),
        organization_id=doc.organization_id,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    user: CurrentUser,
    db: DbSession,
    invoice_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> DocumentListResponse:
    filters = [InvoiceDocument.organization_id == user.organization_id]
    if invoice_id is not None:
        filters.append(InvoiceDocument.invoice_id == invoice_id)
    total = (
        db.scalar(select(func.count()).select_from(InvoiceDocument).where(*filters))
        or 0
    )
    rows = list(
        db.scalars(
            select(InvoiceDocument)
            .where(*filters)
            .order_by(InvoiceDocument.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return DocumentListResponse(
        items=[_out(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=DocumentOut, status_code=201)
def register_document(
    body: DocumentCreate,
    user: CurrentUser,
    db: DbSession,
) -> DocumentOut:
    """Register document metadata (local/demo path). No paid OCR upload."""
    inv = db.scalar(
        select(Invoice).where(
            Invoice.id == body.invoice_id,
            Invoice.organization_id == user.organization_id,
            Invoice.archived.is_(False),
        )
    )
    if inv is None:
        raise ApiError(
            status_code=404,
            code="invoice_not_found",
            message="Invoice not found in your organization",
        )
    doc = InvoiceDocument(
        organization_id=user.organization_id,
        invoice_id=body.invoice_id,
        filename=body.filename.strip(),
        content_type=body.content_type,
        storage_path=body.storage_path.strip(),
        byte_size=body.byte_size,
        ocr_text=body.ocr_text,
    )
    db.add(doc)
    db.flush()
    record_audit(
        db,
        organization_id=user.organization_id,
        actor_id=user.id,
        entity_type="invoice_document",
        entity_id=doc.id,
        action="register_metadata",
        details={"invoice_id": str(inv.id), "filename": doc.filename},
    )
    db.commit()
    db.refresh(doc)
    return _out(doc)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> DocumentOut:
    doc = db.scalar(
        select(InvoiceDocument).where(
            InvoiceDocument.id == document_id,
            InvoiceDocument.organization_id == user.organization_id,
        )
    )
    if doc is None:
        raise ApiError(
            status_code=404,
            code="document_not_found",
            message="Document not found",
        )
    return _out(doc)
