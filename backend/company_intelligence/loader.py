"""Runtime Company Intelligence loader service.

Consumes ONLY compiled JSON artifacts produced by compiler.py. This module
MUST NOT import or parse markdown. It is the single runtime entry point that
other subsystems (Planner, Company Readiness, AI Mentor, Analytics, Mock
Interviews) should use to read company intelligence.

Artifact layout (see scripts/compile_companies.py):
    compiled/index.json                 -> manifest (registry + version pointers)
    compiled/<company_id>/latest.json    -> latest compiled artifact (alias)
    compiled/<company_id>/v<version>.json-> immutable versioned artifact
"""
from __future__ import annotations

import copy
import json
import logging
import threading
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("company_intelligence.loader")

COMPILED_DIR = Path(__file__).resolve().parent / "compiled"
INDEX_PATH = COMPILED_DIR / "index.json"


class CompanyIntelligenceService:
    """Thread-safe, lazily-cached loader for compiled company artifacts."""

    def __init__(self, compiled_dir: Path = COMPILED_DIR):
        self._dir = compiled_dir
        self._lock = threading.Lock()
        self._index: Optional[dict] = None
        self._cache: Dict[str, dict] = {}
        self._loaded = False

    # -- internal -----------------------------------------------------------
    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._load()
            self._loaded = True

    def _load(self) -> None:
        index_path = self._dir / "index.json"
        if not index_path.exists():
            logger.warning(
                "Company Intelligence index not found at %s. "
                "Run scripts/compile_companies.py to generate artifacts.",
                index_path,
            )
            self._index = {"schema_version": None, "companies": []}
            self._cache = {}
            return
        self._index = json.loads(index_path.read_text(encoding="utf-8"))
        cache: Dict[str, dict] = {}
        for entry in self._index.get("companies", []):
            cid = entry.get("company_id")
            latest_rel = entry.get("latest")
            if not cid or not latest_rel:
                continue
            artifact_path = self._dir / latest_rel
            if not artifact_path.exists():
                logger.warning("Compiled artifact missing for %s: %s", cid, artifact_path)
                continue
            try:
                cache[cid] = json.loads(artifact_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                logger.error("Failed to parse artifact %s: %s", artifact_path, exc)
        self._cache = cache

    # -- public API ---------------------------------------------------------
    def refresh(self) -> None:
        """Force a reload of artifacts from disk (e.g. after recompilation)."""
        with self._lock:
            self._loaded = False
            self._index = None
            self._cache = {}
        self._ensure_loaded()

    def is_ready(self) -> bool:
        self._ensure_loaded()
        return bool(self._cache)

    def index(self) -> dict:
        self._ensure_loaded()
        return dict(self._index or {})

    def list_companies(self) -> List[dict]:
        """Return lightweight catalog entries (registry + version pointers)."""
        self._ensure_loaded()
        out: List[dict] = []
        for cid, art in self._cache.items():
            meta = art.get("metadata", {})
            out.append({
                "company_id": cid,
                "name": meta.get("display_name") or meta.get("name"),
                "accent": meta.get("accent"),
                "category": meta.get("primary_category"),
                "profile_version": art.get("profile_version"),
                "artifact_schema_version": art.get("artifact_schema_version"),
            })
        # Preserve registry order via index if available.
        order = [e.get("company_id") for e in (self._index or {}).get("companies", [])]
        if order:
            out.sort(key=lambda e: order.index(e["company_id"]) if e["company_id"] in order else 999)
        return out

    # Fields that are compiled from raw editorial markdown and must NOT be
    # served on the public runtime API. They remain in the on-disk artifact and
    # are retrievable via internal-only accessors (get_sections).
    _INTERNAL_ONLY_FIELDS = ("sections",)

    def _artifact(self, company_id: str) -> Optional[dict]:
        """Return a defensive deep copy of the full on-disk artifact (INTERNAL
        use only). Deep-copied so callers can never mutate the shared cache."""
        self._ensure_loaded()
        art = self._cache.get(company_id)
        return copy.deepcopy(art) if art else None

    def get_company(self, company_id: str) -> Optional[dict]:
        """Public runtime view: normalized data only.

        The raw editorial ``sections`` block (verbatim markdown text) is
        stripped so the public API never exposes markdown.
        """
        art = self._artifact(company_id)
        if art is None:
            return None
        for field in self._INTERNAL_ONLY_FIELDS:
            art.pop(field, None)
        return art

    def get_sections(self, company_id: str) -> Optional[dict]:
        """INTERNAL/admin-only: raw editorial section text. Not exposed on the
        public API. Reserved for future explainability/admin tooling."""
        art = self._artifact(company_id)
        if art is None:
            return None
        return art.get("sections", {})

    def get_summary(self, company_id: str) -> Optional[dict]:
        art = self.get_company(company_id)
        if art is None:
            return None
        return {
            "company_id": company_id,
            "profile_version": art.get("profile_version"),
            "summary_variant": art.get("summary_variant"),
            "summary": art.get("summary", {}),
        }

    def get_signals(self, company_id: str) -> Optional[dict]:
        art = self.get_company(company_id)
        if art is None:
            return None
        return {
            "company_id": company_id,
            "profile_version": art.get("profile_version"),
            "summary_variant": art.get("summary_variant"),
            "signals": art.get("signals", []),
            "subjects": art.get("subjects", {}),
        }

    def get_metadata(self, company_id: str) -> Optional[dict]:
        art = self.get_company(company_id)
        if art is None:
            return None
        return {
            "company_id": company_id,
            "metadata": art.get("metadata", {}),
            "profile_version": art.get("profile_version"),
            "artifact_schema_version": art.get("artifact_schema_version"),
            "registry_schema_version": art.get("registry_schema_version"),
            "source_checksum": art.get("source_checksum"),
            "content_checksum": art.get("content_checksum"),
        }


# Module-level singleton for app-wide reuse.
company_intelligence = CompanyIntelligenceService()
