# 03 · Assessment → Learner Intelligence Integration (Phase 3B)

> The Assessment Engine is the canonical **producer** of learner evidence.
> Learner Intelligence is the canonical **consumer** of that evidence.

Phase 3B wires the two together — **additively, deterministically, backend
only** — so evidence flows one way and the Assessment Engine never touches
planner state:

```
Assessment
    ↓
AssessmentEvidence  (immutable, canonical contract — see 02)
    ↓
[Assessment → Learner Intelligence integration layer]
    ↓
LearnerIntelligenceUpdate  (append-only, immutable)
    ↓
Learner State overlay  (deterministic aggregation)
```

Future systems (Planner, Analytics, AI Mentor, Revision Engine, Company
Readiness) consume **Learner Intelligence**, never the Assessment Engine
directly.

---

## 1. Components

| Module (`services/learner_intelligence/`) | Responsibility |
|---|---|
| `evidence_integration.py` | The isolated, reusable bridge: `validate_evidence`, `process_evidence` (pure translation), `ingest_evidence` (process + append). |
| `learner_update.py` | `LearnerIntelligenceUpdate` — immutable (frozen) learner-state delta + `from_dict`. |
| `learner_state.py` | `build_learner_state(updates)` — deterministic per-node aggregation ("Updated Learner State"). |
| `update_repository.py` | Append-only Mongo repo (`learner_intelligence_updates`), `ensure_indexes`. |
| `evidence_api.py` | Read-only observability API `/api/learner-intelligence/{updates,state}`. |

**Dependency direction:** the integration layer depends only on the evidence
*contract* (an `AssessmentEvidence` object **or** a plain dict). Assessment
code never imports Learner Intelligence.

---

## 2. Evidence processing lifecycle

`process_evidence(evidence)` is **type-agnostic** — it reads ONLY canonical
contract fields, so Coding, MCQ, Behavioral, LLD, HLD, Resume, Debugging, SQL,
OS, Networking, and any future type flow through **without changing Learner
Intelligence** and with **no `if assessment_type == …` branching.**

Deterministic translation rules:

| Learner-state field | Derivation |
|---|---|
| `confidence_delta` | passthrough of evidence `confidence_delta` (-1..1) |
| `mastery_delta` | `(proficiency − 0.5) × 20` → [-10, +10] pts |
| `weakness_detected` | evidence `weakness_confirmation` |
| `strength_detected` | verdict `correct` **and** `accuracy ≥ 0.9` |
| `knowledge_gap_adjustment` | `(1 − accuracy)×15` if weakness; `−accuracy×15` if strength; else 0 |
| `revision_hint` | evidence `revision_trigger` |
| `learning_signals` | canonical scalars + evidence `metrics` bag |

Only learner-state fields are produced — never planner-specific fields.

---

## 3. Learner update lifecycle & append-only history

1. An assessment completes → `AssessmentEvidence` (immutable).
2. At the orchestration boundary (the `/evaluate` route), `ingest_evidence`
   translates it and **appends** a `LearnerIntelligenceUpdate` to the
   `learner_intelligence_updates` collection (INSERT only — never updated or
   deleted).
3. `build_learner_state` aggregates the append-only history into the current
   learner-state overlay on demand.

`LearnerIntelligenceUpdate` is a frozen dataclass; combined with the immutable
evidence and insert-only writes, the entire chain is auditable and immutable.

**New collection justification:** `learner_intelligence_updates` is a distinct
concern from `assessments` (immutable evidence) and `knowledge_nodes` (current
progress the planner reads). Keeping it separate preserves existing
planner/revision behavior and gives analytics a clean, append-only history.

---

## 4. Explainability model

Every update carries deterministic `reasons`, e.g.:

- *"Confidence increased because the assessment verdict was 'correct' (accuracy 100%)."*
- *"Mastery improved because demonstrated proficiency was 96%."*
- *"Weakness detected because accuracy (10%) confirmed a gap on this topic."*
- *"Revision suggested because the evidence indicates unstable retention."*

Reasons are aggregated per node in the learner-state overlay.

---

## 5. Backward compatibility & architecture validation

- **Planner unchanged:** it still reads the Phase 2C computed snapshot only.
  The evidence-derived overlay is exposed for future consumers but is **not**
  wired into the planner's scoring path, so existing planner behavior is
  byte-identical.
- **Additive only:** one new collection, one read-only router, one ingest call
  at the assessment `/evaluate` boundary. No existing API, collection, mission,
  Company Intelligence, Company Context, revision scheduling, or planner scoring
  was modified. Regression suite: **200 passed**.
- **One-way flow verified:** the Assessment Engine produces evidence only; it
  never communicates with Planner, Mission Engine, Company Readiness, Revision
  Engine, Analytics, or AI Mentor. Learner Intelligence is the sole consumer.

---

## 6. Read API (additive)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/learner-intelligence/updates` | Append-only update history for the user |
| GET | `/api/learner-intelligence/state` | Aggregated learner-state overlay |

---

## 7. Future extensibility

- New assessment types need **no** Learner Intelligence changes — they emit the
  canonical evidence contract and flow through the same pipeline.
- A future planner-facing adapter can fold the learner-state overlay into the
  Phase 2C snapshot when that phase is scheduled (out of scope for 3B).
- The append-only history is analytics-ready (velocity of improvement,
  weakness recurrence, confidence trajectories from real evidence).
