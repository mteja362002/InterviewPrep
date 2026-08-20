#!/usr/bin/env python3
"""Deterministic Company Intelligence compilation CLI.

Reads canonical company markdown (editorial source), validates + compiles each
profile into normalized JSON artifacts (runtime source), and regenerates the
shared frontend catalog from the single canonical registry.

Usage:
    python backend/scripts/compile_companies.py            # compile all
    python backend/scripts/compile_companies.py google     # compile a subset
    python backend/scripts/compile_companies.py --check     # validate only

Exit code is non-zero if ANY company fails validation/compilation. Malformed
markdown is never silently repaired.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make the backend package importable regardless of CWD.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from company_intelligence import registry  # noqa: E402
from company_intelligence.compiler import (  # noqa: E402
    ARTIFACT_SCHEMA_VERSION,
    COMPILED_DIR,
    CompilationError,
    compile_company,
)

_REPO_ROOT = _BACKEND_DIR.parent
_FRONTEND_CATALOG = _REPO_ROOT / "frontend" / "src" / "config" / "companies.generated.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_artifact(company_id: str, artifact: dict) -> dict:
    """Persist immutable versioned artifact + latest alias. Returns index entry."""
    version = artifact["profile_version"]
    cdir = COMPILED_DIR / company_id
    versioned_rel = f"{company_id}/v{version}.json"
    latest_rel = f"{company_id}/latest.json"
    _write_json(COMPILED_DIR / versioned_rel, artifact)
    _write_json(COMPILED_DIR / latest_rel, artifact)
    meta = artifact.get("metadata", {})
    return {
        "company_id": company_id,
        "name": meta.get("display_name") or meta.get("name"),
        "accent": meta.get("accent"),
        "category": meta.get("primary_category"),
        "profile_version": version,
        "artifact_schema_version": artifact.get("artifact_schema_version"),
        "latest": latest_rel,
        "versioned": versioned_rel,
        "source_checksum": artifact.get("source_checksum"),
        "content_checksum": artifact.get("content_checksum"),
    }


def _write_frontend_catalog() -> None:
    """Regenerate the shared frontend catalog from the canonical registry."""
    data = {
        "_generated": "DO NOT EDIT. Generated from backend/company_intelligence/registry.json "
                      "by backend/scripts/compile_companies.py.",
        "schema_version": registry.REGISTRY_SCHEMA_VERSION,
        "companies": [
            {"id": c["id"], "name": c["name"], "accent": c["accent"]}
            for c in registry.company_registry()
        ],
    }
    _write_json(_FRONTEND_CATALOG, data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile PrepOS company intelligence.")
    parser.add_argument("companies", nargs="*", help="Optional subset of company ids.")
    parser.add_argument("--check", action="store_true", help="Validate only; do not write artifacts.")
    parser.add_argument("--clean", action="store_true", help="Remove compiled/ before writing.")
    args = parser.parse_args()

    all_ids = registry.company_ids()
    targets = args.companies or all_ids
    unknown = [c for c in targets if c not in all_ids]
    if unknown:
        print(f"ERROR: unknown company id(s) not in registry: {unknown}", file=sys.stderr)
        return 2

    if args.clean and not args.check and COMPILED_DIR.exists():
        shutil.rmtree(COMPILED_DIR)

    index_entries = []
    failures = []
    print(f"Compiling {len(targets)} company profile(s) "
          f"(artifact schema v{ARTIFACT_SCHEMA_VERSION})\n")

    for cid in targets:
        try:
            artifact = compile_company(cid)
        except CompilationError as exc:
            failures.append(cid)
            print(f"  [FAIL] {cid}")
            for err in exc.errors:
                print(f"         - {err}")
            continue

        warns = artifact.get("validation", {}).get("warnings", [])
        status = "OK  " if not warns else "WARN"
        print(f"  [{status}] {cid}  v{artifact['profile_version']}  "
              f"{artifact['content_checksum'][:19]}...")
        for w in warns:
            print(f"         ! {w}")

        if not args.check:
            index_entries.append(_write_artifact(cid, artifact))

    if not args.check:
        # index.json is the MUTABLE manifest / latest-alias pointer.
        index = {
            "schema_version": registry.REGISTRY_SCHEMA_VERSION,
            "artifact_schema_version": ARTIFACT_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "company_count": len(index_entries),
            "companies": index_entries,
        }
        _write_json(COMPILED_DIR / "index.json", index)
        _write_frontend_catalog()

    print()
    if failures:
        print(f"FAILED: {len(failures)} company profile(s) did not compile: {failures}")
        return 1
    if args.check:
        print(f"OK: all {len(targets)} company profile(s) are valid.")
    else:
        print(f"OK: compiled {len(index_entries)} artifact(s) -> {COMPILED_DIR}")
        print(f"    frontend catalog -> {_FRONTEND_CATALOG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
