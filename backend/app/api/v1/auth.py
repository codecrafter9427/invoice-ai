"""Demo login with JWT + org-scoped identity (prototype, not production)."""

from fastapi import APIRouter, Request

from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.rate_limit import check_rate_limit
from app.core.security import create_access_token, verify_password
from app.models import Organization, User
from app.schemas.common import DemoLoginRequest, DemoLoginResponse, MeResponse

router = APIRouter()


@router.post("/demo-login", response_model=DemoLoginResponse)
def demo_login(
    body: DemoLoginRequest, db: DbSession, request: Request
) -> DemoLoginResponse:
    settings = get_settings()
    if settings.is_production:
        raise ApiError(
            status_code=403,
            code="demo_login_disabled",
            message="Demo login is disabled when APP_ENV=production",
        )

    client_host = request.client.host if request.client else "unknown"
    check_rate_limit(
        f"auth:demo-login:{client_host}",
        limit=settings.auth_rate_limit,
        window_seconds=settings.auth_rate_window_seconds,
        message="Too many login attempts — try again shortly",
    )

    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None or not verify_password(body.password, user.hashed_password):
        raise ApiError(
            status_code=401,
            code="invalid_credentials",
            message="Invalid demo credentials",
        )
    org = db.get(Organization, user.organization_id)
    if org is None or not org.is_active:
        raise ApiError(
            status_code=403,
            code="org_inactive",
            message="Organization is inactive",
        )
    token, expires_in = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        role=user.role.value,
    )
    return DemoLoginResponse(
        access_token=token,
        expires_in=expires_in,
        email=user.email,
        role=user.role.value,
        organization_id=user.organization_id,
        organization_name=org.name,
        user_id=user.id,
    )


@router.post("/refresh", response_model=DemoLoginResponse)
def refresh_token(user: CurrentUser, db: DbSession) -> DemoLoginResponse:
    """Issue a new access token from a still-valid access JWT (sliding session)."""
    org = db.get(Organization, user.organization_id)
    if org is None or not org.is_active:
        raise ApiError(
            status_code=403,
            code="org_inactive",
            message="Organization is inactive",
        )
    token, expires_in = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        role=user.role.value,
    )
    return DemoLoginResponse(
        access_token=token,
        expires_in=expires_in,
        email=user.email,
        role=user.role.value,
        organization_id=user.organization_id,
        organization_name=org.name,
        user_id=user.id,
        message="Access token refreshed — prototype sliding session only",
    )


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, db: DbSession) -> MeResponse:
    org = db.get(Organization, user.organization_id)
    return MeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        organization_id=user.organization_id,
        organization_name=org.name if org else "",
    )
