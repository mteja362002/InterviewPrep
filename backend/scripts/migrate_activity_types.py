"""One-time migration: stamp activity_type + assessment_type onto the roadmap.

PHASE 3C.1 \u2014 Foundation Stabilization (Architecture Freeze), decision #3.

``activity_type`` and ``assessment_type`` are CURRICULUM metadata (not runtime
decisions), so they must live inside the roadmap JSON itself. This script
writes them onto every node of ``data/roadmap_v1.json`` using the single
canonical, deterministic build-time derivation in
``services.curriculum.activity_metadata`` \u2014 the very same rules that
``scripts/generate_roadmap.py`` now applies for future generation.

Idempotent: running twice produces byte-identical output. A timestamped
backup of the roadmap is written before the first mutation.

Usage (from backend/):
    python scripts/migrate_activity_types.py            # apply + write
    python scripts/migrate_activity_types.py --check    # dry-run, no write
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.curriculum.activity_metadata import stamp_node  # noqa: E402

_DATA = Path(__file__).resolve().parent.parent / "data"
_ROADMAP = _DATA / "roadmap_v1.json"

# Every list key that can hold child nodes in the roadmap tree.
_CHILD_KEYS = ("modules", "topics", "subtopics", "learning_nodes")


def _walk(node: dict, track_id: str, stats: dict) -> None:
    stamp_node(node, track_id)
    stats["count"] += 1
    stats.setdefault("by_activity", {})
    stats["by_activity"][node["activity_type"]] = (
        stats["by_activity"].get(node["activity_type"], 0) + 1
    )
    for key in _CHILD_KEYS:
        for child in (node.get(key) or []):
            _walk(child, track_id, stats)


def migrate(check: bool = False) -> dict:
    data = json.loads(_ROADMAP.read_text(encoding="utf-8"))
    stats = {"count": 0}
    for track in data.get("tracks", []):
        _walk(track, track["id"], stats)

    if check:
        return stats

    backup = _DATA / "roadmap_v1.backup.pre_activity_types.json"
    if not backup.exists():
        shutil.copy2(_ROADMAP, backup)
        print(f"Backup written: {backup}")

    _ROADMAP.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Stamped {stats['count']} nodes -> {_ROADMAP}")
    print(f"By activity_type: {stats['by_activity']}")
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="dry-run, no write")
    args = ap.parse_args()
    migrate(check=args.check)
