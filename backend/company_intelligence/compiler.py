"""Deterministic Company Intelligence compiler (compile-time only).

Converts a canonical company markdown profile into a normalized, versioned JSON
artifact that the runtime loader consumes. Markdown is read ONLY here (at
compile time). Runtime never touches markdown.

Determinism guarantees:
  * Given identical source markdown + registry metadata, the emitted artifact
    (excluding no fields) is byte-for-byte identical. No wall-clock timestamps
    are written into immutable artifacts.
  * ``source_checksum`` = sha256 of the raw markdown bytes.
  * ``content_checksum`` = sha256 of the canonical JSON serialization of the
    artifact payload (with source/content checksums blanked), enabling exact
    version tracing.
  * Malformed markdown is NEVER silently repaired. Validation failure raises
    CompilationError with structured diagnostics.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from . import registry
from .schema_validator import ValidationResult, validate_markdown

# Artifact schema version. Bump when the compiled artifact SHAPE changes.
ARTIFACT_SCHEMA_VERSION = "1.0"

_REPO_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_DIR = _REPO_ROOT / "docs" / "curriculum" / "company-intelligence" / "companies"
COMPILED_DIR = Path(__file__).resolve().parent / "compiled"

# Canonical editorial sections preserved as raw text (top-level '# N. Title').
# key -> heading substring (case-insensitive). Only present sections are stored.
_SECTION_MAP = {
    "company_overview": "Company Overview",
    "engineering_philosophy": "Engineering Philosophy",
    "hiring_philosophy": "Hiring Philosophy",
    "interview_pipeline": "Interview Pipeline",
    "evaluation_signals": "Evaluation Signals",
    "subject_importance": "Subject Importance",
    "behavioral": "Behavioral",
    "role_differences": "Role Differences",
    "negative_evidence": "Negative Evidence",
    "contradiction_register": "Contradiction Register",
    "preparation_strategy": "Preparation Strategy",
    "evidence_summary": "Evidence Summary",
}

_TOP_HEADING_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)


class CompilationError(Exception):
    """Raised when a company profile cannot be compiled (validation failed)."""

    def __init__(self, company_id: str, errors: List[str]):
        self.company_id = company_id
        self.errors = errors
        super().__init__(
            f"Company '{company_id}' failed schema validation:\n  - "
            + "\n  - ".join(errors)
        )


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _humanize(key: str) -> str:
    return key.replace("_", " ").strip().title()


def markdown_path(company_id: str) -> Path:
    return MARKDOWN_DIR / f"{company_id}.md"


def _extract_section(markdown: str, title_substr: str) -> Optional[str]:
    """Return the raw body text of the first top-level ('# ') section whose
    heading contains ``title_substr`` (case-insensitive), up to the next
    top-level heading. Deterministic; no interpretation of the content."""
    matches = list(_TOP_HEADING_RE.finditer(markdown))
    target = title_substr.lower()
    for i, m in enumerate(matches):
        if target in m.group(1).lower():
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            return markdown[start:end].strip()
    return None


def _normalize_signals(summary: dict) -> (List[dict], str):
    """Unify the two canonical signal representations into one list.

    Returns (signals, variant) where variant is 'interview' or 'signals'.
    This is an ADDITIVE convenience view; the full original payload is always
    preserved under artifact['summary'].
    """
    interview = summary.get("interview")
    if isinstance(interview, dict) and interview:
        signals = []
        for key, val in interview.items():
            val = val or {}
            signals.append({
                "id": key,
                "name": _humanize(key),
                "importance": val.get("importance"),
                "confidence": val.get("confidence"),
                "role_dependency": val.get("role_dependency", False),
                "level_dependency": val.get("level_dependency", False),
                "formal_component": val.get("formal_component", False),
            })
        return signals, "interview"

    raw = summary.get("signals")
    if isinstance(raw, list) and raw:
        signals = []
        for item in raw:
            item = item or {}
            signals.append({
                "id": item.get("id"),
                "name": item.get("name") or _humanize(str(item.get("id", ""))),
                "importance": item.get("importance"),
                "confidence": item.get("confidence"),
                "role_dependency": item.get("role_dependency", False),
                "level_dependency": item.get("level_dependency", False),
                "signal_type": item.get("signal_type"),
                "evidence_status": item.get("evidence_status"),
                "planner_hint": item.get("planner_hint"),
                "scope": item.get("scope"),
            })
        return signals, "signals"

    return [], "unknown"


def _build_payload(company_id: str, markdown: str, result: ValidationResult) -> dict:
    summary = result.summary or {}
    company = summary.get("company", {}) or {}
    profile = summary.get("profile", {}) or {}
    meta = registry.get_company_meta(company_id) or {}

    signals, variant = _normalize_signals(summary)

    sections: Dict[str, str] = {}
    for key, title in _SECTION_MAP.items():
        body = _extract_section(markdown, title)
        if body:
            sections[key] = body

    payload = {
        "company_id": company_id,
        "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
        "registry_schema_version": registry.REGISTRY_SCHEMA_VERSION,
        "profile_version": str(profile.get("version")),
        "source_checksum": "",   # filled below (deterministic)
        "content_checksum": "",  # filled below (deterministic)
        "metadata": {
            "name": company.get("name"),
            "display_name": meta.get("name"),
            "accent": meta.get("accent"),
            "primary_category": meta.get("category"),
            "categories": company.get("categories", []),
            "last_reviewed": profile.get("last_reviewed"),
            "confidence": profile.get("confidence"),
        },
        "summary_variant": variant,
        "signals": signals,
        "subjects": summary.get("subjects", {}),
        "levels": summary.get("levels", {}),
        "trends": summary.get("trends", {}),
        "planner": summary.get("planner", {}),
        # Full machine-readable payload preserved verbatim (incl. variant-only
        # fields like negative_evidence, contradictions, priority_by_level,
        # signal_classification, role_domains). Nothing is lost.
        "summary": summary,
        # Raw editorial section text (engineering/hiring philosophy, evidence,
        # etc.) preserved for downstream explainability.
        "sections": sections,
        "validation": {
            "warnings": list(result.warnings),
        },
    }
    return payload


def compile_company(company_id: str) -> dict:
    """Validate + compile a single company. Raises CompilationError on failure."""
    path = markdown_path(company_id)
    if not path.exists():
        raise CompilationError(company_id, [f"markdown file not found: {path}"])

    markdown = path.read_text(encoding="utf-8")
    result = validate_markdown(company_id, markdown)
    if not result.ok:
        raise CompilationError(company_id, result.errors)

    payload = _build_payload(company_id, markdown, result)

    # Deterministic checksums.
    payload["source_checksum"] = _sha256(markdown)
    checksum_seed = dict(payload)
    checksum_seed["content_checksum"] = ""
    canonical = json.dumps(checksum_seed, sort_keys=True, ensure_ascii=False)
    payload["content_checksum"] = _sha256(canonical)
    return payload
