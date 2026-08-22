# CONSTITUTION-004 — Learner Intelligence

**Version:** 1.0  
**Status:** Active  
**Scope:** `backend/services/learner_intelligence/`  
**Authority:** Chief Software Architect  

---

## Purpose

The Learner Intelligence (LI) Engine models **HOW a learner learns** — not just what they have covered, but their behavioral patterns, learning velocity, retention quality, consistency, and readiness trajectory. This intelligence is injected into the mission planning pipeline as a bounded signal that helps the adaptive engine make better decisions.

LI is a **pure analytical layer**. It does not decide what to teach, generate content, evaluate performance, or write to the database directly. It observes, computes, and signals.

---

## Responsibilities

### Learner Intelligence Owns

- Computing all 10 behavioral learning signals from raw learner data
- Producing the `LearnerIntelligenceSnapshot` (the computed output)
- The consumption pipeline (`planner_adapter.py`) that converts the snapshot to a planning nudge
- Ingesting `AssessmentEvidence` into `knowledge_nodes` updates (`evidence_integration.py`)
- The `LearnerIntelligenceInput` dataclass (raw signal bundle)
- Explainability summaries (`explainability.py`)

### Learner Intelligence Does NOT Own

- Deciding which node to study (owned by Learning Engine Planner)
- Generating missions (owned by Mission Engine)
- Evaluating assessments (owned by Assessment Engine)
- Scheduling revisions (owned by Revision Engine)
- Storing learner state (owned by `knowledge_nodes` collection, written by `evidence_integration.py`)

---

## Scope

This constitution governs the entire `services/learner_intelligence/` package:

```
engine.py              — computation pipeline entry point
context.py             — LearnerIntelligenceInput (raw signal bundle)
snapshot.py            — LearnerIntelligenceSnapshot (computed output)
planner_adapter.py     — consumption pipeline (bounded nudge to planner)
velocity.py            — Signal 1: learning velocity
retention.py           — Signal 2: retention quality
confidence.py          — Signal 3: confidence trend
weakness.py            — Signal 4: weakness stability
consistency.py         — Signal 5: learning consistency
revision_health.py     — Signal 6: revision health
coding.py              — Signal 7: coding growth
mastery_trend.py       — Signal 8: topic mastery trend
difficulty.py          — Signal 9: difficulty adaptation
readiness.py           — Signal 10: interview readiness trend
explainability.py      — human-readable summaries
evidence_integration.py — evidence → knowledge_nodes update pipeline
evidence_api.py        — REST API for evidence ingestion
```

---

## Architectural Principles

### LI-001 — Deterministic Computation

The LI engine MUST produce identical output for identical input. No randomness, no time-based branching, no stochastic elements. `same inputs → same snapshot always`.

### LI-002 — No AI, No ML, No Prediction

The LI engine MUST NOT use any machine learning model, neural network, statistical prediction, or generative AI. All 10 signals are computed from deterministic formulas applied to existing data. This is intentional: determinism, auditability, and zero external dependencies are non-negotiable for the planning hot path.

### LI-003 — Defensive Never-Raises

The computation pipeline MUST NEVER raise an exception that propagates to the caller. Any internal computation failure MUST degrade gracefully to `empty_snapshot()`. The planning pipeline then falls back to pre-LI behavior. This guarantee is enforced by the `try/except` in `engine.build_learner_intelligence()`.

### LI-004 — Bounded Nudge Only

The LI signal injected into the Learning Engine MUST be a bounded additive adjustment (±). It MUST NOT hard-veto any candidate node, override the planner's primary recommendation, or introduce discontinuous jumps in node scores. The planner remains in control; LI is an advisory signal.

### LI-005 — No New MongoDB Collections

LI MUST NOT introduce new MongoDB collections. All LI computation consumes data from existing collections (`knowledge_nodes`, `problem_feedback`, `activity_events`) as inputs. LI output (`LearnerIntelligenceSnapshot`) is in-memory; it is not persisted as a document. The `evidence_integration.py` updates existing `knowledge_nodes` rows only.

### LI-006 — Separation of Computation and Consumption

`engine.py` computes the snapshot. `planner_adapter.py` converts it to a planning nudge. These MUST remain separate. The snapshot is a reusable multi-consumer artifact (Analytics, AI Mentor, future Mobile) — it is not a planner-specific object.

### LI-007 — Evidence Integration is the Only Write Path

The only write operation in LI is `evidence_integration.process_evidence()` writing to `knowledge_nodes`. This MUST be the single place where assessment evidence is translated into learner state updates.

---

## Design Philosophy

LI exists because simple progress tracking (binary completed/not-completed) is insufficient for adaptive learning. Two learners who have completed the same set of nodes may be in radically different states:

- One completed them quickly with high confidence
- One completed them slowly with hints and low confidence

LI captures this nuance by modeling behavioral patterns over time, not just completion events. It answers: "Is this learner on an improving trajectory or a declining one?"

LI is intentionally placed **between** the raw learner data and the planning decision. It pre-processes signals so the planner doesn't need to do multi-signal analysis inline. This makes the planner simpler and the signals individually testable.

The decision to make LI a **bounded nudge** rather than a decisive signal is deliberate: it preserves the curriculum-driven ordering of the roadmap while allowing the planner to adapt at the margins. A learner who is struggling should see more revision — but not so much that they never advance.

---

## The 10 Learner Signals

| # | Signal | Module | What It Measures | Label Vocabulary |
|---|--------|--------|-----------------|-----------------|
| 1 | Learning Velocity | `velocity.py` | Rate of topic completion over time | fast / normal / slow / stalled |
| 2 | Retention Quality | `retention.py` | How well completed topics are retained (revision success rate) | strong / moderate / weak / unknown |
| 3 | Confidence Trend | `confidence.py` | Direction of confidence over recent sessions | improving / stable / declining / unknown |
| 4 | Weakness Stability | `weakness.py` | Whether weaknesses are being resolved or persisting | resolving / stable / worsening / unknown |
| 5 | Learning Consistency | `consistency.py` | Regular vs. bursty study behavior | consistent / moderate / bursty / inactive |
| 6 | Revision Health | `revision_health.py` | Proportion of overdue revision items | healthy / moderate / overloaded / unknown |
| 7 | Coding Growth | `coding.py` | Improvement in coding problem-solving metrics | growing / stable / declining / insufficient_data |
| 8 | Topic Mastery Trend | `mastery_trend.py` | Per-track mastery trajectory | rising / flat / declining (per track) |
| 9 | Difficulty Adaptation | `difficulty.py` | Whether the learner is ready for harder problems | ready_to_advance / maintain / reduce |
| 10 | Interview Readiness | `readiness.py` | Composite readiness trend toward the target date | on_track / at_risk / ahead | 

---

## LearnerIntelligenceInput Contract

```python
@dataclass
class LearnerIntelligenceInput:
    progress_rows: list[dict]       # All knowledge_nodes rows for the user
    recent_completions: list[dict]  # Last 30 completed node rows
    completed_dates: list[str]      # ISO dates of completions (for consistency)
    recent_track_ids: list[str]     # Track distribution (for fatigue detection)
    skipped_node_ids: set[str]      # Skipped nodes (for skip-deferral)
    position: Optional[str]        # Experience band: student|0-1|1-3|3-5|5+
```

**Invariants:**
- `has_any_signal()` returns `False` when all inputs are empty → engine returns `empty_snapshot()`
- All inputs are read-only. The computation pipeline MUST NOT mutate input data.

---

## LearnerIntelligenceSnapshot Contract

```python
@dataclass
class LearnerIntelligenceSnapshot:
    velocity: VelocitySignal
    retention: RetentionSignal
    confidence_trend: ConfidenceTrendSignal
    consistency: ConsistencySignal
    revision_health: RevisionHealthSignal
    weakness_stability: WeaknessStabilitySignal
    mastery_trends: dict[str, MasteryTrendSignal]  # keyed by track_id
    coding_growth: CodingGrowthSignal
    difficulty_adaptation: DifficultyAdaptationSignal
    readiness_trend: ReadinessTrendSignal
    empty: bool  # True when computed from insufficient data
```

**Invariants:**
- `empty=True` → all signals are default/unknown. Planner falls back silently.
- `empty=False` → all 10 signals are computed and valid.
- Snapshot is in-memory only. It is NOT persisted.
- Snapshot is immutable once constructed.

---

## Planner Adapter Contract

`learner_intelligence_signal(snapshot, node_id, track_id) → float`

Returns a bounded additive score adjustment:
- Range: `[-BOUND, +BOUND]` where `BOUND` is defined in `planner_adapter.py`
- Positive: the signal suggests this node should be prioritized
- Negative: the signal suggests this node should be de-prioritized
- Zero: no signal or empty snapshot

The planner MUST treat this as **one additive component** of the total score, not a multiplier or override.

---

## Evidence Integration Contract

`evidence_integration.process_evidence(db, evidence: AssessmentEvidence) → None`

**Input:** An `AssessmentEvidence` object (from Assessment Engine).

**Effects:**
1. Update `knowledge_nodes` for `evidence.roadmap_node_id`:
   - `confidence` += `confidence_delta` (clamped to [0, 10])
   - `mastery_percentage` updated based on `proficiency`
   - `weakness_score` updated based on `accuracy`
   - `status` transitioned if thresholds met
2. If `revision_trigger == True`: call `revision_engine.mark_node_for_revision()`
3. If `weakness_confirmation == True`: create/update `WeaknessRecord`

**Invariants:**
- MUST NOT create new `knowledge_nodes` documents (upsert only on existing)
- MUST NOT touch any collection other than `knowledge_nodes` and `weaknesses`
- MUST NOT call the Assessment Engine or the Learner Intelligence computation pipeline
- MUST be idempotent: processing the same evidence twice MUST produce the same final state

---

## Explainability Contract

`summarize_contributions(snapshot) → list[str]`  
`summarize_snapshot(snapshot) → str`

Returns human-readable sentences derived from the actual signal values in the snapshot. MUST NOT hardcode explanations. Every sentence MUST reference actual signal labels.

The AI Mentor's context builder MAY consume these summaries. They are also used in the `recommendation_insight` object stamped on `DailyMission`.

---

## Data Ownership

| Collection | Access | Notes |
|-----------|--------|-------|
| `knowledge_nodes` | Read (computation) + Write (evidence_integration only) | Primary LI input and only LI write target |
| `problem_feedback` | Read only | Coding growth, confidence trend, retention signals |
| `activity_events` | Read only | Consistency signal |
| `assessments` | Read only (via evidence object passed in) | Evidence integration input |

LI MUST NOT read from `daily_missions`, `mentor_conversations`, or `knowledge_content`.

---

## Allowed Dependencies

The LI engine MAY depend on:

- Standard Python library
- Each other (within `services/learner_intelligence/`)
- `services/revision_engine.py` (for `mark_node_for_revision`, called from `evidence_integration.py`)

---

## Forbidden Dependencies

❌ `mission_engine.py`  
❌ `assessment/`  
❌ `ai_service.py` or any LLM  
❌ `roadmap.py` (LI is pattern-agnostic)  
❌ `problem_bank.py`  
❌ `services/learning_engine/` (LI is consumed BY learning_engine, not the reverse)  
❌ Any FastAPI router  
❌ Any new MongoDB collection write  

---

## Performance Expectations

| Operation | Target |
|-----------|--------|
| `build_learner_intelligence(inp)` | <50ms for typical learner (~100 progress rows) |
| `learner_intelligence_signal()` | <1ms (pure computation on snapshot) |
| `process_evidence()` | <100ms (1 MongoDB write) |
| Input assembly | O(n) in progress_rows count |

The snapshot SHOULD be computed once per mission generation cycle and reused within that cycle. It SHOULD NOT be recomputed for each candidate node.

---

## Invariants

1. `build_learner_intelligence()` NEVER raises — it returns `empty_snapshot()` on any error.
2. `learner_intelligence_signal()` returns exactly one float, always.
3. `process_evidence()` is idempotent.
4. The snapshot is always computed from the same set of signals — no signals are conditionally omitted.
5. A snapshot with `empty=True` MUST NOT have non-default signal values.
6. The planner adapter's output is always within the documented bounded range.

---

## Anti-patterns

❌ Using LI to hard-veto a node (the output MUST be a bounded nudge, not a gate)  
❌ Persisting the `LearnerIntelligenceSnapshot` to MongoDB  
❌ Computing signals in the planner adapter (signals belong in individual signal modules)  
❌ Calling `build_learner_intelligence()` multiple times per mission generation  
❌ Making `evidence_integration.py` depend on the computation pipeline  
❌ Using AI to generate signals (signals MUST be deterministic formulas)  
❌ Allowing one signal module to call another (signals are independent)  
❌ Using LI signals for UI decisions (LI is a backend planning signal only)  

---

## Future Evolution

- **New signals:** Add a new `*_signal.py` module, implement the signal, add it to `LearnerIntelligenceInput`, add to `LearnerIntelligenceSnapshot`, wire into `engine.build_learner_intelligence()`. The planner adapter and all other consumers are unchanged.
- **Persisted snapshots:** A future phase may persist `LearnerIntelligenceSnapshot` to a `learner_intelligence_snapshots` collection for Analytics. The computation pipeline is unchanged; add a persistence step after `build_learner_intelligence()`.
- **Analytics dashboard:** `LearnerIntelligenceSnapshot` is the data foundation for a future Analytics page. Analytics MUST read the snapshot (or persisted version) — it MUST NOT recompute signals independently.
- **Mobile notifications:** The `readiness_trend` signal drives "You're on track for your interview" / "You're falling behind" push notifications. Mobile reads the snapshot from the Analytics API.
- **Team LI:** A team-level snapshot aggregates individual snapshots. Implemented as a separate `team_learner_intelligence/` package consuming individual LI snapshots.
