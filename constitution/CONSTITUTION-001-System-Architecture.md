# CONSTITUTION-001 — System Architecture

**Version:** 1.0  
**Status:** Active  
**Scope:** Entire PrepOS engineering system  
**Authority:** Chief Software Architect  

---

## Purpose

This constitution governs the overall system architecture of PrepOS. It defines the mandatory layer model, subsystem boundaries, dependency directions, ownership rules, and the architectural invariants that every future feature, module, and pull request MUST respect.

PrepOS is an **adaptive, AI-powered interview preparation operating system**. It is not a static course platform. Its central promise is personalized, evidence-based, daily learning missions — produced by a deterministic planning pipeline that models the learner, the curriculum, and company expectations simultaneously.

---

## Responsibilities

### System Architecture Owns

- The canonical layering model for all backend and frontend code
- The dependency direction rules (who may depend on whom)
- The subsystem map and ownership boundaries
- The data flow contract from onboarding to next-day mission
- The integration boundary between frontend and backend
- The rules governing external service integration (LLM providers, email, database)

### System Architecture Does NOT Own

- The internal implementation of any individual subsystem
- Curriculum content (owned by Curriculum Engine — CONSTITUTION-002)
- Problem selection logic (owned by Curriculum Engine)
- Business rules for assessment evaluation (owned by Assessment Engine — CONSTITUTION-005)

---

## Scope

This constitution applies to every file in the PrepOS monorepo: `backend/`, `frontend/`, `constitution/`, `docs/`, `tests/`, `scripts/`.

---

## Architectural Principles

### P-001 — Vertical Slicing by Responsibility

Each subsystem MUST own a complete vertical slice of its domain. It MUST own its data, its logic, its API exposure, and its contracts. No subsystem may bleed its implementation details into another's vertical slice.

### P-002 — Unidirectional Dependency Flow

Dependencies flow in one direction:

```
Frontend → API Layer → Service Layer → Domain Layer → Data Layer
```

No layer may import from a layer above it. The Data Layer (MongoDB, `problem_bank.py`, `roadmap_v1.json`) has zero upstream dependencies.

### P-003 — Determinism First

Every backend decision that affects the learner's experience MUST be deterministic for the same inputs. Non-determinism (e.g., LLM responses, AI narrative) is confined to presentation layers and cached on first computation. The planning pipeline, selection pipeline, and evaluation pipeline are always deterministic.

### P-004 — Additive Evolution

All extension MUST be additive. New signals, new assessment types, new companies, new roadmap tracks, new AI providers MUST be integrated by adding new modules — never by modifying the core contract of existing modules.

### P-005 — Single Source of Truth Per Domain

Each piece of authoritative data has exactly one owner:

| Data Domain | Owner |
|------------|-------|
| Problem metadata | `backend/problem_bank.py` |
| Curriculum graph | `backend/data/roadmap_v1.json` |
| Learning progress | `knowledge_nodes` MongoDB collection |
| Mission state | `daily_missions` MongoDB collection |
| Assessment evidence | `assessments` MongoDB collection |
| Company profiles | `company_intelligence/compiled/*.json` |
| AI-generated content | `knowledge_content` MongoDB collection |

No other module may replicate this data or derive a parallel store.

### P-006 — Immutable Evidence

Assessment evidence, once produced, is immutable. Evidence is a record of what happened. It is never retroactively modified.

### P-007 — Separation of Concerns: Produce vs. Consume

The Assessment Engine produces evidence. It MUST NOT consume it. The Learner Intelligence Engine consumes evidence. It MUST NOT produce assessments. The Mission Engine consumes recommendations. It MUST NOT score learner state.

### P-008 — No Business Logic in Presentation

Business logic, scoring formulas, selection algorithms, and evidence evaluation MUST live in the backend service layer. The frontend MUST NOT re-implement any business rule. The frontend renders the state the backend returns.

---

## Design Philosophy

PrepOS is designed around a **feedback loop architecture**: the learner completes a mission, which generates evidence, which updates learner state, which influences tomorrow's mission. This loop is the core product. Every subsystem exists to make this loop more accurate, more adaptive, and more personalized.

The architecture deliberately separates:

1. **What to learn** (Learning Engine + Curriculum) — a deterministic ranking problem
2. **How to present it** (Mission Engine + MissionContext) — a composition problem
3. **How to evaluate it** (Assessment Engine) — an evidence production problem
4. **What it means about the learner** (Learner Intelligence) — a signal computation problem
5. **What to do tomorrow** (Planner) — a recommendation problem

These five concerns MUST remain separate. Their integration points are defined by stable contracts, not by direct module coupling.

---

## System Layer Model

```
┌─────────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER (React SPA)                                  │
│  pages/, components/, contexts/, hooks/                         │
│  Rules: No business logic. Render backend state. Pure UI.       │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP/REST (JWT cookie auth)
┌──────────────────────────▼──────────────────────────────────────┐
│  API LAYER (FastAPI Routers)                                     │
│  routes_*.py, assessment/api.py, ai_mentor/mentor_routes.py     │
│  Rules: Request parsing, auth, response shaping. No business    │
│  logic. Delegate to Service Layer immediately.                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  SERVICE LAYER (Domain Engines)                                  │
│  mission_engine.py, assessment/, ai_mentor/, company_intel.,    │
│  services/learning_engine/, services/learner_intelligence/,     │
│  services/problem_selection/, services/progress_engine.py,      │
│  services/revision_engine.py, services/mission_context.py       │
│  Rules: All business logic lives here. Stateless where possible.│
│  No direct HTTP context. No React awareness.                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  DOMAIN LAYER (Pure Data + Contracts)                           │
│  models.py, roadmap.py, problem_bank.py,                        │
│  assessment/schemas.py, services/mission_context.py (dataclass) │
│  Rules: Pydantic models, dataclasses, pure functions. No I/O.   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│  DATA LAYER                                                      │
│  MongoDB (motor async), data/roadmap_v1.json, problem_bank.py,  │
│  company_intelligence/compiled/                                  │
│  Rules: Storage only. No logic.                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Subsystem Map

| Subsystem | Constitution | Primary Files | MongoDB Collections |
|-----------|-------------|---------------|---------------------|
| Mission Engine | CONST-003 | `mission_engine.py`, `routes_missions.py` | `daily_missions`, `mission_adjustments` |
| Curriculum Engine | CONST-002 | `problem_bank.py`, `roadmap.py`, `data/roadmap_v1.json`, `services/mission_context.py`, `services/problem_selection/` | — (static) |
| Learner Intelligence | CONST-004 | `services/learner_intelligence/` | `knowledge_nodes` (read) |
| Assessment Engine | CONST-005 | `assessment/` | `assessments` |
| AI Mentor | CONST-006 | `ai_mentor/` | `mentor_conversations`, `mentor_messages`, `knowledge_content` |
| Company Intelligence | CONST-007 | `company_intelligence/` | — (compiled JSON) |
| Content Architecture | CONST-008 | `knowledge_generation.py`, `prompt_builder.py` | `knowledge_content` |
| Frontend Experience | CONST-009 | `frontend/src/` | — |
| Progress Engine | (cross-cutting) | `services/progress_engine.py` | `knowledge_nodes`, `knowledge_progress` |
| Revision Engine | (cross-cutting) | `services/revision_engine.py` | `knowledge_nodes` |
| Streak Engine | (cross-cutting) | `services/streak_engine.py` | `study_streaks` |

---

## Data Flow

### Mission Generation Flow (canonical)

```
1. GET /api/mission/today
2. API Layer reads DB: onboarding, knowledge_nodes, problem_feedback, revision queue
3. Build LearnerContext (learning_engine/context.py)
4. get_today_learning_node() → recommended node_id + insight
5. build_mission_context(node_id) → MissionContext (single source of truth)
6. build_mission_for_user() → CompositionPlan + task mix + difficulty clamping
7. select_representative() → arena and assessment problem IDs
8. DailyMission document persisted to MongoDB
9. MissionAdjustment audit record persisted
10. AI Mentor generates narrative + week_goal (async, cached on mission)
11. Return DailyMission to frontend
```

### Evidence Loop (canonical)

```
1. Learner completes Assessment
2. evaluate_assessment() → AssessmentEvidence (immutable, frozen)
3. POST /api/learner-intelligence/evidence → evidence_integration.process_evidence()
4. knowledge_nodes updated: confidence, mastery_percentage, weakness_score, revision scheduling
5. Spaced repetition rescheduled via revision_engine.mark_node_for_revision()
6. Next day: updated knowledge_nodes feed the Learning Engine ranking
```

---

## Dependency Direction Rules

### MUST rules

- Frontend MUST only depend on the REST API. It MUST NOT import backend Python modules.
- API Layer MUST delegate all business logic to Service Layer. It MUST NOT contain scoring, selection, or evaluation logic.
- Service Layer MUST NOT import from API Layer (no circular dependency).
- Assessment Engine MUST NOT import from Learner Intelligence Engine.
- Learner Intelligence Engine MUST NOT import from Assessment Engine.
- Mission Engine MUST NOT import from Assessment Engine.
- Assessment Engine MUST NOT import from Mission Engine.
- Problem Bank (`problem_bank.py`) MUST NOT import from any service module.
- Roadmap (`roadmap.py`) MUST NOT import from any service module.

### Allowed cross-service dependencies

```
mission_engine.py        → learning_engine/planner.py
mission_engine.py        → services/mission_context.py
mission_engine.py        → services/problem_selection/
mission_engine.py        → roadmap.py
mission_engine.py        → problem_bank.py

learning_engine/planner  → learner_intelligence/ (read-only snapshot)
learning_engine/planner  → roadmap.py
learning_engine/planner  → problem_bank.py (via mission_context)

assessment/              → problem_bank.py (read only)
assessment/              → services/problem_selection/ (read only)

ai_mentor/               → roadmap.py (read only)
ai_mentor/               → knowledge_generation.py (read only)

routes_missions.py       → mission_engine.py
routes_missions.py       → services/problem_selection/
routes_missions.py       → services/mission_context.py
routes_missions.py       → services/progress_engine.py
routes_missions.py       → services/revision_engine.py
```

---

## Data Ownership

### Reads from external services

| Service | Who Reads | Purpose |
|---------|----------|---------|
| MongoDB | All backend modules | Learner state, missions, assessments |
| Google Gemini API | `ai_service.py` | KB content generation, AI Mentor responses |
| SMTP | `email_service.py` | Auth emails |

### Static data (no runtime writes)

| File | Owner | Who Reads |
|------|-------|-----------|
| `data/roadmap_v1.json` | Curriculum team | `roadmap.py` (singleton load) |
| `problem_bank.py` | Curriculum team | Problem Selection, Mission Engine, Assessment Generator |
| `company_intelligence/compiled/*.json` | Company Intelligence | `company_intelligence/loader.py` |

---

## Contracts

### The MissionContext Contract

`MissionContext` is the single integration point between the Curriculum Engine and every consuming subsystem. It MUST contain:

| Field | Type | Guarantee |
|-------|------|-----------|
| `node_id` | str | Always present, valid roadmap node ID |
| `activity_type` | str | One of: study, coding, quiz, behavioral, design, system_design, flashcards |
| `coding_pattern` | Optional[str] | Present when activity_type == coding |
| `learning_stage` | Optional[str] | One of: foundation, core, advanced |
| `representative_problem_ids` | List[str] | Empty only when activity_type != coding |
| `difficulty` | Optional[str] | One of: easy, medium, hard |

### The AssessmentEvidence Contract

`AssessmentEvidence` is the single output contract of the Assessment Engine. It MUST be:
- Frozen (immutable after creation)
- Type-agnostic (same structure for all assessment types)
- Normalized (all scalars 0..1 or -1..1)

### The LearnerIntelligenceSnapshot Contract

`LearnerIntelligenceSnapshot` is the output contract of the Learner Intelligence Engine. It MUST be:
- Deterministic (same input → same output)
- Non-raising (errors degrade to empty snapshot)
- Bounded (produces a ±-bounded nudge, never a hard veto)

---

## Extension Points

| Domain | How to Extend |
|--------|--------------|
| New roadmap tracks | Add track JSON to `data/roadmap_v1.json`. No engine changes required. |
| New assessment types | Add to `AssessmentType` enum + implement generator. Assessment Engine schema unchanged. |
| New LLM providers | Add provider to `ai_service.py`. No consumer changes required. |
| New companies | Add to `company_intelligence/registry.json` + compile. No service changes. |
| New learner signals | Add field to `LearnerIntelligenceInput`, implement signal module, add to snapshot. Planner adapter unchanged. |
| New problem patterns | Add to `PATTERN_TO_DOMAIN` in `problem_bank.py`. Add problems. No selector change. |

---

## Performance Expectations

| Concern | Expectation |
|---------|------------|
| Mission generation | O(n) in learner's `knowledge_nodes` count. Target <500ms end-to-end |
| Problem selection | O(p) in problem bank size. In-memory. Target <5ms |
| Learner Intelligence | O(n) in progress rows. In-memory. Never hits DB directly. Target <50ms |
| KB content generation | First request: up to 10s (LLM). Subsequent: <50ms (cache read) |
| Roadmap load | Singleton load at process start. O(1) per node lookup thereafter |
| Assessment evaluation | O(d) in rubric dimensions. Pure computation. Target <10ms |

---

## Invariants

1. **Problem IDs are immutable.** A problem's `id` (e.g., `lc-3`) MUST NEVER change. Frontend bookmarks, assessment history, and feedback records reference them.
2. **Roadmap node IDs are immutable.** Once published, a node's `id` is a permanent key in `knowledge_nodes`.
3. **`MissionContext` is the canonical topic descriptor.** No subsystem may infer topic, pattern, difficulty, or learning stage independently.
4. **The problem selection pipeline is deterministic.** Same input → same ranked list.
5. **`representative_pool()` never mixes patterns or stages.** Stage and pattern scoping are hard constraints.
6. **Arena and Assessment problems are always disjoint.** `split_arena_assessment()` enforces this unconditionally.
7. **AssessmentEvidence is never mutated after creation.**
8. **The planner never introduces randomness** (legacy `_seeded_random` path is deprecated).
9. **`knowledge_nodes` is the single progress store.** No secondary progress store may be introduced.

---

## Anti-patterns

❌ Business logic in FastAPI route handlers  
❌ Scoring formulas duplicated across modules  
❌ Problem metadata stored in MongoDB (belongs in `problem_bank.py`)  
❌ Roadmap graph loaded from MongoDB at runtime  
❌ LLM calls in the mission generation hot path  
❌ Circular imports between service modules  
❌ Frontend computing which problems to show  
❌ Assessment Engine writing to `knowledge_nodes`  
❌ Learner Intelligence Engine calling the Assessment API  
❌ Company Intelligence parsed from Markdown at runtime  
❌ Any module importing from a layer above itself  
❌ Two modules owning the same MongoDB collection  

---

## Future Evolution

- **Mobile client:** The REST API surface is the only integration point. Mobile MUST consume the same API. No backend changes required.
- **Multi-user teams:** The `user_id` key on every collection isolates learner data. Team features add collections without modifying existing ownership.
- **Real-time features:** WebSocket sessions MAY be introduced as an additional transport layer. The service layer remains unchanged.
- **Analytics platform:** A read-only analytics service MAY subscribe to `knowledge_nodes`, `assessments`, and `daily_missions` changes via change streams. It MUST NOT write to these collections.
- **Microservices:** Each subsystem's vertical slice is already well-bounded. Extraction to microservices is possible without architectural redesign — it requires network boundaries, not logic changes.
