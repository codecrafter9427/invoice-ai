"""Domain enums for Invoice AI."""

import enum


class UserRole(str, enum.Enum):
    """Admin/Finance Manager, Reviewer, Approver, Staff."""

    ADMIN = "admin"  # Admin / Finance Manager
    REVIEWER = "reviewer"
    APPROVER = "approver"
    STAFF = "staff"


class InvoiceStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    ARCHIVED = "archived"


class ApprovalDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentMethod(str, enum.Enum):
    ACH = "ach"
    WIRE = "wire"
    CHECK = "check"
    CARD = "card"
    OTHER = "other"


class ReviewFlag(str, enum.Enum):
    NONE = "none"
    MISSING_FIELDS = "missing_fields"
    TOTAL_MISMATCH = "total_mismatch"
    DUPLICATE = "duplicate"
    ANOMALY = "anomaly"
    OTHER = "other"
