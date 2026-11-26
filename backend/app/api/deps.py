"""FastAPI dependencies: DB session, current user, org scoping."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.models import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise ApiError(
            status_code=401,
            code="unauthorized",
            message="Authentication required",
        )
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = UUID(payload["sub"])
        org_id = UUID(payload["org_id"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise ApiError(
            status_code=401,
            code="invalid_token",
            message="Invalid or expired access token",
        ) from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise ApiError(
            status_code=401,
            code="unauthorized",
            message="User not found or inactive",
        )
    if user.organization_id != org_id:
        raise ApiError(
            status_code=403,
            code="tenant_mismatch",
            message="Token organization does not match user",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    allowed = set(roles)

    def _checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise ApiError(
                status_code=403,
                code="forbidden",
                message="Insufficient role for this action",
                details={"role": user.role.value, "allowed": [r.value for r in allowed]},
            )
        return user

    return _checker


def assert_same_org(user: User, organization_id: UUID) -> None:
    if user.organization_id != organization_id:
        raise ApiError(
            status_code=403,
            code="tenant_forbidden",
            message="Resource belongs to another organization",
        )
