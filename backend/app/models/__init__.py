"""SQLAlchemy models — placeholders only (Milestone 2).

Planned entities:
Organization, User, Supplier, Invoice, InvoiceLine, InvoiceDocument,
InvoiceReview, ApprovalStep, Payment, PurchaseOrderReference,
AccountingCategory, AuditEvent.
"""

from app.core.db import Base

__all__ = ["Base"]
