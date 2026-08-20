"""Single canonical company registry loader.

registry.json is the ONLY authored source of company identity in the whole
repository. Every other consumer (backend readiness, compiled artifacts index,
frontend catalog) derives from it.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

_REGISTRY_PATH = Path(__file__).resolve().parent / "registry.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    with _REGISTRY_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


REGISTRY_SCHEMA_VERSION: str = _load().get("schema_version", "1.0")


def company_registry() -> List[dict]:
    """Return the ordered list of canonical company registry entries."""
    return list(_load().get("companies", []))


def company_ids() -> List[str]:
    """Return the ordered list of canonical company ids."""
    return [c["id"] for c in company_registry()]


@lru_cache(maxsize=1)
def _by_id() -> Dict[str, dict]:
    return {c["id"]: c for c in company_registry()}


def get_company_meta(company_id: str) -> Optional[dict]:
    """Return the registry display metadata for ``company_id`` or None."""
    return _by_id().get(company_id)


def is_known_company(company_id: str) -> bool:
    return company_id in _by_id()


REGISTRY_PATH = _REGISTRY_PATH
