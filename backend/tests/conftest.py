"""Pytest fixtures for Invoice AI smoke tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# Ensure settings load before app import
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://invoiceai:invoiceai_dev_password@localhost:5436/invoice_ai",
)
os.environ.setdefault("SECRET_KEY", "test-secret-key-invoice-ai-m1-32b")
os.environ.setdefault("APP_ENV", "test")
# High ceilings so the full suite does not trip in-memory auth/AI limiters
os.environ.setdefault("AUTH_RATE_LIMIT", "10000")
os.environ.setdefault("AI_RATE_LIMIT", "10000")


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.core.rate_limit import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.core.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    return TestClient(app)
