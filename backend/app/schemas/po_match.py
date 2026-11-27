"""PO match request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class PoMatchConfirm(BaseModel):
    purchase_order_reference_id: UUID
    confirmed: bool = Field(
        ...,
        description="Must be true — PO matches are never auto-applied",
    )
