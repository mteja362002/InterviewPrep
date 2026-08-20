"""Company Intelligence schema validator (compile-time only).

Validates that a canonical company markdown profile conforms to the Company
Knowledge Schema (docs/curriculum/company-intelligence/schema.md) before it is
compiled into a runtime artifact.

Design rules:
  * Deterministic: same input -> same result.
  * NO silent repair. On any violation the validator reports a structured
    error; the compiler refuses to emit an artifact for that company.
  * Meaningful diagnostics: every error names the company, the rule, and the
    concrete missing/invalid element.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

import yaml

# ---------------------------------------------------------------------------
# Canonical required sections (matched case-insensitively as heading substrings).
# Mirrors the "Required Sections" contract in schema.md.
# ---------------------------------------------------------------------------
REQUIRED_SECTIONS: List[str] = [
    "Metadata",
    "Company Overview",
    "Engineering Philosophy",
    "Hiring Philosophy",
    "Interview Pipeline",
    "Evaluation Signals",
    "Subject Importance",
    "Behavioral",            # "Behavioral Expectations" / "Behavioral Signals"
    "Role Differences",
    "Evidence Summary",
    "Machine-Readable Summary",
]

_HEADING_RE = re.compile(r"^#{1,3}\s+(.*)$", re.MULTILINE)
_MR_ANCHOR = "Machine-Readable Summary"
_YAML_BLOCK_RE = re.compile(r"```yaml\s*\n(.*?)```", re.DOTALL)


@dataclass
class ValidationResult:
    company_id: str
    ok: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    # Parsed machine-readable YAML payload (populated only when parseable).
    summary: Optional[dict] = None

    def error(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def extract_machine_readable_yaml(markdown: str) -> Optional[str]:
    """Return the raw YAML text of the first ```yaml block that appears AFTER
    the 'Machine-Readable Summary' heading, or None if not found."""
    idx = markdown.find(_MR_ANCHOR)
    if idx < 0:
        return None
    m = _YAML_BLOCK_RE.search(markdown, idx)
    if not m:
        return None
    return m.group(1)


def _headings(markdown: str) -> List[str]:
    return [h.strip() for h in _HEADING_RE.findall(markdown)]


def validate_markdown(company_id: str, markdown: str) -> ValidationResult:
    """Validate a single company markdown document against the canonical schema."""
    result = ValidationResult(company_id=company_id)

    if not markdown or not markdown.strip():
        result.error(f"[{company_id}] markdown document is empty")
        return result

    # 1) Required canonical sections must be present.
    headings_blob = " || ".join(_headings(markdown)).lower()
    for section in REQUIRED_SECTIONS:
        if section.lower() not in headings_blob:
            result.error(
                f"[{company_id}] missing required section heading: '{section}'"
            )

    # 2) Machine-readable YAML block must exist and parse.
    raw_yaml = extract_machine_readable_yaml(markdown)
    if raw_yaml is None:
        result.error(
            f"[{company_id}] no ```yaml block found under '{_MR_ANCHOR}' section"
        )
        return result

    try:
        summary = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        result.error(f"[{company_id}] machine-readable YAML failed to parse: {exc}")
        return result

    if not isinstance(summary, dict):
        result.error(
            f"[{company_id}] machine-readable summary must be a YAML mapping, "
            f"got {type(summary).__name__}"
        )
        return result

    result.summary = summary

    # 3) Required machine-readable fields.
    company = summary.get("company")
    if not isinstance(company, dict) or not company.get("name"):
        result.error(f"[{company_id}] machine-readable summary missing 'company.name'")

    profile = summary.get("profile")
    if not isinstance(profile, dict) or not profile.get("version"):
        result.error(
            f"[{company_id}] machine-readable summary missing 'profile.version'"
        )

    # 4) Must expose evaluation signals in one of the two canonical shapes.
    has_interview = isinstance(summary.get("interview"), dict) and summary["interview"]
    has_signals = isinstance(summary.get("signals"), list) and summary["signals"]
    if not (has_interview or has_signals):
        result.error(
            f"[{company_id}] machine-readable summary must contain either a non-empty "
            f"'interview' mapping or a non-empty 'signals' list"
        )

    # 5) Subject importance mapping is required.
    if not isinstance(summary.get("subjects"), dict) or not summary["subjects"]:
        result.error(
            f"[{company_id}] machine-readable summary missing non-empty 'subjects' mapping"
        )

    # Non-fatal advisories.
    if not summary.get("planner"):
        result.warn(f"[{company_id}] machine-readable summary has no 'planner' section")
    if isinstance(profile, dict) and not profile.get("confidence"):
        result.warn(f"[{company_id}] profile has no 'confidence' value")

    return result
