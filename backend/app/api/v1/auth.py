"""Demo login placeholder — not production auth."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.errors import ApiError
from app.schemas.common import DemoLoginRequest, DemoLoginResponse

router = APIRouter()


@router.post("/demo-login", response_model=DemoLoginResponse)
async def demo_login(body: DemoLoginRequest) -> DemoLoginResponse:
    settings = get_settings()
    if (
        body.email != settings.demo_user_email
        or body.password != settings.demo_user_password
    ):
        raise ApiError(
            status_code=401,
            code="invalid_credentials",
            message="Invalid demo credentials",
        )
    return DemoLoginResponse(
        access_token="demo-placeholder-token",
        email=body.email,
        role="admin",
    )


@router.get("/me")
async def me() -> dict:
    settings = get_settings()
    return {
        "email": settings.demo_user_email,
        "role": "admin",
        "demo": True,
        "message": "Demo identity placeholder — wire JWT/session in Milestone 1+",
    }
