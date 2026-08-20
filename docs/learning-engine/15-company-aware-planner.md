## Phase 2B — Company-Aware Adaptive Planner

> **Status:** Company Intelligence is now an ACTIVE, bounded, deterministic
> planner signal. Learner intelligence remains dominant. The change is opt-in
> and falls back automatically when Company Intelligence is unavailable.

---

### 1. Architecture

```
Roadmap ──► roadmap.company_importance()  ─┐
                                            ├─► score_learning_node ─► Planner ─► Mission
Compiled Company Intelligence artifacts     │        ▲
   │  (Phase 1 loader, JSON only)           │        │  company_intelligence_score term
   ▼                                        │        │
CompanyContext (Phase 2A) ──► Company Weight Engine (Phase 2B) ─┘
                                  ├─ scoring.py         (subject importance × confidence × level × bias)
                                  ├─ bias_engine.py     (bounded priority multiplier)
                                  └─ explainability.py  (per-company reasons + confidence)
```

The Company Weight Engine lives in `backend/company_intelligence/` and consumes a
**duck-typed CompanyContext** — it never imports the learning engine, preserving
clean layering (higher layer → lower layer only). It reads **only** compiled
runtime artifacts (never markdown).

---

### 2. Company Scoring Pipeline

For a candidate node, `compute_company_intelligence_signal(company_context, node, level)`:

```
signal = mean_over_selected_companies( importance × confidence × level_factor )
         × company_bias_multiplier
```

- **importance** — compiled `subjects[subject]` label → scalar
  (Critical 1.0 … Very Low 0.15; unknown → neutral 0.5).
- **confidence** — profile evidence confidence → scalar
  (High 1.0 … Low 0.6; unknown → 0.8). Uncertain evidence contributes less —
  Company Intelligence never converts Medium/Low confidence into a dominant push.
- **level_factor** — experience-aware. Design subjects (HLD/LLD) are suppressed
  for juniors (`new_grad` 0.6 → `staff` 1.2) so advanced design is never forced
  onto a beginner. Non-design subjects use 1.0.
- **company_bias_multiplier** — bounded `[0.85, 1.15]`: a subject earlier in a
  company's planning-priority hierarchy gets a mild boost.

Track→subject aliasing (`hld→high_level_design`, `lld→low_level_design`) is
curriculum-structural, not company-specific. No company ids are hardcoded.

---

### 3. Planner Integration & Weight Calculation

One new weighted term is added inside `ranking.score_learning_node`:

```
total_score = … + company_score × 3.0            # roadmap.company_importance (unchanged)
                + company_intelligence_score × 6.0 # NEW, Phase 2B
                + …
```

`company_intelligence_score` is bounded (~0…1.3), so its weighted contribution is
~0…8 points — modest next to `knowledge_gap` (up to ~100) and
`subject_transition_bonus` (100). **Company Intelligence influences ordering and
ties; it never overrides a strong learner signal.**

**Activation is opt-in.** `LearnerContext.company_intelligence_enabled` (default
`False`) gates the term. `get_today_learning_node(..., company_intelligence=…)`
sets it; the real mission route (`routes_missions.py`) passes `True`. Existing
callers/tests that don't opt in get byte-identical scores.

---

### 4. Signals Implemented

| Signal | Source | Effect in Phase 2B |
|---|---|---|
| Subject Importance | `subjects` | primary driver of the CI term |
| Evaluation / Behavioral signals | `signals` | preserved in CompanyContext; surfaced for explainability (composition changes deferred to a later phase) |
| Adaptive Biases (priority) | `planner.priority` | bounded multiplier |
| Experience Level | onboarding `current_position` | `level_factor` (juniors ≠ staff) |
| Role Differences | `levels` | available in CompanyContext for future role-aware weighting |
| System Design gating | level + existing prerequisite/eligibility guards | juniors' design emphasis suppressed |
| Negative evidence / contradictions | `summary` (preserved) + confidence | confidence scaling prevents over-prioritising uncertain evidence |

---

### 5. Fallback Behavior

The CI term is `0.0` (planner reverts to roadmap-only `company_score`) whenever:
- Company Intelligence is not enabled, **or**
- `company_context` is empty (no selection, or only UI-only/unknown ids like `others`), **or**
- any exception occurs while computing the signal (wrapped in a defensive
  `try/except` in `score_learning_node`).

No crashes, no partial state — deterministic fallback.

---

### 6. Explainability

`score_learning_node` returns a `company_intelligence` block:

```json
{
  "top_company": "google",
  "confidence": "Medium",
  "reasons": ["Critical importance for Google (Dsa, Medium confidence)"],
  "companies": [{"company_id": "google", "subject": "dsa", "importance": "Critical",
                 "confidence": "Medium", "level": "new_grad", "contribution": 0.92}]
}
```

`insight.py` surfaces the top reason as a highlight and includes the full block
in the "Why this mission?" payload. The lowest confidence across companies is
exposed (never inflated). Every company contribution is visible — no black box.

---

### 7. Files

**Added:** `backend/company_intelligence/scoring.py`, `bias_engine.py`,
`explainability.py`; `backend/tests/test_company_aware_planner_phase2b.py`.

**Modified (minimal, additive):**
`services/learning_engine/adaptive_weights.py` (+1 weight),
`services/learning_engine/context.py` (+`company_intelligence_enabled` flag),
`services/learning_engine/ranking.py` (+CI term + breakdown fields),
`services/learning_engine/planner.py` (+opt-in param),
`services/learning_engine/insight.py` (+CI explainability, guarded),
`routes_missions.py` (enable CI on the live mission pick).

---

### 8. Future Extension Points (Phase 2C+)

- Company-driven **mission composition** (evaluation/behavioral signals → task mix).
- **Role-aware** weighting using `levels` / role domains.
- Deeper **negative-evidence / contradiction** parsing into explicit suppressors.
- Dynamic **Company Readiness** from compiled subject signals.
- Weight tuning / A-B experiments via `resolve_weights` overrides.
