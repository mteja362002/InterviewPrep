"""Explicitly supported evidence fixtures, never used to classify production data."""
from copy import deepcopy
from services.evidence import FIELDS


def certified(row, source="confidence_update"):
    raw = deepcopy(row)
    fields = {key: raw.pop(key) for key in list(raw) if key in FIELDS}
    raw.setdefault("roadmap_version", "v1")
    raw["certified_progress"] = {
        **fields,
        "field_sources": {key: {"source": source, "recorded_at": "2026-09-09T00:00:00+00:00"}
                          for key in fields},
    }
    return raw
