"""Supplier request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    payment_details: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class SupplierUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    email: str | None = None
    phone: str | None = None
    payment_details: str | None = None
    is_active: bool | None = None


class SupplierOut(BaseModel):
    id: UUID
    organization_id: UUID
    code: str
    name: str
    email: str | None = None
    phone: str | None = None
    payment_details: str | None = None
    is_active: bool
    archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierListResponse(BaseModel):
    items: list[SupplierOut]
    total: int
    page: int = 1
    page_size: int = 50
