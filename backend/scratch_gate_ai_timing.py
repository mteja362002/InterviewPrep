"""VERIFICATION GATE item 5 — AI generation latency + single-flight proof.

Measures three scenarios against the REAL provider and the REAL database:

  A. First generation (cold)  — cache cleared first.
                                Reports cache_check_ms / generation_ms /
                                parse_ms / persist_ms / total_ms.
  B. Cache hit                — immediately re-requests the same node.
                                Confirms provider calls did NOT increase.
  C. Concurrent same-node     — cache cleared, then two ensure_content()
                                coroutines for the SAME (node_id,
                                roadmap_version) are launched together.
                                Asserts provider calls == 1 and reports
                                waited_for_lock for the second request.

The provider function is wrapped by a counting proxy that DELEGATES to the
real `ai_service.complete`, so latency figures are genuine while calls stay
countable. Nothing is stubbed or simulated.

Emits test_reports/gate_ai_timing.json.

Costs real API credits: 2 generations (one for A, one for C).

Run:  python scratch_gate_ai_timing.py [node_id]
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

import knowledge_generation as kg
from roadmap import get_roadmap, CURRENT_VERSION

DEFAULT_NODE = None  # resolved from the roadmap if not supplied
USER_ID = "verification-gate-harness"

_provider_calls = 0
_provider_lock = asyncio.Lock()
_real_complete = kg.complete


async def _counting_complete(*args, **kwargs):
    """Delegate to the real provider, counting invocations."""
    global _provider_calls
    async with _provider_lock:
        _provider_calls += 1
    return await _real_complete(*args, **kwargs)


def _reset_counter():
    global _provider_calls
    _provider_calls = 0


def _pick_node() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    roadmap = get_roadmap()
    for tid in roadmap.track_ids():
        nodes = roadmap.get_track_learning_nodes(tid)
        if nodes:
            return nodes[0]["id"]
    raise SystemExit("Could not resolve a roadmap node id.")


async def main():
    load_dotenv()
    kg.complete = _counting_complete          # install counting proxy

    node_id = _pick_node()
    version = CURRENT_VERSION
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    out: dict = {
        "node_id": node_id,
        "roadmap_version": version,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print("=" * 72)
    print(f"AI GENERATION TIMING — node={node_id} version={version}")
    print("=" * 72)

    # ---- A. Cold generation ----------------------------------------
    removed = await kg.clear_cache(db, node_id=node_id, roadmap_version=version)
    _reset_counter()
    t0 = time.monotonic()
    try:
        doc = await kg.ensure_content(
            db, node_id=node_id, roadmap_version=version, user_id=USER_ID)
        wall = round((time.monotonic() - t0) * 1000, 1)
        out["A_first_generation"] = {
            "cache_rows_cleared": removed,
            "timing": doc.get("_timing"),
            "wall_ms": wall,
            "provider_calls": _provider_calls,
            "theory_chars": len(doc.get("theory") or ""),
            "prerequisites": doc.get("prerequisites"),
            "related_topics": doc.get("related_topics"),
        }
    except Exception as exc:
        out["A_first_generation"] = {
            "error": f"{type(exc).__name__}: {exc}",
            "kind": getattr(exc, "kind", None),
            "wall_ms": round((time.monotonic() - t0) * 1000, 1),
            "provider_calls": _provider_calls,
        }
    print("\nA. FIRST GENERATION (cold)")
    print(json.dumps(out["A_first_generation"], indent=4, default=str)[:2000])

    # ---- B. Cache hit ----------------------------------------------
    before = _provider_calls
    t0 = time.monotonic()
    doc2 = await kg.ensure_content(
        db, node_id=node_id, roadmap_version=version, user_id=USER_ID)
    out["B_cache_hit"] = {
        "timing": doc2.get("_timing"),
        "wall_ms": round((time.monotonic() - t0) * 1000, 1),
        "provider_calls_before": before,
        "provider_calls_after": _provider_calls,
        "no_new_ai_generation": _provider_calls == before,
        "cache_hit_flag": (doc2.get("_timing") or {}).get("cache_hit"),
    }
    print("\nB. CACHE HIT")
    print(json.dumps(out["B_cache_hit"], indent=4, default=str))

    # ---- C. Concurrent same-node -----------------------------------
    await kg.clear_cache(db, node_id=node_id, roadmap_version=version)
    _reset_counter()
    t0 = time.monotonic()
    results = await asyncio.gather(
        kg.ensure_content(db, node_id=node_id, roadmap_version=version,
                          user_id=USER_ID + "-r1"),
        kg.ensure_content(db, node_id=node_id, roadmap_version=version,
                          user_id=USER_ID + "-r2"),
        return_exceptions=True,
    )
    wall = round((time.monotonic() - t0) * 1000, 1)

    timings = []
    for i, r in enumerate(results, start=1):
        if isinstance(r, BaseException):
            timings.append({"request": i, "error": f"{type(r).__name__}: {r}"})
        else:
            timings.append({"request": i, "timing": r.get("_timing")})

    waiter = next(
        (t for t in timings
         if (t.get("timing") or {}).get("waited_for_lock")), None)

    out["C_concurrent_same_node"] = {
        "wall_ms": wall,
        "provider_calls": _provider_calls,
        "single_flight_holds": _provider_calls == 1,
        "requests": timings,
        "waited_for_lock_reported_by":
            waiter["request"] if waiter else None,
        "note": ("waited_for_lock is only stamped when the waiter's "
                 "post-lock cache re-check HITS; if the winner errored, the "
                 "waiter generates and the flag is absent by design."),
    }
    print("\nC. CONCURRENT SAME-NODE (2 requests)")
    print(json.dumps(out["C_concurrent_same_node"], indent=4, default=str))

    # ---- Verdict ----------------------------------------------------
    a = out["A_first_generation"]
    gen_ms = ((a.get("timing") or {}).get("generation_ms")
              if "timing" in a else None)
    total_ms = ((a.get("timing") or {}).get("total_ms")
                if "timing" in a else None)
    out["conclusions"] = {
        "cold_generation_total_ms": total_ms,
        "provider_generation_ms": gen_ms,
        "provider_share_of_total":
            (round(gen_ms / total_ms, 3) if gen_ms and total_ms else None),
        "cache_hit_total_ms": (out["B_cache_hit"].get("timing") or {}).get("total_ms"),
        "cache_hit_avoids_provider_call": out["B_cache_hit"]["no_new_ai_generation"],
        "single_flight_deduplicates": out["C_concurrent_same_node"]["single_flight_holds"],
    }
    print("\nCONCLUSIONS")
    print(json.dumps(out["conclusions"], indent=4, default=str))

    dest = Path(__file__).parent / "test_reports" / "gate_ai_timing.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nJSON: {dest}")
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
