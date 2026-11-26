"""Accounting category suggestion heuristics — user must confirm."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AccountingCategory

# Keyword → category code (seed codes)
_KEYWORD_MAP: list[tuple[str, str]] = [
    ("paper", "OFFICE"),
    ("stationery", "OFFICE"),
    ("office", "OFFICE"),
    ("card", "OFFICE"),
    ("electric", "UTIL"),
    ("utility", "UTIL"),
    ("water", "UTIL"),
    ("telecom", "UTIL"),
    ("power", "UTIL"),
    ("license", "SOFT"),
    ("software", "SOFT"),
    ("saas", "SOFT"),
    ("hosting", "SOFT"),
    ("cloud", "SOFT"),
    ("freight", "LOGISTICS"),
    ("shipping", "LOGISTICS"),
    ("logistics", "LOGISTICS"),
    ("box", "LOGISTICS"),
    ("packaging", "LOGISTICS"),
]


def suggest_category(
    db: Session,
    *,
    organization_id: UUID,
    description: str,
    line_descriptions: list[str] | None = None,
) -> dict[str, Any]:
    """Suggest a category from org catalog using keyword heuristics."""
    cats = list(
        db.scalars(
            select(AccountingCategory).where(
                AccountingCategory.organization_id == organization_id
            )
        ).all()
    )
    by_code = {c.code.upper(): c for c in cats}
    text = " ".join(
        [description or ""] + list(line_descriptions or [])
    ).lower()

    matched_code: str | None = None
    matched_keyword: str | None = None
    for keyword, code in _KEYWORD_MAP:
        if keyword in text and code in by_code:
            matched_code = code
            matched_keyword = keyword
            break

    candidates: list[dict[str, Any]] = []
    for c in cats:
        score = 0.2
        if matched_code and c.code.upper() == matched_code:
            score = 0.82
        elif c.name.lower() in text or c.code.lower() in text:
            score = 0.55
        candidates.append(
            {
                "id": str(c.id),
                "code": c.code,
                "name": c.name,
                "score": score,
            }
        )
    candidates.sort(key=lambda x: x["score"], reverse=True)

    suggested = None
    if matched_code and matched_code in by_code:
        c = by_code[matched_code]
        suggested = {
            "id": str(c.id),
            "code": c.code,
            "name": c.name,
            "matched_keyword": matched_keyword,
        }
    elif candidates:
        top = candidates[0]
        if top["score"] >= 0.55:
            suggested = {
                "id": top["id"],
                "code": top["code"],
                "name": top["name"],
                "matched_keyword": None,
            }

    return {
        "suggested_category": suggested,
        "candidates": candidates[:5],
        "requires_confirmation": True,
        "note": "Category is a suggestion only — user must confirm before save.",
    }
