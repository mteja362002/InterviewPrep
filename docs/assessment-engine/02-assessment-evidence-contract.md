# 02 · Assessment Evidence Contract

> The stable, canonical contract every assessment type produces and every
> future consumer reads — **without any assessment-type-specific logic.**

Phase 3A exposes exactly **one** evidence model: `AssessmentEvidence`
(`backend/assessment/schemas.py`, aliased as `Evidence`). This document is the
authoritative description of that contract. It was refined *before* Phase 3B so
the shape is fixed for Coding, MCQ, Behavioral, System Design, LLD, Resume, and
Debugging assessments alike.

---

## 1. Design principles

1. **One canonical model.** `Evidence is AssessmentEvidence` — there is never a
   per-type evidence class.
2. **Type-agnostic.** Consumers read normalized scalars + generic signals; they
   never branch on `assessment_type` to interpret evidence.
3. **Immutable.** `model_config = ConfigDict(frozen=True)`. Once an assessment
   completes, its evidence is a fixed, auditable record.
4. **Exposed, never applied.** Evidence is the OUTPUT of the Assessment Engine.
   The engine never writes planner, Learner Intelligence, mission, or revision
   state. Consumers decide how (or whether) to use it.
5. **Extensible without schema change.** Type-specific richness goes into the
   open `metrics` / `signals` / `tags` bags — new assessment types add detail
   without altering the model.
6. **Derived recommendations.** `AssessmentRecommendation` is computed from this
   evidence object, not from the raw score.

---

## 2. Schema (`schema_version = "1.0"`)

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | str | Contract version (`"1.0"`). |
| `assessment_id` | str | Source assessment id. |
| `user_id` | str | Learner id. |
| `assessment_type` | enum | Source type (informational only — not required to interpret evidence). |
| `roadmap_node_id` | str? | Node under assessment (nullable). |
| `mission_id` | str? | Linked mission (nullable). |
| `verdict` | enum? | `correct / partially_correct / incorrect`. |
| **Canonical normalized scalars** | | |
| `accuracy` | float 0..1 | How correct the response was. |
| `proficiency` | float 0..1 | Overall demonstrated skill. |
| `completion_quality` | float 0..1 | Thoroughness / coverage. |
| `confidence_delta` | float -1..1 | Signed confidence suggestion. |
| `difficulty_achieved` | str? | Difficulty tier demonstrated. |
| **Canonical boolean signals** | | |
| `weakness_confirmation` | bool | Evidence confirms a weakness. |
| `revision_trigger` | bool | Suggests revision is warranted. |
| `repeated_mistakes` | bool | Repeated failure across attempts. |
| **Extensibility (no schema change)** | | |
| `metrics` | dict[str,float] | Type-specific normalized detail (e.g. `dim_correctness`, `edge_case_coverage`). |
| `signals` | dict[str,bool] | Boolean signals mirrored for uniform dict access. |
| `tags` | list[str] | Qualitative markers (e.g. `optimal`). |
| `created_at` | str | ISO timestamp. |

**Backward-compatible accessors** (Python properties, not serialized):
`coding_accuracy → accuracy`, `problem_solving → proficiency`,
`topic_confidence_delta → confidence_delta`.

---

## 3. How each future type maps onto the same contract

| Type | `accuracy` | `proficiency` | `metrics` examples |
|------|-----------|---------------|--------------------|
| Coding | tests passed ratio | weighted rubric score | `edge_case_coverage`, `dim_complexity` |
| MCQ | correct options ratio | same | `per_option_analysis` |
| Behavioral | rubric adherence | communication score | `structure`, `impact` |
| System Design | requirement coverage | trade-off quality | `scalability`, `bottlenecks` |
| LLD | correctness of design | SOLID adherence | `extensibility`, `coupling` |
| Resume | ATS/keyword match | impact clarity | `keyword_coverage` |
| Debugging | bugs fixed ratio | root-cause quality | `regression_safety` |

Every type fills the **same** canonical scalars + signals; type-specific numbers
live in `metrics`. No consumer needs to know which type produced it.

---

## 4. Consumers (read-only, uniform)

`Learner Intelligence, Planner, Analytics, Revision Engine, AI Mentor, Company
Readiness` can all consume `AssessmentEvidence` (or the list from
`GET /api/assessments/evidence`) using only the canonical fields:

```python
# Example: a future Learner-Intelligence adapter (illustrative, not wired here)
for ev in evidence_list:
    if ev.revision_trigger:      ...   # schedule revision
    confidence_hint += ev.confidence_delta
    if ev.weakness_confirmation: ...   # confirm a weakness
```

No `if assessment_type == "coding"` branching is required.

---

## 5. Immutability & compatibility

- `AssessmentEvidence` is `frozen=True`; attempts to mutate raise. Reconstruction
  from the persisted `assessments` document (`Assessment(**doc)`) rebuilds the
  frozen object faithfully.
- Refinement was **additive**: canonical fields + bags were added and the
  original field names are preserved as properties. No database collection was
  added or altered; no planner / learner-intelligence / mission / API-route
  behavior changed.
