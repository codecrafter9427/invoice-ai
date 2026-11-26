"""Approval request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ApprovalDecide(BaseModel):
    decision: str = Field(description="approved | rejected")
    comment: str | None = Field(default=None, max_length=2000)


class ApprovalStepOut(BaseModel):
    id: UUID
    invoice_id: UUID
    step_order: int
    approver_id: UUID | None
    decision: str
    comment: str | None
    decided_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalListResponse(BaseModel):
    items: list[ApprovalStepOut]
    total: int
