"""Verification gate item 1 — executable proof of provenance separation.

Runs the REAL `_derive_subject_status` and the REAL `services.evidence`
boundary. No mocks of the logic under test.
"""
import sys

sys.path.insert(0, ".")

from services.evidence import ACTUAL, BASELINE, LEGACY, certified_fields, planner_row  # noqa: E402
from services.learning_engine.subject_progression import _derive_subject_status  # noqa: E402

TRACK = "dsa"
NODES = [{"id": "n1", "learning_stage": "foundation"},
         {"id": "n2", "learning_stage": "core"}]


def derive(progress_map):
    return _derive_subject_status(
        track_id=TRACK,
        subject_prereqs=[],
        completed_subjects={TRACK},
        track_nodes=NODES,
        progress_map=progress_map,
    )


def row(status, source):
    r = {"node_id": "n1", "status": status}
    if source is not None:
        r["planner_progress_source"] = source
    return r


results = []


def check(label, got, want):
    ok = got == want
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}\n         got={got!r} want={want!r}")


print("=" * 72)
print("A. Three provenance states remain DISTINCT at the decision site")
print("=" * 72)
# n2 left incomplete so we never short-circuit to 'mastered'
check("onboarding_baseline completion -> effectively_completed",
      derive({"n1": row("completed", BASELINE)}), "effectively_completed")
check("unverified_legacy completion -> effectively_completed",
      derive({"n1": row("completed", LEGACY)}), "effectively_completed")
check("missing provenance -> effectively_completed",
      derive({"n1": row("completed", None)}), "effectively_completed")
check("empty-string provenance -> effectively_completed",
      derive({"n1": row("completed", "")}), "effectively_completed")
check("certified_actual completion -> completed",
      derive({"n1": row("completed", ACTUAL)}), "completed")

print()
print("=" * 72)
print("B. `not onboarding_baseline` is NOT treated as certified actual")
print("=" * 72)
for bogus in ("legacy", "unknown", "imported", "self_reported", "migrated_v1"):
    check(f"unrecognised source {bogus!r} -> effectively_completed",
          derive({"n1": row("completed", bogus)}), "effectively_completed")

print()
print("=" * 72)
print("C. LAUNDERING PROBE — does an unrelated certified field promote a")
print("   legacy unverified completion into certified-actual evidence?")
print("=" * 72)

# A historical UNVERIFIED_LEGACY row: top-level status='completed' was never
# certified by any forward writer. The learner later performs a *confidence*
# update, which IS a certified forward write — but says nothing about status.
legacy_completion_plus_confidence = {
    "node_id": "n1",
    "status": "completed",              # legacy, unverified, top-level
    "planner_progress_source": LEGACY,
    "certified_progress": {
        "confidence": 4,               # the ONLY certified field
        "field_sources": {
            "confidence": {"source": "confidence_update",
                           "recorded_at": "2026-09-09T12:00:00Z"},
        },
    },
}

cf = certified_fields(legacy_completion_plus_confidence)
pr = planner_row(legacy_completion_plus_confidence)
print(f"  certified_fields()          = {cf}")
print(f"  -> status certified?          {'status' in cf}")
print(f"  planner_progress_source     = {pr['planner_progress_source']!r}")
print(f"  status carried into planner = {pr['status']!r}")
print()

status_uncertified = "status" not in cf
stamped_actual = pr["planner_progress_source"] == ACTUAL
derived = derive({"n1": pr})
print(f"  _derive_subject_status()    = {derived!r}")
print()

laundered = status_uncertified and stamped_actual and derived == "completed"
if laundered:
    print("  [!! HAZARD CONFIRMED !!] An UNVERIFIED_LEGACY completion was")
    print("  promoted to 'completed' (certified actual) even though NO forward")
    print("  writer ever certified `status`. The row-level source stamp was")
    print("  earned by an unrelated field (confidence).")
else:
    print("  [SAFE] legacy completion was not laundered.")
results.append(not laundered)

print()
print("=" * 72)
print("D. Control — the same row WITHOUT the unrelated certified field")
print("=" * 72)
control = dict(legacy_completion_plus_confidence)
control.pop("certified_progress")
pr_control = planner_row(control)
print(f"  planner_progress_source     = {pr_control['planner_progress_source']!r}")
check("legacy completion alone -> effectively_completed",
      derive({"n1": pr_control}), "effectively_completed")

print()
print("=" * 72)
print(f"RESULT: {sum(results)}/{len(results)} checks passed")
print("=" * 72)
sys.exit(0 if all(results) else 1)
