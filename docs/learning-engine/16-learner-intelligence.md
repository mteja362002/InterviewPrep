# 16 · Learner Intelligence Engine (Phase 2C)

> Company Intelligence answers **"What should matter?"**
> Learner Intelligence answers **"What does THIS learner need today?"**

Phase 2C introduces **Learner Intelligence** as a first-class, deterministic
runtime component that continuously models *how* a learner learns and exposes
it to the Adaptive Planner as an additional, bounded scoring input. It adds
**no user-visible features** — it strengthens the adaptive brain that future
features (Mock Interviews, Company Readiness, AI Mentor personalization,
Predictive Analytics, Resume Guidance) will consume.

- **No AI. No LLMs. No ML. No prediction models. No randomness.** Everything
  is a transparent, reproducible function of existing data.
- **No new MongoDB collections.** Every signal is derived from the canonical
  `knowledge_nodes` progress rows and the recent-mission history the planner
  already assembles.
- **Backward compatible.** Disabled by default; when disabled or when the
  snapshot is empty, scoring is byte-identical to Phase 2B and the planner
  falls back automatically.

---

## 1. Architecture

```
Knowledge Graph
      │
      ▼
Learner Context ──────────────► Learner Intelligence (snapshot, compute-once)
      │                                    │
      ▼                                    ▼
Company Context                     planner_adapter (bounded per-node signal)
      │                                    │
      ▼                                    ▼
Adaptive Planner  ◄── Learning Score + Company Score + Learner Intelligence Score
      │
      ▼
Mission Generation
```

The engine lives in its own package and is **not** coupled into `planner.py`:

```
backend/services/learner_intelligence/
    metrics.py          # pure helpers + canonical label vocabulary
    trend_analysis.py   # deterministic split-mean trend detection
    context.py          # LearnerIntelligenceInput (raw signal bundle)
    velocity.py         # (1) learning velocity
    retention.py        # (2) retention quality
    confidence.py       # (3) confidence trend
    weakness.py         # (4) weakness stability (per track)
    consistency.py      # (5) learning consistency
    revision_health.py  # (6) revision health
    coding.py           # (7) coding growth
    mastery_trend.py    # (8) topic mastery trend (per track)
    difficulty.py       # (9) difficulty adaptation
    readiness.py        # (10) interview readiness trend
    snapshot.py         # aggregate snapshot (compute-once view)
    engine.py           # COMPUTATION pipeline (build snapshot)
    planner_adapter.py  # CONSUMPTION pipeline (bounded scoring nudge)
    explainability.py   # reasons derived from the same signals
```

**Separation of concerns:** the *computation* pipeline (`engine.py`) produces
the snapshot once; the *consumption* pipeline (`planner_adapter.py`) turns it
into a scoring nudge for one node. Analytics / AI Mentor / readiness features
can reuse the same snapshot without duplicating any metric math.

---

## 2. Metrics (the ten signals)

| # | Signal | Module | Key outputs |
|---|--------|--------|-------------|
| 1 | Learning Velocity | `velocity.py` | topics/7d, avg/week, speed trend, `speed_score` |
| 2 | Retention Quality | `retention.py` | revision success/fail, repeated mistakes, `knowledge_stability`, trend |
| 3 | Confidence Trend | `confidence.py` | `increasing / stable / declining / rapid_improvement / rapid_decline` |
| 4 | Weakness Stability | `weakness.py` | per track: `temporary / persistent / recovered / recurring` |
| 5 | Learning Consistency | `consistency.py` | streak, missed days, `completion_consistency`, skipped, trend |
| 6 | Revision Health | `revision_health.py` | debt, backlog, avg overdue days, completion rate, `debt_level` |
| 7 | Coding Growth | `coding.py` | difficulty progression, acceptance trend, repeated mistakes |
| 8 | Topic Mastery Trend | `mastery_trend.py` | per track: `learning / improving / plateau / regressing / mastered` |
| 9 | Difficulty Adaptation | `difficulty.py` | `maintain / increase / decrease` (never reorders roadmap) |
| 10 | Interview Readiness Trend | `readiness.py` | trajectory `upward / stable / declining`, 0–1 `score` |

**Trend detection** (`trend_analysis.py`) is a *split-mean delta*: compare the
mean of the recent half of a chronological series to the older half, then map
the delta onto the canonical vocabulary. O(n), zero dependencies, fully
explainable, deterministic.

---

## 3. Computation pipeline

```
LearnerIntelligenceInput            # raw rows the planner already loaded
  progress_rows                     # knowledge_nodes rows
  recent_completions (newest-first)
  completed_dates
  recent_track_ids
  skipped_node_ids
  position
        │  engine.build_learner_intelligence(inp)
        ▼
LearnerIntelligenceSnapshot         # compute-once aggregate (10 signals)
  .is_empty  → planner fallback sentinel
  .to_dict() → JSON-safe (analytics / AI Mentor / debugging)
```

- Empty / garbage input ⇒ `empty_snapshot()` (never raises).
- `build_snapshot(..., precomputed=<snapshot>)` accepts an injected snapshot —
  the **event-driven cache hook** (see §6).

---

## 4. Planner integration

`build_learner_context(...)` builds the snapshot once (mirroring how
`company_context` is built) and stores it on `LearnerContext`:

```python
LearnerContext.learner_intelligence          # the snapshot
LearnerContext.learner_intelligence_enabled  # opt-in flag (default False)
```

The canonical scoring formula (`ranking.score_learning_node`) adds one bounded
term, active only when opted in **and** the snapshot is non-empty:

```
total_score = knowledge_gap + company_score
            + company_intelligence_score * w[...]
            + learner_intelligence_score  * w["learner_intelligence_score"]   # Phase 2C
            + ...
```

- The raw signal from `planner_adapter.learner_intelligence_signal()` is
  clamped to **[-3, +3]**; with `learner_intelligence_score = 5.0` the
  contribution stays in the same order of magnitude as Company Intelligence and
  is far below the core `knowledge_gap` (up to ~100). **The learner remains
  highest priority** — this term only refines *which* learner-relevant node
  wins, it never out-shouts the fundamentals.
- Opt-in is enabled in `routes_missions.py` via
  `get_today_learning_node(..., learner_intelligence=True)`.

**Per-node signal terms:** persistent/recurring weakness on the node's track
(+), regressing/plateau mastery (+), mastered mastery (−, gentle), difficulty
adaptation vs the node's difficulty (±), and a hard-node overload guard when
velocity is declining (−).

---

## 5. Explainability

Every reason is derived from the same signals that influenced the score, so an
explanation can never contradict the ranking. Surfaced on the existing
Recommendation Insight (`insight.py`) under `learner_intelligence` (snapshot
summary) and `learner_intelligence_factors` (per-node contributions).

```
Today's Mission: Sliding Window
Reason:
  • Weak topic
  • High revision debt
  • Learning velocity slowing
  • Consistency improving
  • Difficulty maintained
Confidence: High
Readiness trajectory: upward
```

---

## 6. Performance considerations

- All signals are **O(n)** over the rows the planner already holds. The
  snapshot is computed **once per context build**, not per candidate — the
  scoring adapter only *reads* it.
- Because the cost is negligible, the snapshot is an in-memory computed view;
  **no cache and no new storage** were introduced.
- Metrics only change after a mission completion, coding submission, or
  revision. For a future high-scale deployment those events can recompute and
  persist a snapshot which is then injected via `build_snapshot(precomputed=…)`
  — the hook already exists, so no consumer code changes when caching is added.

---

## 7. Future extension points

- **Coding Growth** currently infers acceptance/pattern trends from mastery on
  attempted nodes because PrepOS has no per-submission acceptance log. A Phase 3
  submission store can feed richer acceptance/pattern-mastery trends through the
  same `CodingGrowth` shape.
- **AI Mentor personalization / Predictive Analytics / Mock Interviews** should
  consume `LearnerIntelligenceSnapshot.to_dict()` directly rather than
  recomputing.
- New signals are additive: add a module + a field on the snapshot + (optional)
  a term in `planner_adapter` and a weight in `adaptive_weights` — no planner
  redesign.

---

## 8. Backward compatibility & determinism

- Disabled by default ⇒ `learner_intelligence_score == 0.0` and byte-identical
  scoring to Phase 2B.
- The engine and adapter never raise; any failure degrades to the empty
  snapshot and the planner falls back.
- Same input ⇒ same snapshot ⇒ same recommendation, always (the only time
  source is `metrics.today_utc()`).
