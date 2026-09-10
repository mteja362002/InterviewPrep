"""VERIFICATION GATE item 4 — regression comparison by test IDENTITY.

The sprint baseline is the union of two runs recorded 2026-09-09:

    test_reports/baseline_semantic_sprint_focused.xml     ->  34 tests
    test_reports/baseline_semantic_sprint_regression.xml  -> 158 tests
                                                    union -> 192 unique
                                                          -> 188 passed / 4 failed

This script compares a NEW junit XML (or several) against that baseline
per-test-id, so "4 failures before, 4 failures after" can never be mistaken
for "no regressions" when the identities differ or when the new run simply
executed fewer tests.

Reports four things the gate asks for separately:
  1. known pre-existing failures — still failing / now fixed
  2. NEW failures (passed in baseline, or absent from baseline)
  3. previously-passing tests that now fail   (the real regression signal)
  4. baseline tests MISSING from the new run  (coverage gaps)

Usage:
    python scratch_gate_compare_regression.py NEW.xml [MORE.xml ...]

Emits test_reports/gate_regression_delta.json
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPORTS = Path(__file__).parent.parent / "test_reports"
BASELINE = [
    REPORTS / "baseline_semantic_sprint_focused.xml",
    REPORTS / "baseline_semantic_sprint_regression.xml",
]

# The four failures the sprint declared pre-existing. Matched by suffix so
# the comparison is robust to classname prefixing differences between runs.
KNOWN_PRE_EXISTING = [
    "test_onboarding_knowledge_seed::test_seed_covers_every_roadmap_track_with_stage_aware_rows",
    "test_interview_pacing::test_mission_practice_count_still_driven_by_study_hours_at_same_urgency",
    "test_candidate_generation::test_candidate_pool_is_compact_and_within_expected_range",
    "test_candidate_generation::test_weakest_or_revision_due_track_is_prioritized",
]

# Failing tests that are pre-existing but were NOT in the 192-test baseline
# selection, so a naive baseline diff reports them as "new". Each entry must
# carry evidence that it pre-dates the sprint, otherwise it does not belong
# here — this list is a documented exception, not a mute button.
KNOWN_PRE_EXISTING_OUTSIDE_BASELINE = {
    "test_mission_roadmap_catalog::test_candidate_ranking_uses_seeded_rng_for_exact_ties": (
        "Already failing in learner_audit_extended.xml @2026-09-09T19:19:26, "
        "31 min BEFORE the baseline was recorded @19:50:13. Exercises "
        "mission_engine.rank_candidate_topics, which has ZERO real changes in "
        "this sprint (git diff --numstat --ignore-cr-at-eol -w). Cause is the "
        "test asserting rank_candidate_topics consumes the seeded rng exactly "
        "like a bare rng.choice(); unrelated to provenance/session selection."
    ),
}


def load(paths) -> dict[str, str]:
    """Return {test_id: outcome} where outcome in passed/failed/error/skipped."""
    results: dict[str, str] = {}
    for p in paths:
        if not Path(p).exists():
            print(f"  !! missing: {p}")
            continue
        root = ET.parse(p).getroot()
        for case in root.iter("testcase"):
            cls = (case.get("classname") or "").split(".")[-1]
            tid = f"{cls}::{case.get('name')}"
            outcome = "passed"
            for child in case:
                tag = child.tag.lower()
                if tag in ("failure", "error"):
                    outcome = "failed"
                    break
                if tag == "skipped":
                    outcome = "skipped"
            # A test appearing twice fails if it failed anywhere.
            if results.get(tid) == "failed":
                continue
            results[tid] = outcome
    return results


def matches_known(tid: str) -> bool:
    return any(tid.endswith(k) or k.endswith(tid) for k in KNOWN_PRE_EXISTING)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    new_paths = [Path(a) for a in sys.argv[1:]]

    print("=" * 72)
    print("REGRESSION DELTA — baseline vs new run")
    print("=" * 72)
    print("Baseline XMLs:")
    for p in BASELINE:
        print(f"  {p.name}")
    print("New XMLs:")
    for p in new_paths:
        print(f"  {p}")
    print()

    base = load(BASELINE)
    new = load(new_paths)

    base_failed = {t for t, o in base.items() if o == "failed"}
    base_passed = {t for t, o in base.items() if o == "passed"}
    new_failed = {t for t, o in new.items() if o == "failed"}
    new_passed = {t for t, o in new.items() if o == "passed"}

    known_still_failing = sorted(t for t in new_failed if matches_known(t))
    known_now_passing = sorted(t for t in new_passed if matches_known(t))
    known_not_run = sorted(
        k for k in KNOWN_PRE_EXISTING
        if not any(t.endswith(k) or k.endswith(t) for t in new))

    regressions = sorted(base_passed & new_failed)
    documented_outside = sorted(
        t for t in new_failed
        if any(t.endswith(k) for k in KNOWN_PRE_EXISTING_OUTSIDE_BASELINE))
    unknown_new_failures = sorted(
        t for t in new_failed
        if t not in base_failed
        and not matches_known(t)
        and t not in documented_outside)
    missing_from_new = sorted(set(base) - set(new))
    added_in_new = sorted(set(new) - set(base))

    out = {
        "baseline": {
            "files": [p.name for p in BASELINE],
            "unique_tests": len(base),
            "passed": len(base_passed),
            "failed": len(base_failed),
            "failed_ids": sorted(base_failed),
        },
        "new_run": {
            "files": [str(p) for p in new_paths],
            "unique_tests": len(new),
            "passed": len(new_passed),
            "failed": len(new_failed),
            "failed_ids": sorted(new_failed),
        },
        "known_pre_existing_still_failing": known_still_failing,
        "known_pre_existing_now_passing": known_now_passing,
        "known_pre_existing_not_executed": known_not_run,
        "pre_existing_outside_baseline_selection": {
            t: next(v for k, v in KNOWN_PRE_EXISTING_OUTSIDE_BASELINE.items()
                    if t.endswith(k))
            for t in documented_outside
        },
        "regressions_previously_passing_now_failing": regressions,
        "new_failures_not_in_baseline": unknown_new_failures,
        "baseline_tests_missing_from_new_run": missing_from_new,
        "tests_added_since_baseline": added_in_new,
    }
    out["verdict"] = {
        # The question the gate actually asks: did anything that used to
        # pass stop passing, or did an undocumented failure appear?
        "no_new_regressions": not regressions and not unknown_new_failures,
        "baseline_fully_covered": not missing_from_new,
        "known_failures_still_failing": len(known_still_failing),
        "known_failures_now_fixed": known_now_passing,
        "documented_pre_existing_outside_baseline": len(documented_outside),
    }

    print(f"baseline : {len(base)} unique — {len(base_passed)} passed, "
          f"{len(base_failed)} failed")
    print(f"new run  : {len(new)} unique — {len(new_passed)} passed, "
          f"{len(new_failed)} failed")
    print()
    print(f"[{'PASS' if out['verdict']['known_failures_still_failing'] == len(known_still_failing) else 'CHECK'}] "
          f"known pre-existing failures still failing: {len(known_still_failing)}/4")
    for t in known_still_failing:
        print(f"       - {t}")
    if known_now_passing:
        print(f"       now PASSING (baseline shifted): {known_now_passing}")
    if known_not_run:
        print(f"       NOT EXECUTED in new run: {known_not_run}")
    print()
    print(f"[{'PASS' if not regressions else 'FAIL'}] "
          f"previously-passing tests now failing: {len(regressions)}")
    for t in regressions:
        print(f"       - {t}")
    print()
    print(f"[{'PASS' if not unknown_new_failures else 'FAIL'}] "
          f"new failures not in baseline: {len(unknown_new_failures)}")
    for t in unknown_new_failures:
        print(f"       - {t}")
    print()
    print(f"[note] failing but documented pre-existing OUTSIDE the baseline "
          f"selection: {len(documented_outside)}")
    for t in documented_outside:
        print(f"       - {t}")
        why = next(v for k, v in KNOWN_PRE_EXISTING_OUTSIDE_BASELINE.items()
                   if t.endswith(k))
        print(f"         evidence: {why}")
    print()
    print(f"[{'PASS' if not missing_from_new else 'CHECK'}] "
          f"baseline tests missing from new run: {len(missing_from_new)}")
    for t in missing_from_new[:25]:
        print(f"       - {t}")
    if len(missing_from_new) > 25:
        print(f"       ... and {len(missing_from_new) - 25} more")
    print()
    print(f"tests added since baseline: {len(added_in_new)}")
    print()
    print(f"VERDICT: {json.dumps(out['verdict'])}")

    dest = REPORTS / "gate_regression_delta.json"
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"JSON: {dest}")


if __name__ == "__main__":
    main()
