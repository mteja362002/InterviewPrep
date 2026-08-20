"""CompanyContext — the normalized company-intelligence bundle the adaptive
planning pipeline can consult.

Phase 2A (architectural integration only):
    This layer BRIDGES the Phase 1 Company Intelligence runtime (the compiled
    artifacts served by ``company_intelligence.loader``) to the Adaptive
    Planner's context bundle (:class:`LearnerContext`). It does NOT make the
    planner company-aware — no scoring, ranking, unlock, or readiness code
    reads it yet. It simply makes normalized company data available to travel
    alongside the planner state for future phases.

Design contract (mirrors LearnerContext):
    * PURE data. Never touches Mongo. Reads ONLY compiled runtime artifacts via
      the Company Runtime Loader. NEVER parses markdown.
    * NO hardcoded company ids, no roadmap company mappings, no frontend lists,
      no mission-engine constants. Everything comes through the loader.
    * DEFENSIVE. Building a CompanyContext can never raise and never changes
      planner behavior: unknown / UI-only ids (e.g. ``others``) are skipped,
      an empty selection yields an empty context.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from company_intelligence.loader import company_intelligence as _default_loader


@dataclass
class CompanyProfileContext:
    """Normalized, read-only runtime view of ONE compiled company profile.

    Every field is derived from the compiled JSON artifact (Phase 1). The raw
    editorial ``sections`` markdown text is deliberately NOT included — this is
    normalized runtime data only.
    """

    company_id: str
    metadata: dict = field(default_factory=dict)
    subjects: dict = field(default_factory=dict)          # subject importance
    signals: list = field(default_factory=list)           # evaluation + behavioral signals
    levels: dict = field(default_factory=dict)            # role / level differences
    planner: dict = field(default_factory=dict)           # philosophy / priority / adaptive biases
    trends: dict = field(default_factory=dict)
    profile_version: Optional[str] = None
    summary_variant: Optional[str] = None

    # -- convenience accessors (normalized planner metadata) ------------------
    @property
    def confidence(self) -> Optional[str]:
        """Overall evidence confidence for the profile."""
        return self.metadata.get("confidence")

    @property
    def philosophy(self) -> list:
        """Engineering / interview philosophy (normalized list)."""
        val = self.planner.get("philosophy")
        return list(val) if isinstance(val, list) else []

    @property
    def priority_hierarchy(self) -> list:
        """Planning priority hierarchy (guidance only)."""
        val = self.planner.get("priority")
        return list(val) if isinstance(val, list) else []

    @property
    def adaptive_biases(self) -> dict:
        """Adaptive bias guidance (guidance only)."""
        val = self.planner.get("adaptive")
        return dict(val) if isinstance(val, dict) else {}


@dataclass
class CompanyContext:
    """Aggregate normalized company intelligence for a learner's selection.

    ``profiles`` only contains companies that resolved to a compiled artifact.
    ``unknown_company_ids`` records selected ids with no compiled profile
    (e.g. the UI-only ``others`` pseudo-company, or a typo) so future phases can
    surface / warn without the planner ever branching on a hardcoded id.
    """

    selected_company_ids: List[str] = field(default_factory=list)
    profiles: Dict[str, CompanyProfileContext] = field(default_factory=dict)
    unknown_company_ids: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.profiles

    def known_ids(self) -> List[str]:
        return list(self.profiles.keys())

    def get(self, company_id: str) -> Optional[CompanyProfileContext]:
        return self.profiles.get(company_id)

    def __iter__(self):
        return iter(self.profiles.values())


def _normalize_ids(company_ids: Optional[Iterable[str]]) -> List[str]:
    """Lower-case, trim, drop blanks, de-duplicate while preserving order."""
    ordered: List[str] = []
    seen = set()
    for raw in company_ids or []:
        cid = str(raw).strip().lower()
        if cid and cid not in seen:
            seen.add(cid)
            ordered.append(cid)
    return ordered


def build_company_context(
    company_ids: Optional[Iterable[str]] = None,
    *,
    loader=None,
) -> CompanyContext:
    """Assemble a CompanyContext from a list of selected company ids.

    Uses the Company Runtime Loader (compiled artifacts) exclusively. Never
    raises: any loader/artifact problem for a single company degrades to
    marking that id unknown, so the planner's behavior is never affected.
    """
    loader = loader or _default_loader
    ordered = _normalize_ids(company_ids)

    profiles: Dict[str, CompanyProfileContext] = {}
    unknown: List[str] = []

    for cid in ordered:
        artifact = None
        try:
            artifact = loader.get_company(cid)
        except Exception:  # pragma: no cover - defensive; must never break planner
            artifact = None
        if not artifact:
            unknown.append(cid)
            continue
        profiles[cid] = CompanyProfileContext(
            company_id=cid,
            metadata=dict(artifact.get("metadata", {})),
            subjects=dict(artifact.get("subjects", {})),
            signals=list(artifact.get("signals", [])),
            levels=dict(artifact.get("levels", {})),
            planner=dict(artifact.get("planner", {})),
            trends=dict(artifact.get("trends", {})),
            profile_version=artifact.get("profile_version"),
            summary_variant=artifact.get("summary_variant"),
        )

    return CompanyContext(
        selected_company_ids=ordered,
        profiles=profiles,
        unknown_company_ids=unknown,
    )
