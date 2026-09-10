# Final Verification Gate — Mission Semantics + AI Generation Performance

**Date:** 2026-09-10
**Scope:** verification pass only. No unrelated changes were made.
**Sprint status:** **NOT CLOSED.** Four items require runtime execution on the Windows host.

Two real defects were found and corrected during this pass. Both were in the
sprint's own blast radius, both are covered by new deterministic regression
tests, and both were proved by executing real source in a sandbox.

---

## Executive summary

| # | Gate item | Result |
|---|-----------|--------|
| 1 | `effectively_completed` vs legacy provenance | **DEFECT FOUND → FIXED** + regression test |
| 2 | User 5 runtime evidence | **UNVERIFIED** — harness ready |
| 3 | Candidate-pool vs ranking behaviour | **PASS** — proved by zero-diff on ranking |
| 4 | Broader regression suite | **PARTIAL PASS** — pre-fix delta clean; post-fix run pending |
| 5 | AI generation latency measurement | **UNVERIFIED** — harness ready |
| 6 | Single-flight scope | **PASS** — process-local, adequate, now documented |
| 7 | Deterministic prerequisites / related topics | **DEFECT FOUND → FIXED** + regression test |
| 8 | Honest generation UX (manual) | **UNVERIFIED** — checklist provided |
| 9 | Performance conclusion | **No actual latency improvement demonstrated** |

---

## 1. `effectively_completed` vs legacy provenance — DEFECT FOUND AND FIXED

### The defect

`services/evidence.py::planner_row` collapsed *per-field* certification into a
*row-level* provenance stamp:

```python
# BEFORE (defective)
return {**row, **certified_fields(row),
        "planner_progress_source": ACTUAL if certified_fields(row)
        else row.get("planner_progress_source", LEGACY)}
```

`certified_fields(row)` is truthy if **any** field carries a certified source.
So an `attempt` write (certifying `attempts`), a `revision` write (certifying
`next_revision`), or a `confidence_update` would stamp the whole row
`certified_actual` — including a `status` field that was never certified.

This is exactly the hazard the gate names: a historical `UNVERIFIED_LEGACY` row
becoming certified actual evidence without any certified completion. The
architecture already defended against this at the write boundary
(`progress_repository.upsert_progress_fields` writes per-field
`field_sources[key]`, docstring: *"Per-field stamps prevent a status/revision
update from certifying old mastery"*) — and the read boundary undid it.

Three production-reachable writers could trigger it: attempt recording,
revision scheduling, and confidence updates.

### The fix (smallest corrective change — 1 line of logic)

```python
# AFTER
certified = certified_fields(row)
return {**row, **certified,
        "planner_progress_source": ACTUAL if "status" in certified
        else row.get("planner_progress_source", LEGACY)}
```

The stamp is now earned by the `status` field specifically. Consumers read
`planner_progress_source == ACTUAL` to mean *"this node's completion is
certified"*, so only a certified `status` may grant it.

### Proof the three states stay distinct

`backend/scratch_verify_provenance_gate.py` runs the **real**
`_derive_subject_status` and **real** `services.evidence`:

- **Before the fix:** 11/12 — `HAZARD CONFIRMED`
- **After the fix:** **12/12 — SAFE**

Sections cover: (A) the three provenance states resolve distinctly;
(B) `not onboarding_baseline` is *not* treated as certified actual, across five
bogus source values; (C) a laundering probe; (D) a control proving certified
status still works.

`_derive_subject_status` itself was already safe — it asks the *positive*
question (`has_actual_completion`), never `not onboarding_baseline`:

```python
has_actual_completion = any(
    status in _COMPLETED_STATUSES
    and progress.get("planner_progress_source") == "certified_actual"
    for n in track_nodes)
if has_actual_completion:
    return "completed"
return "effectively_completed"
```

Only a stale comment was corrected there; no logic changed.

### Regression test

`tests/test_provenance_status_regression.py` →
`TestPlannerStampIsEarnedByStatusField`, covering:

- 5 parametrised cases: non-status certification must not earn the stamp
  (`attempts`/attempt, `actual_solve_minutes`/attempt,
  `next_revision`+`revision_stage`/revision, `last_revision`/revision,
  `confidence`/confidence_update)
- 3 parametrised cases: legacy completion survives an unrelated certified write
- certified `status` still earns the stamp and still resolves to `completed`
- `onboarding_baseline` is preserved, never downgraded

---

## 2. User 5 runtime evidence — UNVERIFIED

Cannot be executed here: no network egress to MongoDB Atlas, and the venv holds
Windows-only `cp311-win_amd64.pyd` binaries. **I will not fabricate these
numbers.**

`backend/scratch_gate_user5.py` is ready. Unlike the existing
`scratch_diagnose_user5.py` (synthetic profile + FakeDB), it reads the **real**
`users` / `onboarding` / `knowledge_nodes` rows for
`teja.2019.ece@anits.edu.in` and reproduces the production read path from
`routes_missions._generate_today_mission`. It is strictly read-only.

It captures every field the gate asks for: eligible candidate count, advanced
technical candidate count, selected task plans, selected tracks, priority/reason
codes, plus a stored-vs-derived provenance census, and asserts ten checks
including *"Behavioral not selected merely by fallback"*, per-track availability
for DSA/LLD/HLD/Core CS, and a beginner control for regression. It does **not**
require any exact mission title.

---

## 3. Candidate-pool vs ranking behaviour — PASS

Proved by measurement, not inspection. Using whitespace/CRLF-insensitive diff
(`git diff HEAD --numstat --ignore-cr-at-eol -w`), the complete set of files
with real changes is **7**:

```
135  3  backend/knowledge_generation.py
 12  2  backend/services/evidence.py
  9  4  backend/services/learning_engine/eligibility.py
 20  7  backend/services/learning_engine/planner.py
 61 11  backend/services/learning_engine/subject_progression.py
 72  4  frontend/src/components/knowledge/AIContentTabs.jsx
 27  6  frontend/src/pages/ai-mentor/AIMentor.jsx
```

`ranking.py`, `priority_engine.py`, `candidates.py` and `mission_engine.py` have
**zero** real changes. The 9 → 124 candidate growth therefore cannot be
attributable to ranking-weight tuning; it comes from `eligibility.py` +
`subject_progression.py` — that is, the eligibility/session-selection
correction, exactly as claimed.

A plain `git diff --stat` is misleading here: repo-wide CRLF churn makes ~300
files appear modified. The `-w --ignore-cr-at-eol` flags are required to see the
truth.

**No new profile-specific or subject-specific hardcoding** was introduced. The
one subject-specific branch in the engine (`composition.py:127`) is pre-existing
and untouched.

---

## 4. Broader regression suite — PARTIAL PASS

### Baseline reconciled

The "188 passed / 4 pre-existing failures" figure is the union of two runs
recorded 2026-09-09:

```
baseline_semantic_sprint_focused.xml      34 tests  @19:50:13
baseline_semantic_sprint_regression.xml  158 tests  @19:51:25
                                  union  192 unique → 188 passed / 4 failed
```

### Delta against the sprint's own post-change runs

`backend/scratch_gate_compare_regression.py` compares by **test identity**, not
failure count — because "4 before, 4 after" is a coincidence of count, not proof
of sameness. Result (380 unique tests, from `provenance_broad_final.xml` +
`provenance_focused.xml`):

```
no_new_regressions                     : true
baseline_fully_covered                 : true   (0 baseline tests missing)
previously-passing now failing         : 0
known failures still failing           : 3 / 4
known failures now FIXED               : test_onboarding_knowledge_seed::
                                         test_seed_covers_every_roadmap_track_with_stage_aware_rows
```

So the failure sets are **not** identical — one of the four pre-existing
failures was *fixed* by the sprint. That is an improvement, not a regression,
but it means the "4 = 4" framing was never load-bearing.

### One failure needed adjudication

`test_mission_roadmap_catalog::test_candidate_ranking_uses_seeded_rng_for_exact_ties`
fails in the post-change runs and is **absent from the 192-test baseline
selection**, so a naive diff flags it as new. It is not:

- It was already failing in `learner_audit_extended.xml` at **19:19:26**, i.e.
  **31 minutes before** the baseline was recorded at 19:50:13.
- It exercises `mission_engine.rank_candidate_topics`, which has **zero** real
  changes in this sprint.
- Cause is test/implementation coupling: the test asserts
  `rank_candidate_topics` consumes the seeded RNG exactly like a bare
  `rng.choice()`. Unrelated to provenance or session selection.

Pre-existing, outside the baseline selection. Documented with evidence in the
comparator rather than silently suppressed.

### Why this is PARTIAL, not PASS

Those XMLs pre-date the two corrective fixes made during *this* gate. The
Windows run must confirm the fixes introduce no regressions, and must execute
the two new test files under **real pytest** — my sandbox verification used a
hand-rolled shim because pytest could not be installed (no network egress).

**I am explicitly not claiming "zero regressions" on the strength of the focused
tests.** The focused suite (34 tests) and the broader suite (380+) are reported
separately throughout.

---

## 5. AI generation latency — UNVERIFIED (instrumentation confirmed complete)

All five requested fields exist and are correctly placed in
`knowledge_generation.py`: `cache_check_ms` (L144), `generation_ms` (L187),
`parse_ms` (L192), `persist_ms` (L226), `total_ms` (L228), plus `cache_hit` and
`waited_for_lock`.

`_timing` is attached to `doc` *after* the Mongo `$set`, so timing data is
correctly **not** persisted into the cache.

Two instrumentation gaps worth knowing (neither blocks the gate):

1. `cache_check_ms` is never set on the `force=True` path, since the first cache
   check is skipped.
2. `waited_for_lock` is only stamped when the waiter's post-lock cache re-check
   *hits*. If the lock winner errors, the waiter generates and the flag is
   absent — so absence of the flag does not prove absence of waiting. There is
   no `lock_wait_ms`.

`backend/scratch_gate_ai_timing.py` measures all three required scenarios
against the real provider and real DB, wrapping `ai_service.complete` in a
counting proxy that **delegates to the real function** so latency stays genuine
while calls stay countable. It asserts `provider calls == 1` for the concurrent
case and reports which request saw `waited_for_lock`.

---

## 6. Single-flight scope — PASS (limitation documented, no new infrastructure)

`_generation_locks` is a module-global `dict[(node_id, roadmap_version),
asyncio.Lock]` — **process-local**.

Deployment topology evidence: `uvicorn==0.25.0` appears in
`backend/requirements.txt`, and the repo contains **no Dockerfile, no
docker-compose, no Procfile, no gunicorn, no `--workers` flag, and no
`WEB_CONCURRENCY`** anywhere. That is the default single-process server, for
which a process-local lock is sufficient.

Per the gate's instruction I documented the limitation in code rather than
building distributed locking:

```python
# SCOPE LIMITATION — this is a PROCESS-LOCAL lock.
# ... If the backend is ever run with multiple worker processes (uvicorn
# --workers N, gunicorn, or >1 container replica), each process keeps its own
# `_generation_locks` dict and N concurrent first-requests for the same node
# would produce up to N provider calls.
# ...
# Correctness does not depend on the lock in any case — the cache is keyed on
# (node_id, roadmap_version) and the write is an idempotent upsert, so the
# worst multi-process outcome is redundant cost, never corruption.
```

**No distributed locking was introduced.** The deployment does not require it.

---

## 7. Deterministic prerequisites / related topics — DEFECT FOUND AND FIXED

### The defect

The authority hierarchy was **inverted**. The original merge placed AI entries
first and let them win id collisions, commented *"AI-generated entries take
priority; deterministic fill gaps."* A model response could therefore redefine,
reorder ahead of, or silently replace an authored curriculum edge — the precise
failure the gate asks about.

### The fix

Extracted the inline merge into a pure, testable function with canonical
entries first, winning every id collision, and a `source` marker
(`"roadmap"` | `"ai"`) so consumers can distinguish the tiers:

```python
return {
    "related_topics": canonical_related + [
        {**r, "source": "ai"} for r in ai_related
        if r.get("id") not in canonical_related_ids],
    "prerequisites": canonical_prereqs + [
        {**p, "source": "ai"} for p in ai_prereqs
        if p.get("id") not in canonical_prereq_ids],
}
```

Enrichment still works — AI may **add** edges the roadmap lacks. It simply
cannot override authored ones. Resulting hierarchy is exactly as specified:
canonical roadmap prerequisites → authoritative; AI suggestions →
supplementary.

### Regression test

`tests/test_canonical_relationship_authority.py` — **9 tests, 9 passed**, run
against real extracted source via
`backend/scratch_verify_canonical_authority.py` (AST-extracts the two pure
helpers so the genuine source text executes without pydantic).

Covers: AI cannot redefine a canonical prerequisite or related topic; canonical
entries come first; AI-only entries survive as supplementary; empty/None AI
output leaves canonical intact; AI cannot empty the canonical list; merge is
deterministic; `_deterministic_related` stamps provenance; unknown canonical ids
are dropped rather than invented.

---

## 8. Honest generation UX — UNVERIFIED (no browser in this environment)

Source review found the imports and structures intact (`Sparkles` used 6×, `cn`
imported in both components), but **rendered behaviour cannot be verified
without a browser.** Manual checklist is in the handoff section below.

---

## 9. Performance conclusion

### Actual latency improvement — NOT DEMONSTRATED

No measurement in this pass shows first-generation latency falling. The
`generation_ms` phase is a synchronous call to the external provider and the
sprint changed nothing about the provider, the model, the prompt size, or the
call pattern. The prior audit recorded provider attempts of **2.8 s – 13.2 s**,
with a full chain failing after 44.5 s.

**Provider generation remains the dominant latency.** Everything else in the
measured path — cache check, parse, persist — is sub-millisecond to
low-millisecond by comparison. The harness will quantify
`provider_share_of_total`; I expect it to be well above 0.95.

### What genuinely improved

- **Perceived latency / UX.** The skeleton and the animated typing indicator
  appear immediately, replacing a blank or stuck state. This is a real
  improvement, and it is a *perceptual* one.
- **Cost and provider load.** Single-flight collapses N concurrent
  first-requests for the same node into 1 provider call. Note this is primarily
  a **cost** win: the second concurrent request still waits for the first
  generation, so its wall time is comparable — it just doesn't pay for a
  duplicate call.
- **Correctness of curriculum relationships**, per item 7.

### One claim to retire

Deterministic prerequisites/related topics do **not** improve latency, actual or
perceived, in the current UI. `_deterministic_related` is computed *inside* the
lock immediately before the AI call and merged *after* it, and
`AIContentTabs.jsx` renders both sections from the same generated `content`
object (L253–254). They are never served before generation completes. Their
value is **reliability and authority**, not speed. Serving them early would be a
genuine perceived-latency win — but that is a future change, not this sprint.

---

## 10. Files changed

Seven files, all in scope. `+336 / −37`.

| File | Change |
|------|--------|
| `backend/services/evidence.py` | **Fix:** stamp earned by `status` field, not any field |
| `backend/services/learning_engine/subject_progression.py` | Sprint work; this pass corrected a stale comment only |
| `backend/services/learning_engine/eligibility.py` | Sprint work, unmodified by this pass |
| `backend/services/learning_engine/planner.py` | Sprint work, unmodified by this pass |
| `backend/knowledge_generation.py` | **Fix:** `_merge_relationships` authority; **doc:** lock scope limitation |
| `frontend/src/components/knowledge/AIContentTabs.jsx` | Sprint work, unmodified by this pass |
| `frontend/src/pages/ai-mentor/AIMentor.jsx` | Sprint work, unmodified by this pass |

**Added this pass** — tests and disposable harness (all `scratch_`-prefixed or
under `tests/`):

- `tests/test_provenance_status_regression.py` (extended)
- `tests/test_canonical_relationship_authority.py` (new, 9 tests)
- `scratch_gate_user5.py`, `scratch_gate_ai_timing.py`,
  `scratch_gate_compare_regression.py`, `run_verification_gate.ps1`
- `scratch_verify_provenance_gate.py`, `scratch_verify_canonical_authority.py`,
  `scratch_minipytest.py`

---

## 11. Remaining limitations

1. **Four gate items are unexecuted** (2, 5, 8, and the post-fix half of 4).
   Blocked by: no network egress to Atlas or the AI providers; a Windows-only
   venv; no browser.
2. **The two new test files have never run under real pytest** — only under a
   hand-rolled shim that supports `parametrize` and plain asserts but *not*
   fixtures.
3. **Single-flight is process-local.** Fine today; breaks silently into extra
   cost if workers are ever added. Now documented at the definition site.
4. `cache_check_ms` is unset on the `force=True` path; `waited_for_lock` can be
   absent for a request that genuinely waited; no `lock_wait_ms` exists.
5. **Deterministic sections are not served early**, so they contribute nothing
   to perceived latency (item 9).
6. One of the four "pre-existing failures" is now fixed, so that baseline
   description is stale going forward.
7. `backend/.env` holds live credentials (Atlas URI, JWT secret, OpenRouter and
   Gemini keys, SMTP password). Nothing in this harness prints, logs, or writes
   any secret value. Keep it out of commits and out of pasted output.

---

## 12. Final PASS / FAIL invariants

**Verified PASS**

- A row is certified actual **only** when its `status` field carries a certified
  source. *(12/12, executed against real source)*
- `ONBOARDING_BASELINE`, `CERTIFIED_ACTUAL` and `UNVERIFIED_LEGACY` remain
  three distinct states.
- `not onboarding_baseline` is never treated as certified actual.
- An `UNVERIFIED_LEGACY` row cannot become certified evidence via an unrelated
  attempt/revision/confidence write.
- Canonical roadmap prerequisites and related topics are authoritative; AI
  output cannot replace, reorder ahead of, or empty them. *(9/9)*
- AI enrichment still adds edges the roadmap lacks, tagged `source: "ai"`.
- The candidate-pool improvement came from eligibility/session selection, not
  ranking weights. *(zero-diff proof)*
- No new profile-specific or subject-specific hardcoding.
- Single-flight lock scope is process-local, adequate for the current
  single-process deployment, and documented.
- No previously-passing test regressed in the sprint's recorded post-change runs
  (380 unique tests, full baseline coverage).

**Cannot be asserted without the Windows run**

- User 5 produces a non-empty structured session pipeline with advanced
  technical candidates and no beginner regression.
- Cold-generation, cache-hit and concurrent timing figures.
- `provider calls == 1` under real concurrency.
- The two new test files pass under real pytest.
- The two fixes introduce no regressions.
- KB and Mentor visual behaviour.

**Asserted FAIL / negative findings**

- ❌ **Actual first-generation latency improvement is NOT demonstrated.**
  Provider generation remains the dominant cost.
- ❌ Deterministic prerequisites/related topics do **not** reduce latency,
  actual or perceived, in the current UI.

---

## Handoff — run this on Windows

```powershell
cd C:\Users\Teja\Downloads\InterviewPrep-Test\InterviewPrep\backend
powershell -ExecutionPolicy Bypass -File .\run_verification_gate.ps1
```

Step 5 spends real API credits (two KB generations) and pauses 5 seconds first
so you can Ctrl-C to skip. Steps 4–5 read the live database; step 4 is
read-only.

If you prefer to run the steps individually:

```powershell
# 1. the two new regression files, under REAL pytest (pytest.ini pins -n 2; do not override)
python -m pytest tests/test_provenance_status_regression.py tests/test_canonical_relationship_authority.py -v --junitxml=..\test_reports\gate_new_tests.xml

# 2. broader regression suite
python -m pytest tests/ -q --junitxml=..\test_reports\gate_full_suite.xml

# 3. identity-level delta vs the 192-test baseline
python scratch_gate_compare_regression.py ..\test_reports\gate_full_suite.xml ..\test_reports\gate_new_tests.xml

# 4. User 5 runtime capture (read-only)
python scratch_gate_user5.py

# 5. AI timing matrix (real provider, ~2 calls)
python scratch_gate_ai_timing.py
```

Paste back `test_reports\gate_console.txt` plus `gate_regression_delta.json`,
`gate_user5.json` and `gate_ai_timing.json`, and I will complete items 2, 4, 5
and 9 with real numbers.

### Manual checklist for item 8

**Knowledge Base generation** — open an ungenerated topic:

- skeleton appears immediately, no blank or stuck state
- no fabricated percentage progress
- no fabricated model reasoning text
- generation state reads honestly
- clicking generate twice does not start a second generation
- completed content replaces the skeleton cleanly
- forcing an error (kill network mid-generation) clears the loading state
- retry works after that error
- route, tab and scroll state survive generation

**AI Mentor** — send a message:

- animated typing indicator appears immediately
- it disappears when the response arrives
- no synthetic typing message is persisted into history
- no duplicate indicator on rapid sends
- an error clears the sending state
- retry works if supported

---

## Bottom line

**Track A (mission semantics / provenance)** — the architectural direction is
right, and the move from overloaded `"completed"` to `"effectively_completed"`
is sound. But the read boundary contained a real provenance-laundering defect
that would have quietly converted legacy rows into certified evidence. It is
fixed and regression-tested. Runtime confirmation on User 5 is still required.

**Track B (AI generation performance)** — the UX work and the single-flight and
deterministic-content changes are good, and item 7 fixed a genuine correctness
bug in them. But the central question stands where you left it: **we still have
not demonstrated that the actual 5–10 second latency improved**, and on the
evidence available it almost certainly did not. What improved is perceived
latency, cost, and correctness. The harness will settle it with numbers.

**Recommendation: do not close the sprint yet.** Run the harness.
