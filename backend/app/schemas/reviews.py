"""Invoice review schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InvoiceReviewCreate(BaseModel):
    invoice_id: UUID
    flag: str = Field(default="none", description="ReviewFlag value")
    notes: str | None = None


class InvoiceReviewUpdate(BaseModel):
    flag: str | None = None
    notes: str | None = None
    is_resolved: bool | None = None


class InvoiceReviewOut(BaseModel):
    id: UUID
    organization_id: UUID
    invoice_id: UUID
    invoice_number: str | None = None
    invoice_status: str | None = None
    reviewer_id: UUID | None = None
    flag: str
    notes: str | None
    is_resolved: bool
    created_at: datetime
    updated_at: datetime
    has_duplicate_warning: bool | None = None
    has_anomaly_signal: bool | None = None

    model_config = {"from_attributes": True}


class InvoiceReviewListResponse(BaseModel):
    items: list[InvoiceReviewOut]
    total: int


class ReviewQueueItem(BaseModel):
    invoice_id: UUID
    invoice_number: str
    supplier_id: UUID
    supplier_name: str | None = None
    status: str
    total: str
    balance_due: str
    currency: str
    has_duplicate_warning: bool
    has_anomaly_signal: bool
    unresolved_review_count: int = 0
    latest_flag: str | None = None
    latest_notes: str | None = None


class ReviewQueueResponse(BaseModel):
    items: list[ReviewQueueItem]
    total: int
