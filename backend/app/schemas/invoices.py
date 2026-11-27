"""Invoice request/response schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceLineIn(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0)


class InvoiceLineOut(BaseModel):
    id: UUID
    line_number: int
    description: str
    quantity: str
    unit_price: str
    tax_rate: str
    line_total: str

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    supplier_id: UUID
    invoice_number: str = Field(min_length=1, max_length=100)
    invoice_date: date
    due_date: date | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    po_reference: str | None = Field(default=None, max_length=100)
    terms: str | None = Field(default=None, max_length=200)
    lines: list[InvoiceLineIn] = Field(min_length=1)
    # Optional client-supplied totals — validated against computed if present
    subtotal: Decimal | None = None
    tax_total: Decimal | None = None
    total: Decimal | None = None
    submit_for_review: bool = False


class InvoiceUpdate(BaseModel):
    supplier_id: UUID | None = None
    invoice_number: str | None = Field(default=None, min_length=1, max_length=100)
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    po_reference: str | None = None
    terms: str | None = None
    lines: list[InvoiceLineIn] | None = None
    subtotal: Decimal | None = None
    tax_total: Decimal | None = None
    total: Decimal | None = None
    # Persist confirmed AI category suggestion (user must confirm in UI first)
    accounting_category_id: UUID | None = None
    category_confirmed: bool | None = None


class CategoryConfirm(BaseModel):
    """Confirm and persist a suggested accounting category."""

    accounting_category_id: UUID
    confirmed: bool = True


class InvoiceWorkflowAction(BaseModel):
    """Submit for review or pending approval."""

    action: str = Field(description="submit_review | submit_approval")
    notes: str | None = None


class DocumentPreviewOut(BaseModel):
    """Tight document metadata for invoice preview (no binary payload)."""

    id: UUID
    filename: str
    content_type: str
    storage_path: str
    byte_size: int
    has_ocr_text: bool
    ocr_char_count: int = 0
    ocr_text_preview: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InvoiceOut(BaseModel):
    id: UUID
    organization_id: UUID
    supplier_id: UUID
    invoice_number: str
    invoice_date: date
    due_date: date | None
    currency: str
    subtotal: str
    tax_total: str
    total: str
    amount_paid: str
    balance_due: str
    po_reference: str | None
    terms: str | None
    status: str
    accounting_category_id: UUID | None = None
    accounting_category_code: str | None = None
    accounting_category_name: str | None = None
    purchase_order_reference_id: UUID | None = None
    matched_po_number: str | None = None
    has_duplicate_warning: bool
    has_anomaly_signal: bool
    anomaly_notes: str | None
    archived: bool
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineOut] = Field(default_factory=list)
    validation_issues: list[str] = Field(default_factory=list)
    documents: list[DocumentPreviewOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class InvoiceListItem(BaseModel):
    id: UUID
    invoice_number: str
    supplier_id: UUID
    supplier_name: str | None = None
    status: str
    invoice_date: date | None = None
    total: str
    balance_due: str
    currency: str
    has_duplicate_warning: bool
    has_anomaly_signal: bool
    organization_id: UUID


class InvoiceListResponse(BaseModel):
    items: list[InvoiceListItem]
    total: int
    page: int = 1
    page_size: int = 50
