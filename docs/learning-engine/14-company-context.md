## Phase 2A — Company Context Layer

> **Status:** Architectural integration only. This phase does **not** make the
> planner company-aware. It introduces a normalized *Company Context* that
> bridges the Phase 1 Company Intelligence runtime to the Adaptive Planner and
> travels alongside the planner state for future phases. **No scoring, ranking,
> unlock, mission-generation, readiness, or AI-Mentor behavior changes.**

---

### 1. Motivation

The Adaptive Planner must never depend on hardcoded company ids, roadmap company
mappings, frontend company lists, or mission-engine constants. Phase 2A gives it
a single normalized **Company Context**, sourced exclusively from the Phase 1
**Company Runtime Loader** (compiled JSON artifacts — never markdown).

```
Learner Context  +  Roadmap Context  +  Revision Context  +  Timeline Context  +  Company Context
                                        ↓
                                Adaptive Planner
```

In Phase 2A the Company Context is **carried** by `LearnerContext` but is
**planner-inert** (read by nothing in the scoring path).

---

### 2. Components

| File | Role |
|---|---|
| `backend/services/learning_engine/company_context.py` | **New.** `CompanyContext`, `CompanyProfileContext`, `build_company_context()` |
| `backend/services/learning_engine/context.py` | **Modified (additive).** `LearnerContext.company_context` field + auto-build in `build_learner_context()` |
| `backend/services/learning_engine/__init__.py` | **Modified (additive).** exports the new symbols |

**`CompanyProfileContext`** — normalized runtime view of one compiled profile:
`company_id, metadata, subjects, signals, levels, planner, trends,
profile_version, summary_variant` plus convenience accessors `confidence`,
`philosophy`, `priority_hierarchy`, `adaptive_biases`. The raw editorial
`sections` markdown is intentionally excluded (normalized runtime data only).

**`CompanyContext`** — aggregate over a learner's selection:
`selected_company_ids`, `profiles` (only ids that resolved to a compiled
artifact), `unknown_company_ids` (selected ids with no compiled profile — e.g.
the UI-only `others` pseudo-company, or typos). Helpers: `is_empty`,
`known_ids()`, `get(id)`, iteration.

---

### 3. Data Flow

```
onboarding.target_companies (learner selection)
        │
        ▼
build_learner_context(target_companies=…)
        │  (auto, when company_context not supplied)
        ▼
build_company_context(ids)
        │  uses ONLY →  company_intelligence.loader  →  compiled/*/latest.json
        ▼
CompanyContext { profiles: {id: CompanyProfileContext}, unknown_company_ids }
        │
        ▼
LearnerContext.company_context   ── travels alongside ──►  Adaptive Planner
                                                             (does NOT read it yet)
```

Building is **defensive**: any loader/artifact issue for a single company
degrades that id to `unknown_company_ids`; construction never raises, so planner
behavior can never be affected.

---

### 4. Planner Integration

`build_learner_context()` (the planner's context-creation entry point) now:
1. resolves `target_companies` exactly as before;
2. builds a `CompanyContext` from them via the runtime loader (unless one is
   passed explicitly);
3. attaches it as `LearnerContext.company_context`.

No other planner file changed. `ranking.py`, `priority_engine.py`,
`eligibility.py`, `unlock.py`, `composition.py`, `cold_start.py`, `companion.py`
do **not** read `company_context`. Consequently `get_today_learning_node`
returns byte-identical recommendations.

---

### 5. Mission Lifecycle (unchanged)

Changing target companies (Onboarding / Settings / Profile) does **not** touch
an already-generated daily mission via this layer. A daily mission remains an
immutable snapshot. Because the planner reads onboarding fresh each cycle and
now builds `CompanyContext` on the fly, the **next** planning cycle
automatically uses the updated selection and the latest compiled Company
Intelligence — with no explicit invalidation. (The pre-existing onboarding-PATCH
behavior in `routes_missions.py` is untouched by Phase 2A.)

---

### 6. Backward Compatibility

Additive only. Verified via unit tests that planner ranking and
`score_candidate` outputs are identical with and without a populated
`company_context`. Existing planner/learning-engine suites pass unchanged.

---

### 7. Future Extension Points (Phase 2B and later)

- Company-weighted **subject importance** blending in the scoring model.
- Level/role-aware emphasis using `CompanyProfileContext.levels`.
- Timeline-driven emphasis using `adaptive_biases` + timeline context.
- Dynamic **Company Readiness** derived from compiled `subjects` signals.
- Optional **mission regeneration** when the company selection changes.
- Explainability: surface *which company signals* influenced a recommendation.

All of the above become reads of the already-available `company_context` —
no planner-orchestration redesign required.
