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


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app

    return TestClient(app)
