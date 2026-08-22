# CONSTITUTION-003 — Mission Engine

**Version:** 1.0  
**Status:** Active  
**Scope:** `backend/mission_engine.py`, `backend/routes_missions.py`, `backend/services/mission_context.py`, `backend/services/learning_engine/composition.py`  
**Authority:** Chief Software Architect  

---

## Purpose

The Mission Engine is the primary orchestrator of the PrepOS learner experience. It synthesizes curriculum knowledge, learner state, revision needs, company preferences, and planning recommendations into a single coherent `DailyMission` — the learner's entire study agenda for the day.

The Mission Engine does not decide **what to learn** (that is the Learning Engine Planner). It decides **how to package the day's learning** given a recommended node.

---

## Responsibilities

### Mission Engine Owns

- Building the `DailyMission` document from a Learning Engine recommendation
- Determining the task mix (practice count, revision slots, study tasks)
- Difficulty clamping (experience band × confidence signal)
- Inserting prerequisite revision tasks when patterns fail
- Mission validation (constraint checking via `MissionConstraints`)
- Computing readiness scores (overall + per-company)
- Managing the mission lifecycle (in_progress → completed → skipped)
- Task-level toggling (idempotent)
- Writing `MissionAdjustment` audit records
- Managing the `assessment_available` / `workflow_state` flags

### Mission Engine Does NOT Own

- Which roadmap node to study (owned by Learning Engine Planner)
- Which problems to surface (owned by Problem Selector)
- Assessment evaluation (owned by Assessment Engine)
- Learner state computation (owned by Learner Intelligence)
- Revision scheduling math (owned by Revision Engine)
- AI narrative content (delegated to AI Mentor `mission_planner.py`, cached on mission)
- Company profile data (owned by Company Intelligence)

---

## Scope

This constitution governs the mission lifecycle from generation through completion:

1. Mission generation (`build_mission_for_user`)
2. Mission composition (`services/learning_engine/composition.py`)
3. Mission context construction (`services/mission_context.py`)
4. Task management (toggle, complete, skip)
5. Readiness computation (`compute_readiness`, `compute_company_readiness`)
6. Adaptive analysis (`analyze_recent_feedback`, `determine_mode`)

---

## Architectural Principles

### ME-001 — One Mission Per User Per Day

The `daily_missions` collection enforces a unique constraint on `(user_id, date)`. A new mission for the same day MUST overwrite the existing one, never create a duplicate. The date is the UTC calendar date of generation.

### ME-002 — Mission Generation is Deterministic

Given identical inputs (learner state, roadmap, problem bank, date), mission generation MUST produce the same output. No randomness is introduced in production. The deprecated `_seeded_random` path (used only in legacy helpers) produces seeded randomness — it is removed from the production path.

### ME-003 — MissionContext is the Curriculum Interface

The Mission Engine MUST obtain all curriculum knowledge (pattern, stage, problems, CTA) through `MissionContext`. It MUST NOT independently query the roadmap or problem bank to infer these values.

### ME-004 — Difficulty is Experience-Bounded

Difficulty is always clamped to the learner's experience band:

| Position | Floor | Ceiling |
|----------|-------|---------|
| student | easy | medium |
| 0-1 | easy | medium |
| 1-3 | easy | hard |
| 3-5 | medium | hard |
| 5+ | medium | hard |

Confidence adjusts within the band (low confidence → floor, high confidence → ceiling) but NEVER outside the band.

### ME-005 — Composition Drives Task Mix

The `CompositionPlan` determines the task mix. The Mission Engine MUST build the task list to match `CompositionPlan.practice_count`, `revision_slots`, `include_supporting`, and `include_core`. It MUST NOT add tasks beyond what the plan authorizes.

### ME-006 — Prerequisite Revisions are Automatic

When the current node has a failing prerequisite pattern (detected from recent feedback), the Mission Engine MUST insert a prerequisite revision task. This is a mandatory circuit breaker, not an optional behavior.

### ME-007 — Mission Validation is Non-Negotiable

Every generated mission MUST pass `validate_mission()` before persistence. A validation failure with `severity == "error"` MUST trigger re-generation. A `severity == "warning"` is logged but does not block persistence.

### ME-008 — Audit Trail is Mandatory

Every mission generation MUST produce a `MissionAdjustment` record that captures: detected weaknesses, inserted prerequisites, whether the learner is advancing or revising, and the `CompositionPlan` + `MissionValidation` outputs. This record is append-only.

### ME-009 — AI Content is Post-Generation

The AI narrative (`ai_narrative`), `tomorrow_preview`, and `week_goal` are generated AFTER the mission is persisted. They are optional enrichments. If AI generation fails, the mission is still valid and returned to the learner. AI content is cached on the `DailyMission` document — re-fetching the mission MUST NOT re-invoke the LLM.

### ME-010 — Assessment Availability is Mission-Owned

The `assessment_available` flag is set by the Mission Engine when the learner has completed both study and coding tasks. The mission workflow state (`workflow_state`) is derived from task completion status. The Mission Engine MUST own this flag; the Assessment Engine MUST NOT write it.

---

## Design Philosophy

The Mission Engine is the **conductor** of the PrepOS experience. It does not play any instrument — it coordinates the instruments. The Learning Engine tells it which note to play. The Problem Selector provides the instrument. The Revision Engine tells it which chords need repetition. The Mission Engine assembles these into a coherent composition.

The Mission Engine must balance multiple competing goals:

1. **Learner urgency** — what does the learner need to do to pass their target interview?
2. **Spaced repetition** — what is overdue for revision?
3. **Prerequisites** — what does the learner need before they can learn today's topic?
4. **Daily capacity** — what fits in `daily_study_hours`?
5. **Company weighting** — what matters most to the learner's target companies?

The `CompositionPlan` is the mechanism by which these competing goals are resolved into a feasible task list.

---

## Mission Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│  GENERATION                                                      │
│  1. Learning Engine Planner → recommended node_id               │
│  2. build_mission_context(node_id) → MissionContext             │
│  3. analyze_recent_feedback() → mode: revise|advance|continue   │
│  4. _clamp_difficulty_to_experience() → clamped difficulty      │
│  5. plan_composition() → CompositionPlan                        │
│  6. Build task list (study + practice + revision)               │
│  7. select_representative() → Arena problems                    │
│  8. validate_mission() → MissionValidation                      │
│  9. DailyMission persisted to MongoDB                           │
│  10. MissionAdjustment audit record persisted                   │
│  11. AI Mentor enrichment (async, cached)                       │
└─────────────────────────────────────────────────────────────────┘
                           │
                     EXECUTION
                           │
┌─────────────────────────▼───────────────────────────────────────┐
│  IN PROGRESS                                                    │
│  - Tasks toggled (idempotent)                                   │
│  - assessment_available computed from task completion           │
│  - workflow_state updated                                       │
└─────────────────────────────────────────────────────────────────┘
                           │
                   COMPLETION / SKIP
                           │
┌─────────────────────────▼───────────────────────────────────────┐
│  COMPLETED / SKIPPED                                            │
│  - Streak updated (completion only)                             │
│  - Knowledge progress updated                                   │
│  - Activity event logged                                        │
│  - next_day planning inputs updated                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Company Readiness Weights

The Mission Engine applies per-company readiness weights to adjust topic prioritization. These weights are hardcoded editorial decisions, reviewed periodically.

| Company | DSA | LLD | HLD | Java | OS | DBMS | CN |
|---------|-----|-----|-----|------|----|------|----|
| Google | 0.45 | 0.10 | 0.20 | 0.05 | 0.07 | 0.07 | 0.06 |
| Microsoft | 0.35 | 0.20 | 0.15 | 0.10 | 0.07 | 0.07 | 0.06 |
| Amazon | 0.40 | 0.20 | 0.15 | 0.05 | 0.07 | 0.07 | 0.06 |
| Oracle | 0.20 | 0.10 | 0.10 | 0.20 | 0.08 | 0.25 | 0.07 |

Companies not in `COMPANY_READINESS_WEIGHTS` fall back to `DEFAULT_READINESS`.

These weights MUST sum to 1.0 per company. Changes require a deliberate editorial review.

---

## Mission Composition Rules

### `CompositionPlan` fields

| Field | Meaning |
|-------|---------|
| `primary_kind` | `practice` or `study` — the day's primary objective |
| `practice_count` | Number of coding practice tasks (0–4) |
| `revision_slots` | Number of revision tasks (0–3) |
| `include_supporting` | Whether to add one supporting-concept task |
| `include_core` | Whether to add one OS/DBMS/CN reading task |
| `capacity_minutes` | Effective study-time budget |

### Practice count by daily study hours

| Hours | Practice Count |
|-------|---------------|
| ≥3h | 3 |
| ≥1.5h | 2 |
| <1.5h | 1 |

### Adaptive mode

| Mode | Trigger | Effect |
|------|---------|--------|
| `revise` | avg_confidence <5, OR hint_ratio >50%, OR failed patterns exist | Shift toward revision tasks, insert prerequisites |
| `advance` | avg_confidence ≥8, hint_ratio <20% | Increase practice count, higher difficulty |
| `continue` | Neither above | Maintain current composition |

---

## Data Ownership

| Collection | Access Type | Purpose |
|-----------|------------|---------|
| `daily_missions` | Read + Write | Primary mission store |
| `mission_adjustments` | Write only | Audit trail |
| `problem_assignments` | Write only | Problem-to-mission linkage |
| `knowledge_progress` | Read only | Legacy track scores for readiness |
| `knowledge_nodes` | Read only | Per-node progress for planner |
| `problem_feedback` | Read only | Adaptive analysis |
| `weaknesses` | Read only | Prerequisite revision decisions |
| `revisions` | Read only (legacy) | Revision queue |

---

## Allowed Dependencies

The Mission Engine MAY depend on:

- `roadmap.py` (via MissionContext builder)
- `problem_bank.py` (via MissionContext builder)
- `services/mission_context.py`
- `services/problem_selection/`
- `services/learning_engine/planner.py` (to get recommendation)
- `services/learning_engine/composition.py` (CompositionPlan, validate_mission)
- `services/learner_intelligence/` (read-only snapshot, via planner)
- `services/revision_engine.py` (get revision queue)
- `services/progress_engine.py` (read progress)
- `services/streak_engine.py` (update streak on completion)
- `models.py` (DailyMission, MissionTask)

---

## Forbidden Dependencies

❌ `assessment/` — Mission Engine MUST NOT call Assessment Engine  
❌ `ai_mentor/context_builder.py` — Mission Engine MUST NOT read AI Mentor context  
❌ Any MongoDB write to `assessments`  
❌ Any HTTP client (no outbound HTTP in mission generation)  
❌ `company_intelligence/` directly (company weights are hardcoded in `mission_engine.py`)  

---

## Contracts

### Input Contract

```python
build_mission_for_user(
    user_id: str,
    onboarding: dict,           # target_companies, position, daily_study_hours
    knowledge_nodes: dict,      # node_id → {confidence, mastery, weakness_score, status}
    feedbacks: list[dict],      # recent problem_feedback rows
    revision_queue: list[dict], # from revision_engine.get_revisions_for_user()
    recommended_node_id: str,   # from learning_engine/planner
    date: str,                  # YYYY-MM-DD
) → DailyMission
```

### Output Contract

```python
DailyMission {
    id: str                    # UUID
    user_id: str
    date: str                  # YYYY-MM-DD
    title: str
    focus_area: str
    focus_topic: str           # one of TOPIC_KEYS
    difficulty: str            # experience-clamped
    estimated_duration_minutes: int
    learning_objective: str
    tasks: list[MissionTask]
    revision_task_ids: list[str]
    status: str                # in_progress | completed | skipped
    assessment_id: str | None  # populated when assessment is created
    assessment_available: bool # true when study+coding done
    workflow_state: str | None
    recommendation_insight: dict | None  # from insight.py
    ai_narrative: str | None   # from AI Mentor mission_planner (cached)
    tomorrow_preview: dict | None
    week_goal: dict | None
}
```

### MissionTask Contract

```python
MissionTask {
    id: str       # UUID
    title: str
    kind: str     # practice | study | revise
    topic: str    # one of TOPIC_KEYS
    completed: bool
    pattern: str | None    # coding pattern (practice tasks)
    problem_count: int | None
    node_id: str | None    # roadmap node linkage
}
```

---

## Performance Expectations

| Operation | Target |
|-----------|--------|
| Full mission generation | <500ms end-to-end (excluding AI enrichment) |
| AI enrichment (first time) | <10s (async, non-blocking) |
| AI enrichment (cached) | 0ms (reads from DailyMission doc) |
| Task toggle | <50ms |
| Mission completion | <100ms |

Mission generation MUST NOT block on AI content generation. AI enrichment runs after the mission is persisted and returned.

---

## Invariants

1. One mission per `(user_id, date)` — enforced by unique index.
2. `difficulty` is always within the learner's experience band.
3. Every `MissionTask` with `kind == practice` MUST have a valid `pattern`.
4. `revision_task_ids` contains only IDs of tasks that exist in `tasks`.
5. `MissionAdjustment` is written for every generation, without exception.
6. `assessment_available` transitions from `false` to `true` exactly once per mission; it never transitions back.
7. Arena and Assessment problems are disjoint — enforced by `split_arena_assessment()`.

---

## Anti-patterns

❌ Generating a mission without calling `validate_mission()`  
❌ Setting `difficulty` without clamping to experience band  
❌ Calling the LLM during the blocking mission generation path  
❌ Writing to `assessments` from any mission engine function  
❌ Including problems from a different pattern than the recommended node's  
❌ Skipping the `MissionAdjustment` audit record  
❌ Modifying the `DailyMission` document outside of mission engine functions  
❌ Bypassing `CompositionPlan` and hardcoding task counts  
❌ Reading `assessment_id` from the mission doc inside the mission engine (Assessment Engine owns that field)  

---

## Future Evolution

- **Team missions:** Add a `team_id` field to `DailyMission`. The composition engine gains a team-aware mode that aligns team members on compatible nodes. The individual mission contract is unchanged.
- **Mission templates:** Pre-authored composition templates (e.g., "Pre-Interview Sprint", "Foundation Week") override `CompositionPlan` for specific learner scenarios.
- **Multi-day missions:** A `DailyMission` may span multiple calendar days for long topics. Add `end_date` field. The unique index constraint changes to `(user_id, start_date)`.
- **Collaborative missions:** Two learners assigned the same mission node can compare progress. Adds a `collaborative_session_id` field. No mission generation logic change.
