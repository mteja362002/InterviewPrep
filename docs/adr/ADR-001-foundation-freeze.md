# ADR-001 — PrepOS Foundation Freeze (Phase 3C.1)

- **Status:** Accepted / FROZEN
- **Scope:** Backend learning architecture (Slice 1)
- **Supersedes:** none
- **Applies to:** all future phases (4+). Do not reintroduce parallel data
  flows or duplicate selection logic without a new ADR.

---

## 1. Context

PrepOS had multiple subsystems (Mission Planner, Coding Arena, Assessment
Engine, AI Mentor, Analytics, Practice) that each independently inferred
topics, activity types, difficulty and problems. This produced drift,
duplicated filtering logic, stage/topic leakage and random fallbacks
(e.g. "return any problem"). This ADR freezes a single, deterministic,
explainable, reusable foundation before product features are built.

---

## 2. Canonical content hierarchy (single sources of truth)

| Source | Owns | Consumed by | NEVER used for |
| --- | --- | --- | --- |
| **Roadmap** (`data/roadmap_v1.json`) | curriculum, prerequisites, learning stages, **`activity_type`**, **`assessment_type`**, patterns | every engine | — |
| **`problem_bank.py`** | representative interview problems | Mission generation, Coding Arena, Assessment | — |
| **`dev_seed.json`** (`leetcode_catalog`) | Practice More, manual search, unlimited practice | Practice More, manual search, **assessment overflow only** | Mission Engine / Coding Arena |
| **Company Intelligence** | company weighting / hiring signals | ranking bias | selecting problems directly |
| **Learner Intelligence** | mastery, confidence, attempts, revision debt, weak areas, history | ranking / selection signals | authoring curriculum |

These are the ONLY canonical datasets. No new parallel dataset or duplicate
selection logic may be introduced.

---

## 3. Frozen decisions

1. **MissionContext is the single source of truth** for "what am I learning
   now" (`services/mission_context.py`). Every downstream module consumes it;
   none re-infers topic / activity / difficulty / stage / pattern / problems.
2. **LearningNode (roadmap node) is the universal abstraction.** Engines are
   subject-independent — no runtime `if subject == DSA/Java/...` branching.
3. **`activity_type` is explicit** on every roadmap node
   (`study | coding | quiz | behavioral | design | system_design | flashcards`).
   Stamped at BUILD time by `services/curriculum/activity_metadata.py` via
   `scripts/generate_roadmap.py` (future) and `scripts/migrate_activity_types.py`
   (one-time). No runtime inference.
4. **`assessment_type`** is derived from `activity_type` at build time:
   `coding→coding, study→quiz, behavioral→behavioral, design→design,
   system_design→system_design`; `resume/projects→none`.
5. **Representative Problems ≠ Practice Library.** `problem_bank.py` powers
   curriculum/mission/arena/assessment; `dev_seed.json` powers Practice More /
   manual search and is only ever assessment *overflow*.
6. **One canonical `ProblemSelector`** (`services/problem_selection/selector.py`)
   is reused by Mission Planner, Coding Arena, Assessment Engine, AI Mentor and
   Practice More. No duplicated filtering logic anywhere.
7. **Arena ⟂ Assessment.** They validate the same objective but never present
   identical representative problems (`split_arena_assessment`). Arena is drawn
   first; Assessment excludes all arena ids; overflow (dev_seed) never
   duplicates arena.
8. **No stage mixing / no future-topic leak.** Selection is scoped to one
   `pattern` and one `learning_stage`; problems for not-yet-unlocked topics are
   never in the pool.
9. **Adaptive volume.** Arena workload scales with mission duration
   (`arena_problem_count`: 45m→1, 90m→2, 135m→3, 180m→4, ≥225m→5). Assessment
   size scales independently.
10. **No random fallbacks.** No random topic, no "Two Sum"/default-coding
    fallback, no unrelated-topic substitution. Insufficient content → explicit
    empty state. All fallbacks stay within the same `pattern`.
11. **KB vs Arena buttons are mutually exclusive** (driven by
    `MissionContext.opens_arena` / `opens_knowledge_base`). *(UI wiring is a
    later slice.)*
12. **AI is a content generator, not a curriculum designer.** Coding uses
    representative problems (no AI). Non-coding assessments will use
    provider-agnostic prompt templates (`assessment/prompts/`) that receive the
    MissionContext + learner signals; no provider/model is hardcoded and no LLM
    is called in this sprint.

---

## 4. Canonical data flow

```
Onboarding + Learner Intelligence + Company Intelligence
        │
        ▼
Adaptive Planner ──► picks node_id (LearningNode)
        │
        ▼
   MissionContext  (single source of truth)
        │
        ├── activity_type == coding ──► Coding Arena  ─┐
        │                                              ├─► ProblemSelector (problem_bank)
        │                              Assessment ─────┘   (Arena ⟂ Assessment; dev_seed overflow for assessment only)
        │
        └── activity_type != coding ──► Knowledge Base + (future) AI prompt templates
```

Practice More / manual search run **independently** on `dev_seed.json` and
never affect mission generation.

---

## 5. Extensibility

Adding a new subject (Python, React, AWS, Docker, Kafka, Redis, GenAI, Spark,
Kubernetes, ...) requires only:
- roadmap additions (+ one row in `TRACK_ACTIVITY_TYPE` if a new track id), and
- content additions (representative problems if coding).

No Assessment Engine, Coding Arena or Planner code changes.

---

## 6. Slice 1 deliverables (this sprint)

- `services/curriculum/activity_metadata.py` — build-time derivation (frozen rules)
- `scripts/migrate_activity_types.py` — one-time roadmap stamp (idempotent, backup)
- `scripts/generate_roadmap.py` — now stamps metadata for future generation
- `services/mission_context.py` — MissionContext object + factory
- `services/problem_selection/selector.py` — canonical selector
- `assessment/prompts/` — provider-agnostic prompt scaffold (no LLM calls)
- Refactors: `assessment/assessment_generator.py`, Coding Arena routes — now
  consume the canonical selector; unrelated-topic fallbacks removed.
- Tests: `test_activity_metadata_migration`, `test_mission_context`,
  `test_problem_selector`, `test_assessment_prompts`.

Deferred (next slices, require review first): frontend KB/Arena button gating,
live AI generation, analytics/mentor MissionContext wiring.
