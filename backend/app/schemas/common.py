"""Shared response schemas."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "invoice-ai"
    version: str = "0.1.0-m1"


class ComingSoonResponse(BaseModel):
    status: str = "coming_soon"
    message: str
    group: str


class DemoLoginRequest(BaseModel):
    email: str
    password: str


class DemoLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str
    organization_id: UUID
    organization_name: str
    user_id: UUID
    demo: bool = True
    message: str = "Demo JWT session — prototype auth only"


class MeResponse(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: str
    organization_id: UUID
    organization_name: str
    demo: bool = True


class AIRequest(BaseModel):
    """Baseline AI request shape — product schemas will be stricter later."""

    input: dict[str, Any] = Field(default_factory=dict)
    context_ids: list[str] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class AISource(BaseModel):
    type: str
    id: str
    label: str


class AIResponse(BaseModel):
    result: dict[str, Any]
    explanation: str
    sources: list[AISource] = Field(default_factory=list)
    requires_confirmation: bool = True


class SupplierListItem(BaseModel):
    id: UUID
    code: str
    name: str
    email: str | None = None
    organization_id: UUID


class SupplierListResponse(BaseModel):
    items: list[SupplierListItem]
    total: int
    page: int = 1
    page_size: int = 50


class InvoiceListItem(BaseModel):
    id: UUID
    invoice_number: str
    supplier_id: UUID
    status: str
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
