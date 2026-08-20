"""PrepOS Company Intelligence package.

Architecture (Phase 1):

    Company Markdown (docs/.../companies/*.md)   <- canonical EDITORIAL source
            |
            v   (compile-time only; scripts/compile_companies.py)
    Schema Validation (schema_validator.py)
            |
            v
    Normalization + Compilation (compiler.py)
            |
            v
    Compiled JSON Artifacts (company_intelligence/compiled/**)  <- canonical RUNTIME source
            |
            v   (runtime; NEVER parses markdown)
    Runtime Loader (loader.py) -> Read-only APIs (routes_companies.py)

CONSTRAINTS:
  * Runtime MUST consume only compiled JSON artifacts. It MUST NOT parse markdown.
  * The single canonical company registry lives in registry.json and is shared
    with the frontend (frontend/src/config/companies.generated.json is generated
    from it).
  * Compilation is deterministic and never silently repairs malformed markdown.
"""

from .registry import (
    REGISTRY_SCHEMA_VERSION,
    company_ids,
    company_registry,
    get_company_meta,
    is_known_company,
)

__all__ = [
    "REGISTRY_SCHEMA_VERSION",
    "company_ids",
    "company_registry",
    "get_company_meta",
    "is_known_company",
]
