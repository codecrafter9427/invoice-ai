"""Admin audit event list (org-scoped)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, require_roles
from app.models import AuditEvent, UserRole

router = APIRouter()


@router.get(
    "",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
def list_audit_events(
    user: CurrentUser,
    db: DbSession,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    filters = [AuditEvent.organization_id == user.organization_id]
    if action:
        filters.append(AuditEvent.action == action)
    if entity_type:
        filters.append(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        filters.append(AuditEvent.entity_id == entity_id)

    total = (
        db.scalar(select(func.count()).select_from(AuditEvent).where(*filters)) or 0
    )
    rows = list(
        db.scalars(
            select(AuditEvent)
            .where(*filters)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        ).all()
    )
    return {
        "items": [
            {
                "id": str(e.id),
                "organization_id": str(e.organization_id),
                "actor_id": str(e.actor_id) if e.actor_id else None,
                "entity_type": e.entity_type,
                "entity_id": str(e.entity_id) if e.entity_id else None,
                "action": e.action,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in rows
        ],
        "total": total,
    }
