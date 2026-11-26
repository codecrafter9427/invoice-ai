"""Shared API error shape: {error:{code,message,details}}."""

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse


def error_body(
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def coming_soon(feature: str) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content=error_body(
            code="coming_soon",
            message=f"{feature} is Coming Soon",
            details={"feature": feature},
        ),
    )


class ApiError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=error_body(code, message, details),
        )
