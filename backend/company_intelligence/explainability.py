"""Company Weight Engine — explainability.

Turns the per-company contribution audit trail produced by
``scoring.compute_company_intelligence_signal`` into human-readable reasons and
a structured payload. Every Company Intelligence contribution is transparent:
which company, which subject, what importance, and at what confidence.
"""
from __future__ import annotations

from typing import List, Optional


def summarize_contributions(contributions: Optional[List[dict]]) -> dict:
    """Return a structured explainability payload for a node's CI signal."""
    contributions = contributions or []
    if not contributions:
        return {"companies": [], "reasons": [], "confidence": None, "top_company": None}

    top = max(contributions, key=lambda c: c.get("contribution", 0.0))
    reasons = build_reasons(contributions)
    # Lowest confidence across companies is the honest confidence to expose
    # (never inflate uncertain evidence into a mandatory-looking signal).
    confidences = [c.get("confidence") for c in contributions if c.get("confidence")]
    return {
        "companies": contributions,
        "reasons": reasons,
        "confidence": _lowest_confidence(confidences),
        "top_company": top.get("company_id"),
    }


_CONFIDENCE_ORDER = ["high", "medium-high", "medium", "medium-low", "low-medium", "low"]


def _lowest_confidence(labels: List[str]) -> Optional[str]:
    if not labels:
        return None
    def rank(lbl: str) -> int:
        try:
            return _CONFIDENCE_ORDER.index(str(lbl).strip().lower())
        except ValueError:
            return 2  # treat unknown as ~medium
    return max(labels, key=rank)


def build_reasons(contributions: List[dict]) -> List[str]:
    """Human-readable bullets, one per company, ordered by contribution."""
    reasons: List[str] = []
    for c in sorted(contributions, key=lambda x: x.get("contribution", 0.0), reverse=True):
        company = str(c.get("company_id", "")).replace("_", " ").title()
        subject = str(c.get("subject", "")).replace("_", " ").title()
        importance = c.get("importance") or "Medium"
        confidence = c.get("confidence") or "Medium"
        reasons.append(
            f"{importance} importance for {company} ({subject}, {confidence} confidence)"
        )
    return reasons
