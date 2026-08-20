# 01 · Assessment Engine (Phase 3A)

> PrepOS knew *"What should the learner study?"*
> Phase 3A adds *"Can the learner actually demonstrate mastery?"*

The Assessment Engine is a **reusable, deterministic backend platform** that
produces **evidence** — the layer between learning and planning. It is **not**
Mock Interviews; it is the foundation future features (Mock Interviews, Coding
/ Theory / Behavioral / System-Design / Resume assessments) build on.

**Non-negotiables honoured:** no frontend, no LLM/AI grading, fully
deterministic, and **zero changes** to the Mission Engine, Adaptive Planner,
Knowledge Graph, Company Intelligence, Learner Intelligence, Revision Engine,
Analytics, Auth, or Onboarding.

---

## 1. Architecture

```
Mission ──(optional)──┐
Roadmap Node ─────────┤
Difficulty ───────────┤        ┌────────────────── Assessment Engine ──────────────────┐
Target Company ───────┼──────► │ generator → session → evaluation → feedback → evidence │
Learner Level ────────┘        │                         → recommendation               │
                               └───────────────────────────────┬────────────────────────┘
                                                                ▼
                                                      Evidence (structured)
                                                                ▼
                                              Learner Intelligence (decides how)
                                                                ▼
                                                        Adaptive Planner
```

One-way flow: **Assessment → Evidence → Learner Intelligence → Planner.** The
Assessment Engine never writes planner/learner state.

Package `backend/assessment/` (SOLID, single-responsibility modules):

| Module | Responsibility |
|--------|----------------|
| `schemas.py` | Domain objects + vocabulary (enums, Pydantic models) |
| `rubrics.py` | Reusable weighted rubrics (coding defined) |
| `difficulty.py` | Difficulty mapping & recommendation |
| `assessment_types.py` | Extensible type registry (coding implemented) |
| `assessment_generator.py` | Question generation, **reuses `problem_bank`** |
| `evaluation_engine.py` | Deterministic rubric scoring |
| `feedback_engine.py` | Structured feedback (no free-text AI) |
| `evidence.py` | Structured evidence (exposed, never applied) |
| `recommendations.py` | Next-step recommendation |
| `assessment_session.py` | Lifecycle state machine |
| `assessment_history.py` | Persistence (`assessments` collection) |
| `assessment_engine.py` | Orchestrator (application service) |
| `api.py` | REST API router |

---

## 2. Domain model

`Assessment` is the aggregate root (one normalized Mongo document) composed of:
`Rubric`, `Question`, `Attempt`, `Result`, `Feedback`, `Evidence`,
`AssessmentRecommendation`, plus session fields (status, timestamps,
time-taken). Per the design refinement, **`mission_id` is nullable** — an
assessment may reference a mission, a roadmap node, both, or neither
(standalone practice, scheduled reassessment, future mock interviews).

---

## 3. Lifecycle (session state machine)

```
pending ──start──► started ──submit──► submitted ──evaluate──► evaluated ──► completed
```

Illegal transitions raise `InvalidTransition` (HTTP 409). Timestamps and
`time_taken_seconds` are stamped on transition.

---

## 4. Assessment types

All eight future types are **registered** (`coding, theory, mcq, debugging,
behavioral, system_design, resume, project_explanation`). Only **Coding** has a
generator in Phase 3A; requesting an unimplemented type returns HTTP 422
(`AssessmentTypeNotSupported`). Adding a type = register one generator +
(optionally) a rubric — **no redesign**.

---

## 5. Rubric Engine

Rubrics are data: a list of weighted dimensions summing to 1.0. Coding rubric:
**Correctness 0.40, Complexity 0.20, Edge Cases 0.20, Communication 0.10, Code
Quality 0.10.** Weights are configurable via `get_rubric(..., weight_overrides=)`
and re-normalized. The same structure is reused for every future type.

---

## 6. Evaluation Engine (deterministic)

Each dimension scored 0–100 from the structured `Attempt`; weighted sum →
`overall_score` → verdict (`correct ≥ 90`, `partially_correct ≥ 40`, else
`incorrect`). Also emits `complexity_rating` (optimal/suboptimal/unknown) and
`edge_case_coverage`. **Extension point:** an AI-assisted evaluator can later
populate the same `DimensionScore` objects without changing consumers.

---

## 7. Evidence flow

`evidence.py` emits a structured `Evidence` object (coding_accuracy,
problem_solving, completion_quality, difficulty_achieved, repeated_mistakes,
`topic_confidence_delta` ∈ [-1,1], weakness_confirmation, revision_trigger,
verdict). It is **exposed** via `GET /api/assessments/evidence` (and per
assessment) for Learner Intelligence to consume on its own terms. The engine
**never** mutates confidence, weakness, velocity, or revision schedules.

---

## 8. Planner & Learner Intelligence integration

There is **no direct coupling**. Evidence is a read surface
(`assessment_history.list_evidence_for_user`). A future Learner-Intelligence
adapter can fold assessment evidence into its snapshot; the planner continues
to consume Learner Intelligence only.

---

## 9. Database impact

New collection **`assessments`** (one doc per assessment). Justification:
`knowledge_nodes` (per-node progress) and `daily_missions` (missions) cannot
represent an assessment's lifecycle/rubric/attempt/result/evidence without
overloading their schema. Indexes: unique `id`, `(user_id, created_at desc)`,
`(user_id, mission_id)`. No existing collection or schema is modified.

---

## 10. API inventory (all under `/api/assessments`, JSON, auth-guarded)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/` | Create assessment (generates question + rubric) |
| POST | `/{id}/start` | pending → started |
| POST | `/{id}/submit` | started → submitted (records attempt) |
| POST | `/{id}/evaluate` | submitted → evaluated → completed |
| GET | `/{id}` | Full assessment |
| GET | `/{id}/result` | Result only |
| GET | `/{id}/feedback` | Feedback only |
| GET | `/{id}/evidence` | Evidence only |
| GET | `/history` | User's assessments (optional `mission_id`) |
| GET | `/evidence` | All user evidence (LI read surface) |

---

## 11. Backward compatibility & performance

- Additive only: one new router + one new collection; existing routes, planner,
  learner intelligence, and missions are untouched (regression suite green).
- All engine operations are O(1)/O(n-small) pure functions; the single heavier
  read is `history` list, backed by indexes.

## 12. Future extension points

- Additional assessment types (register generator + rubric).
- AI-assisted evaluator populating `DimensionScore` (deterministic core stays).
- Learner-Intelligence adapter consuming assessment evidence.
- Per-problem test/edge-case catalogs to replace self-reported attempt inputs.
