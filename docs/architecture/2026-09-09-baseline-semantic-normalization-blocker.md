# Onboarding Baseline & Learner Evidence Semantic Normalization

**Outcome: implementation stopped at the mandatory forensic gate.** The approved product semantics are clear; the blocker is the missing provenance of historical learner state. Hard-stop conditions **2 and 3** apply. No implementation, migration, record reset, or partial rollout was performed.

Checkout: `c560127`, unchanged since the preceding audit. Inspection and fresh Mongo reads were completed on 2026-09-09. The preceding audit's scripts/tests/documents remain in the workspace; they are not new implementation changes in this sprint.

## 1. Root cause and exact blocker

Onboarding declarations become ordinary `knowledge_nodes` fields without provenance. Later real activity modifies those same fields, sometimes starting from an onboarding-derived value. A record can therefore contain a genuine completion event and an inseparable historical mixture in its mastery score.

The missing information cannot be recovered from a complete event log: direct KB confidence/status writes do not maintain a per-field before/after history. The assessment-derived append-only ledger exists, but does not cover every knowledge-node writer. It also contains no records for these three profiles.

The user explicitly requires both evidence-only actual KB metrics and preservation of genuine historical mastery. Treating every unknown value as actual would violate the former; removing unknown values from actual totals could downgrade genuine unjournaled learning. Persisting a new `source` flag cannot establish what produced an old value.

### Evidence paths

| File/function | Verified behavior | Why it matters |
|---|---|---|
| `backend/models.py:62`, `OnboardingSelfAssessment` | Eight integer 0–10 fields | No Projects/Resume/Behavioral schema extension is needed or authorized |
| `backend/routes_user.py`, `submit_onboarding` | Stores declaration, initializes roadmap progress, calls seed | Declaration and learning-state initialization are coupled |
| `backend/services/progress_engine.py:290`, `seed_knowledge_nodes_from_self_assessment` | Skips prerequisite roots; lower stages get 85/`completed`; selected stage gets rating×10/`in_progress` | Creates actual-looking mastery/status for Java, DSA, OS, DBMS, CN, LLD, HLD; PF differs because it is the root |
| Same seed | Attempts0, completion date null, revision dates null, revision stage0 | Does not invent nonzero attempts/dates; nevertheless creates false completion/mastery signals |
| `backend/models.py:301`, `KnowledgeNode` | No source, provenance, or track field | Stored representation cannot distinguish declaration from measured score |
| `backend/routes_missions.py:231`, `_record_completed_task_progress` | Reads existing mastery, otherwise declaration×10; applies gain; writes completed status/date and revision | A real task completion does not prove the resulting entire mastery score is evidence-only |
| `backend/routes_missions.py`, problem-feedback sync | Averages previous confidence with actual feedback | Can continue blending a seeded historical value into a genuine update |
| `backend/routes_roadmap.py:519`, `update_confidence` | Writes derived score/status and timestamp directly; no immutable update history | Legitimate confidence updates can have the same score/status shape as a seed |
| `backend/routes_roadmap.py:554`, `update_status` | Preserves nonzero existing mastery when marking complete; stamps completion/revision | A completion marker identifies an event, not the source of the retained score |
| `backend/routes_roadmap.py`, notes/flags/attempt routes | Update parts of existing rows and `updated_at` | A later timestamp cannot identify which score/status fields have evidence provenance |
| `backend/services/progress_repository.py` | Shared score/confidence/field upserts without provenance or prior-value journal | No general reconstruction boundary exists here |
| `backend/server.py`, startup backfill | Writes from legacy `knowledge_progress` and feedback aggregates; refreshes existing derived fields | Seed is not the only historical initialization/projection writer |
| `backend/services/roadmap_progress/initializer.py` | Separate default `roadmap_node_progress` records for all learning nodes | Has track identity but does not establish provenance of `knowledge_nodes` values |
| `backend/services/learner_intelligence/evidence_integration.py:145`, `ingest_evidence` | Writes assessment-derived updates to append-only repository | This is not a complete history of direct KB or mission-progress changes |
| `backend/services/learner_intelligence/update_repository.py` | Explicitly says planner/revision do not consume its update history | Ledger presence alone cannot repair the canonical progress store |

A concrete collision: Java's advanced-stage onboarding score70 is `in_progress`, confidence7, mastery70, weakness30. A genuine KB confidence update to7 produces those same fields. Zero attempts, no completion date, or an exact match to the current seed formula cannot prove that no actual confidence update occurred. Notes/bookmarks can also change timestamps independently of scores. No such heuristic was used to classify or modify records.

## 2. Approved semantic model

The following model is accepted from this sprint's instruction; it does not need another product approval:

```text
Persisted onboarding declaration (eight subjects, 0–10)
        ↓
Separately labeled onboarding baseline (0–100 display)
        ↓
LearnerContext → deterministic effective knowledge
        ↓
Planner / eligibility / prerequisite credit (not persisted evidence)

Actual supported learning events
        ↓
Canonical actual learner evidence
        ↓
KB actual progress/mastery, completion counts, revision/activity views
```

Readiness can remain an explicitly derived estimate using declared and actual inputs under its existing formula. It must not be relabeled curriculum completion. Module/subject progress must still derive from the canonical actual evidence population; no subject-level baseline copied into leaf mastery.

The unresolved question is how to carry forward **legacy values of unverified origin**, including mixed mastery attached to known completed events, while satisfying that model and preserving their values.

## 3. Current representation and forensic findings

No new representation was installed. Current declaration remains in `onboarding.self_assessment`; current mastery/status remain mixed in `knowledge_nodes`; effective knowledge remains a runtime context calculation.

### Fresh production-shaped inventory

Read-only Mongo inventory captured at `2026-09-09T14:20:54Z`; detailed counts and dated rows are in `test_reports/baseline_semantic_legacy_inventory.json`.

| Profile | Knowledge rows | With provenance/source | With stored track | Unresolvable node/track | Dated completions |
|---|---:|---:|---:|---:|---:|
| Suresh | 89 | 0 | 0 | 0 | 1 Java |
| Gowri | 132 | 0 | 0 | 0 | 2 DSA, 1 OS |
| Kusuma | 368 | 0 | 0 | 0 | 0 |
| Total | 589 | 0 | 0 | 0 | 4 |

For each profile, `learner_intelligence_updates`, `assessments`, `problem_feedback`, and legacy `knowledge_progress` each contain zero records. Activity contains one `task_completed` event for Suresh and three for Gowri. These support recorded task completion; they do not certify every stored mastery value or prove absence of direct confidence/status activity.

- Suresh's Java introduction is completed with mastery21.2, completion date `2026-09-09T13:23:04.306104+00:00`, and next revision2026-09-10. That value is consistent with a task gain applied to onboarding-derived20; the task-write path permits this, but the current row does not certify the source of its prior value. Preserving the completed event is straightforward; claiming all21.2 is actual-only mastery is not.
- Gowri has 48 Java rows: 35 completed, 13 in progress, no completion dates, no attempts or revision markers. These match the shape expected from seeding, but **were not classified as proven seed-only data**. Her DSA and OS dated completion/revision records were preserved.
- Kusuma has 368 rows, including 73 DSA and127 LLD completed statuses without completion dates. They were not reset or relabeled. The unrelated candidate-pool issue was not addressed.

### Track identity is recoverable, but not yet normalized

For all589 inspected rows, `(roadmap_version, node_id)` resolves to canonical roadmap track identity. Deriving it on read is feasible without guessing. Current `build_learner_context` does not enrich it: track averages and evidence counts require `row.track`. Simply adding track now would cause seeded `completed` rows to enter the “actual” blend, so identity normalization must follow the legacy provenance policy, not bypass it.

### Formulas remain distinct

| Formula/path | Current semantic role |
|---|---|
| Seed stage projection | Onboarding-derived state persisted as learning state; incompatible with approved actual-evidence semantics |
| `build_canonical_progress` | Structural aggregation of stored leaf status/mastery; cannot determine field provenance |
| `track_average_mastery`, `track_completion_count` | Intended actual-evidence inputs, but depend on missing row.track and completed statuses that can be seeded |
| `effective_knowledge_score` | Planner blend α×actual+(1−α)×declaration×10, α=n/(n+2) |
| `effectively_completed_tracks` | Effective knowledge≥70 prerequisite credit |
| `effective_completed_subject_ids(roadmap)` | Union of actual foundation/core-completed subjects and effective tracks |
| `build_all_sessions` | Already requires explicit `effective_completed_subjects`; planner passes the unified set |
| `virtual_completed_node_ids` | Runtime-only planner completion; no persistence |
| Session module/subject “mastery” | Completion coverage, not the KB's mean stored mastery |
| KB API/React | Backend stored mastery rollup, display rounding; no baseline label/population distinction |
| Dashboard knowledge / legacy knowledge tree | Canonical touched-subject scores, with onboarding fallback for untouched subjects |
| Readiness / company readiness | Derived weighted readiness estimates; must stay distinct from actual curriculum progress |
| Revision | Schedule fields on canonical rows; seed's defaults are not actual revision events |
| Analytics / weekly activity | Analytics combines dashboard and summary; weekly activity consumes activity data rather than proving mastery provenance |
| AI Mentor context | Reads knowledge-node mastery/status and progress counts; inherits source ambiguity but does not supply a reliable evidence classifier |

The eight-subject model and required effective-completion input already exist. No prerequisite or ranking change is necessary merely to represent a separate declared baseline. However, removing persisted stage seeds without preserving the intended planner-only projection can change candidate inputs and missions. That compatibility work cannot safely use unknown legacy mastery as actual evidence.

### Onboarding updates

The current route invalidates today's mission for self-assessment or position changes. Target companies, target date, and hours also feed ranking/pacing/composition, but do not currently trigger invalidation. Existing rows are intentionally not overwritten by repeated seeding, leaving old projected state possible after declaration changes. No cache-invalidation change was made while the hard stop was active.

## 4. Files changed in this sprint

Only diagnostic/report artifacts were added:

| Path | Purpose |
|---|---|
| `docs/architecture/2026-09-09-baseline-semantic-normalization-blocker.md` | This hard-stop walkthrough and decision record |
| `test_reports/baseline_semantic_legacy_inventory.json` | Fresh, read-only legacy/source/track/event inventory |
| `test_reports/baseline_semantic_sprint_focused.xml` | Focused pytest results |
| `test_reports/baseline_semantic_sprint_regression.xml` | Broader practical backend pytest results |

No application, schema, API, frontend, curriculum, AI, or test implementation was changed. The preceding sprint's untracked files remain untouched.

## 5. Data / migration impact and smallest decision

No database writes or migration were performed. Ambiguous records were preserved exactly. No additional Mongo users were created. No claim of a deterministic backfill or required manual migration is made; sufficient historical evidence has not been found.

**Smallest decision needed:** authorize a legacy carry-forward policy: preserve unverifiable stored mastery/status values as separately labeled **unverified legacy progress**, without asserting either onboarding or actual provenance; retain independently supported completion/attempt/date/revision facts; establish separately attributable actual mastery from subsequent supported activity. Existing legacy values must remain inspectable and must not be silently zeroed or relabeled as evidence.

That requires explicit acceptance that an old combined mastery number may remain available as legacy information rather than as a certified actual-progress percentage. If the product instead requires every historical number to remain inside the actual metric, independently verifiable source/history data is necessary; this repository cannot manufacture it. Planner compatibility treatment of those legacy values must be stated as legacy input, not claimed to be actual evidence.

This request does **not** reopen the approved actual-versus-onboarding display model. It resolves how its rules apply to historical data that lacks the information needed to populate it truthfully.

## 6. Tests

Fresh runs preserved the configured `-n 2 --dist loadscope`. No tests were added, weakened, deleted, or rewritten because implementation stopped before a representation was selected. The preceding audit's five invariant tests were rerun, not counted as new tests.

Focused: **33 passed, 1 failed in3.91s**.

| Test file (under `backend/tests`) | Passed | Failed |
|---|---:|---:|
| `test_canonical_progress.py` | 7 | 0 |
| `test_effective_completion_verification.py` | 8 | 0 |
| `test_effective_prerequisite_completion.py` | 6 | 0 |
| `test_learner_audit_invariants.py` | 5 | 0 |
| `test_onboarding_knowledge_seed.py` | 4 | 1 |
| `test_planner_ranking_integration.py` | 3 | 0 |

Broader backend: **155 passed, 3 failed in6.41s**.

| Test file (under `backend/tests`) | Passed | Failed |
|---|---:|---:|
| `test_learning_engine.py` | 16 | 0 |
| `test_adaptive_planning_phase4_step2.py` | 17 | 0 |
| `test_curriculum_sync_phase2_metadata.py` | 16 | 0 |
| `test_interview_pacing.py` | 7 | 1 |
| `test_company_aware_planner_phase2b.py` | 19 | 0 |
| `test_company_aware_ranking.py` | 7 | 0 |
| `test_learning_stage_engine.py` | 5 | 0 |
| `test_eligibility_engine.py` | 5 | 0 |
| `test_universal_node_actions.py` | 5 | 0 |
| `test_mission_context.py` | 5 | 0 |
| `test_mission_context_cta.py` | 5 | 0 |
| `test_candidate_generation.py` | 2 | 2 |
| `test_learner_intelligence_phase2c.py` | 43 | 0 |
| `test_roadmap_node_progress.py` | 3 | 0 |

Exact failing cases, all reproduced in the preceding unchanged-code audit:

1. `test_onboarding_knowledge_seed.py::test_seed_covers_every_roadmap_track_with_stage_aware_rows`: expects neutral5 for isolated tracks, implementation uses zero. Stale expectation; not changed.
2. `test_candidate_generation.py::test_candidate_pool_is_compact_and_within_expected_range`: fixture omits row.node_id and does not satisfy the current subject DAG; eligible0, expected>30.
3. `test_candidate_generation.py::test_weakest_or_revision_due_track_is_prioritized`: DSA revision fixture does not unlock DSA prerequisites. No implementation change made to accommodate it.
4. `test_interview_pacing.py::test_mission_practice_count_still_driven_by_study_hours_at_same_urgency`: passes identical pacing capacity while varying onboarding hours; both practice counts3. Existing fixture/contract mismatch.

No collection/environment failures occurred in these fresh runs. External preview-server/mutating integration suites were not run. No failures are caused by this sprint's application changes, because there are none. The full proposed eight-subject/provenance/mixed-evidence acceptance suite is **not implemented or claimed green**.

XML artifacts contain every executed test classname/case. Focused command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_learner_audit_invariants.py tests/test_onboarding_knowledge_seed.py tests/test_canonical_progress.py tests/test_effective_prerequisite_completion.py tests/test_effective_completion_verification.py tests/test_planner_ranking_integration.py -q --tb=short --junitxml=../test_reports/baseline_semantic_sprint_focused.xml
```

Broader command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_learning_engine.py tests/test_learning_stage_engine.py tests/test_eligibility_engine.py tests/test_candidate_generation.py tests/test_adaptive_planning_phase4_step2.py tests/test_company_aware_ranking.py tests/test_company_aware_planner_phase2b.py tests/test_learner_intelligence_phase2c.py tests/test_roadmap_node_progress.py tests/test_curriculum_sync_phase2_metadata.py tests/test_universal_node_actions.py tests/test_interview_pacing.py tests/test_mission_context.py tests/test_mission_context_cta.py -q --tb=short --junitxml=../test_reports/baseline_semantic_sprint_regression.xml
```

## 7. Manual verification

Performed read-only database verification for existing Suresh, Gowri, and Kusuma profiles, including all current row fields, canonical node/track resolution, completion dates, revision fields, activity kinds, and evidence-history collection counts. No browser acceptance test of a new UI is claimed; no new UI exists.

Suresh's actual Java completion/revision remains recorded. Gowri's existing Java values and actual DSA/OS events remain intact, without classifying her undated Java rows by their appearance. Kusuma's learner state and mission records remain untouched. Projects/Resume/Behavioral were not given onboarding fields. No AI call, content generation, Gateway modification, or performance intervention occurred in this sprint.

## 8. Regression review

Roadmap, prerequisites, mission generation, scoring/ranking, company intelligence, readiness, revision, dashboard, analytics, KB rendering, and AI Gateway are all **unchanged**. The protected effective-completion and planner/ranking suites pass. Existing defects, including missing runtime track identity and the separate session candidate-pool issue, are not represented as fixed.

## 9. Dead / duplicate logic

The persisted onboarding seed is incompatible with the approved future model, but is **not dead code**: `submit_onboarding` calls it and stage/eligibility/ranking consume its resulting rows. It cannot simply be deleted without preserving intentional planner-only baseline interpretation.

The mission completion fallback from declaration, existing-value confidence averaging, and legacy startup projections are additional active ways onboarding/legacy values enter learner state. The separate roadmap progress initializer has production and test callers. No cleanup or compatibility deletion was performed.

## 10. Remaining risks

- Missing per-field provenance/history prevents reliable classification and decomposition of legacy mastery.
- Physical preservation of an unknown value does not decide whether it belongs in actual-progress totals.
- Identifying a genuine completion event does not make its retained score evidence-only.
- Track enrichment alone would admit seeded completion statuses into actual evidence weighting.
- Removing the seed without a planner-only replacement changes stage/candidate inputs even if ranking weights are unchanged.
- Existing per-version read selection, display fallback, and cache-invalidation inconsistencies remain.

## 11. Explicit invariants at the stop

PASS means verified within the stated scope; FAIL includes unmet/not implemented requirements. Preservation alone is not success for the normalization sprint.

- **FAIL** — Onboarding baseline is not actual learning evidence: current seed/mixed-write behavior still violates separation.
- **FAIL** — Actual KB progress is evidence-based: legacy mixed values still feed current rollups.
- **FAIL** — All eight self-assessment subjects follow the same semantic model: current root-versus-staged initialization remains.
- **PASS** — Effective planner knowledge remains deterministic: existing implementation unchanged; protected focused tests pass.
- **PASS** — Effective completion does not create fake learning evidence: runtime virtual completion remains non-persistent; distinct seed defect remains as above.
- **PASS** — Genuine learner evidence is preserved: no records modified.
- **PASS** — Ambiguous legacy data is not guessed: no provenance assigned, inferred, or migrated.
- **FAIL** — Track identity is safe end-to-end: canonical identity resolves for all589 inspected rows, but runtime context enrichment remains unfixed.
- **FAIL** — Planner eligibility remains consistent end-to-end: effective-completion/Java prerequisite tests pass and behavior is unchanged, but previously identified session/eligibility divergence remains outside this sprint.
- **PASS** — No ranking/weight changes were introduced.
- **PASS** — No AI learning-state decisions were introduced.
- **FAIL** — Tests pass: 188 passed, 4 pre-existing failures; normalization acceptance coverage remains blocked.
