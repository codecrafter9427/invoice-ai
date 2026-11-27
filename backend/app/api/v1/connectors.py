"""Read-only Business Insights connector (versioned).

Auth: Authorization Bearer <org JWT> OR Bearer matching INSIGHTS_CONNECTOR_TOKEN
(with X-Organization-Id / organization_id when using the shared token).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import DbSession, get_current_user
from app.core.config import get_settings
from app.core.errors import ApiError
from app.models import Organization, User
from app.services.reports import (
    aging_report,
    payables_summary,
    supplier_spend_report,
)

router = APIRouter()
_bearer = HTTPBearer(auto_error=False)

APP_VERSION = "0.6.0-m6"


def _resolve_org_id(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
    organization_id: UUID | None = Query(None),
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> UUID:
    settings = get_settings()
    token = credentials.credentials if credentials else None
    connector_token = (settings.insights_connector_token or "").strip()

    if token and connector_token and token == connector_token:
        raw = x_organization_id or (str(organization_id) if organization_id else None)
        if not raw:
            raise ApiError(
                status_code=400,
                code="organization_required",
                message=(
                    "When using INSIGHTS_CONNECTOR_TOKEN, pass organization_id "
                    "query or X-Organization-Id header"
                ),
            )
        try:
            org_id = UUID(str(raw))
        except ValueError as exc:
            raise ApiError(
                status_code=422,
                code="invalid_organization_id",
                message="organization_id must be a UUID",
            ) from exc
        org = db.get(Organization, org_id)
        if org is None or not org.is_active:
            raise ApiError(
                status_code=404,
                code="org_not_found",
                message="Organization not found",
            )
        return org_id

    # Fall through to JWT
    user: User = get_current_user(db, credentials)
    return user.organization_id


ConnectorOrgId = Annotated[UUID, Depends(_resolve_org_id)]


@router.get("/health")
def insights_health() -> dict:
    return {
        "status": "ok",
        "product": "invoice-ai",
        "api_version": "v1",
        "app_version": APP_VERSION,
        "read_only": True,
    }


@router.get("/meta")
def insights_meta() -> dict:
    return {
        "product": "invoice-ai",
        "api_version": "v1",
        "app_version": APP_VERSION,
        "currency_default": "USD",
        "metrics": [
            "outstanding_balance",
            "paid_this_month",
            "aging_totals",
            "supplier_spend",
        ],
        "auth": [
            "Bearer JWT (org-scoped)",
            "Bearer INSIGHTS_CONNECTOR_TOKEN + X-Organization-Id",
        ],
    }


@router.get("/payables/summary")
def insights_payables_summary(
    db: DbSession,
    org_id: ConnectorOrgId,
    as_of: date | None = None,
) -> dict:
    return payables_summary(db, organization_id=org_id, as_of=as_of)


@router.get("/payables/aging")
def insights_payables_aging(
    db: DbSession,
    org_id: ConnectorOrgId,
    as_of: date | None = None,
) -> dict:
    return aging_report(db, organization_id=org_id, as_of=as_of)


@router.get("/payables/supplier-spend")
def insights_supplier_spend(
    db: DbSession,
    org_id: ConnectorOrgId,
    as_of: date | None = None,
) -> dict:
    return supplier_spend_report(db, organization_id=org_id, as_of=as_of)
