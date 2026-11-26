"""Audit event helpers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record_audit(
    db: Session,
    *,
    organization_id: UUID,
    actor_id: UUID | None,
    entity_type: str,
    entity_id: UUID | None,
    action: str,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        actor_id=actor_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details=details,
    )
    db.add(event)
    return event
