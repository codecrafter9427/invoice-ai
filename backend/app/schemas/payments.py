"""Payment request/response schemas."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    invoice_id: UUID
    amount: Decimal = Field(gt=0)
    payment_date: date
    method: str = Field(default="ach", description="ach|wire|check|card|other")
    reference: str | None = Field(default=None, max_length=200)


class PaymentOut(BaseModel):
    id: UUID
    organization_id: UUID
    invoice_id: UUID
    amount: str
    payment_date: date
    method: str
    reference: str | None
    recorded_by_id: UUID | None
    created_at: datetime
    invoice_status: str | None = None
    invoice_balance_due: str | None = None
    invoice_amount_paid: str | None = None

    model_config = {"from_attributes": True}


class PaymentListResponse(BaseModel):
    items: list[PaymentOut]
    total: int
    page: int = 1
    page_size: int = 50
