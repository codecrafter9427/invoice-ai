"""Shared response schemas."""

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "invoice-ai"
    version: str = "0.1.0-scaffold"


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
    role: str = "admin"
    demo: bool = True
    message: str = "Demo login placeholder — not a real session"


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
