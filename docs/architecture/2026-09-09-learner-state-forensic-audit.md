# Learner state, ranking, and KB generation: forensic audit

Date: 2026-09-09. Checkout: `c560127`. Production implementation was clean when the audit began.

**Disposition: semantic hard stop. No production code, learner records, mission records, curriculum, ranking weights, or shared content cache were changed.** The existing contracts conflict over whether declared baseline may become completed learning. Changing KB percentages without resolving that conflict would conceal it. The requested effective-completion and planner/ranking fixes remain intact.

The audit inspected onboarding models/UI/routes, both progress stores, canonical progress, roadmap metadata and prerequisite traversal, context, eligibility, stage/session progression, ranking/priority, mission composition/history, dashboard/analytics, evidence ingestion, KB React/query hooks, content routes/service/prompts, Gateway/routing/adapters, architecture documents, and related tests. The prompt's `backend/services/learning_engine/roadmap.py` does not exist; the actual roadmap implementation is `backend/roadmap.py`.

## Evidence and limits

- `test_reports/learner_paths_audit.json`: configured MongoDB profiles, full per-track state, all eligibility-engine candidates plus session representatives, every scoring term, candidate inclusion flags, current replay, stored missions, Java module/topic rollups, and PF matrix. Captured at 13:47 UTC. The database display names are Suresh Mogadala, Gowri Mogadala, and Kusuma Mogadala.
- `backend/scripts/audit_learner_paths.py`: reusable exact-name lookup parameters; no user-dependent algorithm. Reads the same inputs and enables the same company/learner intelligence flags as the mission route. Calls the pure planner and mission builder, never the mission-generation write route.
- `test_reports/kb_generation_audit_network.json`: successful real AI Gateway probe after network permission. Mongo reads are real; generation cache miss and resulting write are in memory. No production cache was cleared or populated.
- `test_reports/kb_generation_audit.json`: first, sandbox-constrained probe. Its provider connection errors are environmental, not evidence of a production outage.
- Stored mission snapshots are historical; current replay includes subsequent activity and recency/fatigue from those stored missions. The original full candidate pool was not persisted. Current replay reproduces Kusuma's focus, but cannot prove every historical score was identical.
- The screenshots themselves were not supplied. Reported values were checked against current database rows and backend/React calculations, not against pixels.

## Issues 1 and 3: PF baseline disappears at seeding, not in React

Exact path:

`MissionInit.jsx / SELF_ASSESSMENT_TOPICS` → `OnboardingSelfAssessment` → `routes_user.submit_onboarding` → `seed_knowledge_nodes_from_self_assessment` → `knowledge_nodes` → `load_user_progress_rows` → `build_canonical_progress` → `routes_roadmap._rollup_from_progress` → `/api/roadmap` → `KnowledgeBase.jsx`.

PF is accepted as an integer 0–10 and remains in the Mongo onboarding document. In `backend/services/progress_engine.py:348`, the seed skips every `roadmap.root_subject_ids()` track **before reading its explicit rating**. The current DAG has one academic root, PF. The exclusion applies equally to PF=0, 7, 9, and 10. It is structural, not learner-specific.

The canonical progress engine accepts only roadmap and progress rows, not onboarding. With no PF rows it correctly produces 0 mastery, 0 completed topics, and `not_started`. The API and React carry that through; React only rounds `mastery_percentage`.

Separately, `LearnerContext.effective_knowledge_score` reads the intact declaration. With no evidence, effective knowledge is rating × 10. At 70 or above, PF belongs to the effective prerequisite-completion set. Virtual node completion remains in memory. The session pipeline receives the unified effective set, preserving the previous fix.

| PF declaration | Fresh seed PF rows | Context effective score | Effective prerequisite completion | Canonical/KB mastery | Fresh-profile mission |
|---|---:|---:|---|---:|---|
| 0 | 0 | 0 | No | 0 | `pf.intro.core` |
| 7 | 0 | 70 | Yes | 0 | `java.basics.programming_intro` |
| 9 | 0 | 90 | Yes | 0 | `java.basics.programming_intro` |
| 10 | 0 | 100 | Yes | 0 | `java.basics.programming_intro` |

This matrix uses the real seed/context/planner/rollup code with in-memory persistence, all other ratings zero, student position, and no target-company/history signals. It does not create four Mongo users. Current Mongo confirms zero PF rows for all three real profiles. Suresh's PF effective score is 90; Gowri's and Kusuma's are 100.

The separate `roadmap_node_progress` initializer creates default rows for all 983 learning nodes. Those rows do not feed the KB or planner. Their existence does not rescue the missing PF baseline in `knowledge_nodes`.

**Contract conflict:** context comments explicitly say effective completion is planner-only and KB uses actual completion. The seed and `test_programming_fundamentals_is_never_seeded_from_onboarding` explicitly require PF to be earned and start at zero even with an explicit rating. But the same seed manufactures `completed` statuses for other subjects from declarations. Dashboard knowledge additionally falls back to declaration × 10 for untouched tracks. There is no consistent evidence-only KB model, nor an approved display projection of effective knowledge.

Thus Issues 1 and 3 share the same proven cause. The baseline is retained in onboarding and omitted from the KB projection, rather than lost from Mongo entirely. Correcting PF alone to 90/100 would invent a different semantic for one root subject.

## Issue 2: Java's 80/85 arithmetic is consistent; its evidence semantics are not

`progress_engine._stage_for_rating(7)` selects `advanced`. Every earlier-stage Java learning node gets score 85 and status `completed`; advanced-stage nodes get 70 and `in_progress`. Rows have no completion date, zero attempts, and no source/provenance field.

Current Gowri Mongo contains 48 Java rows: 35 completed, 13 in progress, zero completion dates, zero attempts. Programming Basics contains six visible 85% completed topics. Its mean is 85%. Seven Java modules have mastery 85 and four have mastery 70:

`(7 × 85 + 4 × 70) / 11 = 79.545… → API 79.55 → React 80%`.

This is not an 85-versus-80 rounding defect. Module completion is 100% for Programming Basics while module mastery is 85%; binary completion and quality score are separate existing fields. The misleading part is that the completion originated from a declaration but is displayed like completed learning.

The canonical engine averages immediate children equally, recursively; it does not weight every leaf equally across differently sized modules. Completion counts do aggregate leaves. Do not replace the weighting without deciding the intended metric.

Current Suresh KB values are PF 0, Java 1.84, DBMS 1.67, OS 0.83. React rounds them to 0, 2, 2, 1. Java has one subsequently completed node, so today's raw rows are not an untouched onboarding snapshot.

### Multiple formulas discovered

| Consumer | Existing calculation | Consequence |
|---|---|---|
| Canonical leaf mastery | Stored `mastery_percentage` | Baseline and evidence share a field |
| Canonical parent mastery | Mean immediate-child mastery | Hierarchical weighting, empty descendants zero |
| Canonical completion | Completed/mastered leaf count ÷ all leaves | Distinct from mastery; revision-due excluded |
| KB leaf adapter | Recalculates status/completion, including date-derived revision-due | Can disagree with canonical parent, which does not normalize revision dates |
| Context effective knowledge | α × mean row mastery + (1−α) × declared baseline; α=n/(n+2) | Planner-only blend, not a roadmap rollup |
| Subject progression “mastery” | Fraction of completed/mastered learning nodes, plus foundation/core subset | Named mastery but actually completion coverage |
| Stage engine | Means over seeded/present track nodes and stage status | Different population from full-tree KB mean |
| Dashboard knowledge | Canonical score for touched subject, otherwise baseline × 10 | PF can display differently from KB |
| Readiness | Company/default weighted subject scores | Intentionally different concept, not curriculum completion |

`subject_progression.compute_module_mastery` and `compute_subject_mastery` are used in live session construction; they are not dead duplicates. Their names and contracts need clarification, not automatic deletion. `routes_missions._get_knowledge`, `/roadmap/summary`, dashboard, and analytics reuse some canonical data but do not expose one interchangeable percentage.

## Shared learner-state defects

1. **Missing curriculum identity enrichment:** `KnowledgeNode`, the seed, and canonical repository writes do not store `track`. The loader returns raw rows. `build_learner_context` does not derive track from `node_id`. Yet context completion counts/mastery and learner-intelligence grouping read `row['track']`. All inspected rows for these profiles lack it. Every context evidence count is zero, including Suresh's real Java completion and Gowri's real DSA/OS completions. Their effective scores therefore remain at onboarding values. Many unit fixtures include track, masking the production shape mismatch.
2. **Source ambiguity:** onboarding assigns actual-looking completion statuses. Simply enriching track would make those seeded completions count toward the supposedly actual-evidence blend. Fixing identity alone is unsafe until declaration provenance and legacy-row treatment are decided. Dates/attempts are useful forensic clues, but are not a safe universal migration classifier.
3. **Onboarding scope mismatch:** the frontend offers eight subjects, and `OnboardingSelfAssessment` defines only those eight. Projects/Resume/Behavioral fields supplied outside that UI are ignored by Pydantic. Their reported scores are absent in all inspected onboarding documents. Missing independent-track ratings seed zero, and rank as complete knowledge gaps. This is not proof those extra values were submitted through this checkout's UI. The supplied profile specification exceeds the current frontend and API contract.
4. **Preferred language:** no preferred-language field/path was found in these onboarding/settings models or generation prompt. Global content currently has no language cache dimension. The content constitution describes language-aware caching as future work.
5. **Version/read boundaries:** the canonical progress loader queries by user only, caps at 2,000, and collapses by node ID, despite writes being keyed by user/version/node. Multiple roadmap versions would need an explicit read boundary. This is a risk, not the demonstrated cause here.
6. **Changed onboarding/cached missions:** seeding intentionally leaves existing rows untouched; changing a declaration therefore does not revise its old seeded scores. Today's mission is invalidated for self-assessment/position changes, but not target-company, timeline, or study-hours changes, even though those influence ranking/composition. These are additional consistency risks, not established causes of the supplied screenshots.

## Issue 4: Kusuma's STAR Method win is reproducible, but over a restricted pool

Actual stored profile: position `3-5`, study time 4.5 hours, target date 2026-10-31, target companies Microsoft/Salesforce; PF10, Java10, DSA9, OS8, DBMS8, CN8, LLD6, HLD2. The replay has 52 days remaining, 270 minutes daily capacity, urgency 0.7. Company Intelligence and Learner Intelligence are enabled as in production.

### Candidate boundaries

Eligibility engine returns **119 nodes**: LLD48, HLD42, Projects9, Behavioral11, Resume9. All are recorded, with scores and inclusion flags, in the audit JSON.

PF/Java/DSA/OS/DBMS/CN are effectively completed from baseline. `virtual_completed_node_ids` marks **every** learning node in those subjects virtual, and eligibility excludes virtual nodes from new learning. That suppresses advanced DSA as well: 28 actual DSA rows are still in progress, but no DSA candidate survives. This goes beyond prerequisite satisfaction. It is existing behavior protected by the effective-completion changes, so changing its scope requires explicitly distinguishing prerequisite credit from remaining study depth.

The session pipeline then derives its own representatives, independently of the eligible-node list. LLD is `completed` for foundation/core prerequisite purposes, with unfinished capstones. `select_subjects_for_today` nominally includes completed sessions in `schedulable`, but has no ordinary selection pass for them unless revision is due. Its documented elective-enrichment pass is absent. Thus LLD's eligible work is not ranked.

The three session-plan candidates are:

| Candidate | Eligibility engine | Score | Primary loop |
|---|---|---:|---|
| `behavioral.framework.star` | Eligible | 340.505 | Selected |
| `projects.build.url_shortener` | Eligible | 279.510 | Considered |
| `hld.foundations.cap` | **Not eligible** | 230.474 | Considered |

HLD's subject gate passes using actual+effective completion, but its full node prerequisite chain does not; the session path does not intersect representatives with eligibility. Ranking does honor the three supplied scores. The problem is partly which nodes reach it.

### Scoring details

| Raw signal | STAR | Project | HLD CAP |
|---|---:|---:|---:|
| Node confidence/mastery | 0 / 0 | 0 / 0 | 2 / 20 |
| Node knowledge gap | 95 | 95 | 76 |
| Node mastery weight | 1.5 | 1.2 | 1.4 |
| Company importance sum | 8 | 6 | 7 |
| Company-intelligence signal | .4 | .4 | .6006 |
| Effective gap, company-amplified | 260 | 220 | 208 |
| Subject readiness | 1 | 1 | .8 |
| Subject transition | 0 | 0 | 0 |
| Prerequisite shortfall | 0 | 0 | 1 |
| Urgency contribution | 20.055 | 10.71 | 20.37 |
| Recency/fatigue deductions | 12 / 8 | 0 / 0 | 0 / 0 |
| Momentum raw signal | .6667 | 0 | 0 |
| Revision confidence / freshness | 0 / 0 | 0 / 0 | 0 / 0 |
| Learner-intelligence contribution | 0 | 0 | 0 |

Raw adaptive signals are multiplied by `adaptive_weights.py`; full breakdowns include difficulty/time/ROI. STAR's final score is `142.5 +156 +24 +2.4 −.45 +20.055 −12 −8 +12 +4 =340.505`.

There is **no explicit independent-track bonus**. Independent tracks avoid prerequisite penalties, have zero baseline here, and receive both node and effective knowledge-gap rewards. STAR's authored importance and mastery weight also matter. Whether the combined reward is excessive is a calibration decision; the trace does not justify penalizing Behavioral by name.

Experience is incorporated: senior-level company importance factors are applied, fatigue deducts 8 after two Behavioral missions, and composition uses experience bands. It is not absent. HLD still receives no transition bonus because that scoring helper uses only effectively completed tracks, unlike the actual+effective subject gate; LLD has effective60 but foundation/core completion credited from seeded rows. This is another input-semantic mismatch.

Answers to the eight questions: (1) STAR legitimately wins its three-candidate comparison, not a demonstrated global optimum; (2) technical work is excluded before ranking; (3) no explicit independent bonus, but asymmetrical gaps/penalties; (4) experience exists, stage constraints differ between paths; (5) baseline/evidence representation is defective; (6) technical eligibility and session-selection exclusions contribute, but admitting them alone does not prove a different winner; (7) composition preserves STAR and validation is `ok`; (8) prerequisite satisfaction, completed core breadth, and remaining advanced depth are not adequately separated in scheduling.

The highest-scoring eligibility-engine candidate in the replay is another Behavioral node, `behavioral.values.amazon_lp`, 351.91, not STAR. The ID is curriculum data, not a user-specific rule added here. Within-subject authored sequence narrows to STAR. Existing planner/ranking tests verify the winner **after session preselection**; they do not prove every eligible subject reaches ranking or that ordering cannot affect preselection. Do not “fix” this by bypassing authored within-topic progression.

## Issue 5: AI latency, cache, and UI responsiveness

Exact path: `DeepTopicPage` → `AIContentTabs/useAIContent` → Axios `roadmapService.generateContent` → `POST /api/roadmap/nodes/{id}/content/generate` → version/node lookup → `knowledge_generation.ensure_content` → Mongo global cache read → bounded roadmap prompt → `ai_service.complete(KNOWLEDGE_GENERATION)` → Gateway capability/routing/model selection → adapter → parse/normalize → cache upsert → response → hook-local React state.

The capability retains quality settings: structured output, standard reasoning, 8,192 maximum tokens, 30-second configured timeout, two Gateway retries. OpenRouter is preferred, followed by direct Gemini. The successful probe selected `google/gemini-2.5-flash` through OpenRouter. No provider routing/settings were changed.

| Measured stage | Successful probe |
|---|---:|
| First Mongo cache lookup, including cold connection | 355.00 ms |
| Second/warm Mongo lookup | 36.32 ms |
| Prompt construction, 2,356 characters | 0.024 ms |
| OpenRouter adapter, including SDK/client initialization and transport | 20,373.160 ms |
| AI façade + Gateway aggregate | 20,373.248 ms |
| Parsing/normalizing 10,460 response characters | 0.121 ms |
| Generation service with in-memory cache miss/write | 20,375.014 ms |
| Maximum event-loop scheduling lag during probe | 3,883.838 ms |
| Real Mongo write | Not performed/measured |
| HTTP/authentication/browser render | Not measured |

Mongo timings are separate probes; do not add them to the in-memory generation total as if they were one observed HTTP request. There was one successful attempt and no fallback. The adapter duration includes local initialization and transport; it is not pure model inference time. The event-loop lag shows cold initialization also needs profiling; the probe did not isolate import time from client initialization. These measurements do not establish that the reported historical ten seconds had exactly this breakdown.

Frontend generation is already asynchronous and local to the content hook. Only its generate/regenerate button is disabled; no full-page overlay or global loading transition is wired to generation. A mounted React test checks that an unrelated interaction updates while generation remains pending. A spinner alone is not evidence the page is blocked.

However, direct `GeminiAdapter.complete` calls synchronous `client.interactions.create` inside `async def`. A controlled SDK stub proves an unrelated coroutine cannot run until it returns. It also does not forward the declared temperature/token/timeout settings. This is a real same-worker backend blocking defect, relevant when Gemini is selected or OpenRouter fails over. Async OpenRouter network I/O does yield, but its lazy import/client construction can still occupy the event loop on cold use.

Other concrete findings:

- Global cache is real: key `(node_id, roadmap_version)`, no user in lookup, 11 current documents, valid PF content cache hit observed. Warm requests return without AI. No TTL was found.
- Only `_id_` index exists on the live collection; startup does not create a unique node/version index. Simultaneous misses can generate twice and may race their upserts.
- Controlled concurrent misses produce **two model calls**. A subsequent hit produces **zero**. Neither backend single-flight nor distributed coordination exists.
- Frontend `inflight` deduplicates GETs only. Generate POSTs are guarded only by each hook instance's state, not a shared per-node promise.
- `AIInterviewCards` and `AIContentTabs` have separate hook state. Updating the module-level Map does not notify the sibling hook. Their “shared state” comment overstates what is implemented.
- Hook responses check mounted status but not current node identity. Navigation within the same mounted component can let an older response overwrite another topic's local content; generating state can also remain associated with the new topic. This is a code-path finding, not a claimed browser reproduction.
- The authenticated regenerate endpoint clears the global cache without an admin/editor check, although the content constitution requires one. Flagged separately; no cache permissions were changed.

**Smallest proposed correction once this hard stop is resolved:** asynchronous provider transport inside its existing adapter, preserving Gateway settings; node-keyed generation state/shared pending requests and stale-response guards in the existing frontend data layer; backend same-process single-flight plus a reviewed unique cache index after checking duplicates. A process-local guard must be documented as such for multi-worker deployments. No evidence requires SSE, streaming infrastructure, a worker system, or a persistent job queue. No model downgrade, arbitrary short timeout, or provider bypass is justified.

## Tests, changes, and pre-existing failures

Production files intentionally unchanged: `models.py`, `routes_user.py`, `progress_engine.py`, context/planner/ranking/eligibility/stage/session/roadmap, mission routes/composition, KB routes/components/hooks, AI service/Gateway/adapters, curriculum data, and configuration. No test expectation or existing fixture was rewritten.

Added:

- `backend/scripts/audit_learner_paths.py` and `backend/scripts/audit_kb_generation.py`: repeatable diagnostic probes.
- `backend/tests/test_learner_audit_invariants.py`: four PF baseline cases guarding effective planning without persisted evidence, plus global cache hit across learners without generation or writes. **5 passed in 2.45s.**
- `frontend/src/hooks/useAIContent.audit.test.jsx`: pending generation/unrelated UI interaction invariant. **1 test / 1 suite passed, 45.794s total Jest time**; result in `test_reports/kb_ui_audit.json`. This is a mounted hook/component test, not an end-to-end browser test of every KB control.
- This report and JSON/XML audit artifacts. These additions do not constitute functional fixes.

Initial existing suite, before production changes (none were made): **155 passed, 3 failed, 8.49s**. Files: onboarding knowledge seed, canonical progress, effective prerequisite completion, effective completion verification, planner ranking integration, learning stage, eligibility, candidate generation, company-aware ranking, adaptive planning Phase4Step2, AI Gateway, AI response parsing.

Extended existing suite: **274 passed, 15 failed, 4 collection errors, 2 warnings, 12.16s**. Exact individual results are in `test_reports/learner_audit_extended.xml`. It covers learning engine, the three protected suites again, company-aware planner/context, learner intelligence, assessment integration, pacing, insights, roadmap initialization/expansion/curriculum metadata, AI consumer/security tests, node actions, mission catalog/context/CTA, and problem selection. Counts overlap the initial run; they are not a unique-test total.

| Pre-existing failure group | Classification/evidence |
|---|---|
| Seed coverage, 1 | Stale expectation: demands neutral5 independent-track rows, implementation explicitly uses zero for unrated isolated tracks |
| Candidate generation, 2 | Incomplete/stale fixtures: rows omit `node_id` and do not satisfy current subject DAG. Original pool0; adding node IDs alone yields pool1, still not >30. Revision fixture does not unlock DSA prerequisites |
| Assessment→LI, 13 | Fixture refers to removed `dsa.arrays.core`; roadmap lookup and pattern resolution return None, so assessment generation correctly refuses an unrelated replacement |
| Mission catalog tie, 1 | Test expects seeded randomness; current helper returns stable lexical ID for ties. Stale expectation relative to deterministic implementation, not changed here |
| Pacing, 1 | Both cases pass identical pacing capacity (2 hours) while varying onboarding hours. Composition consumes supplied pacing capacity, so both counts3. Fixture violates canonical capacity input; broader policy was not changed |
| Roadmap expansion, 4 collection errors | Two test files read `/app/frontend/.env` on Windows. Each error appears once per configured xdist worker; two distinct missing-path causes |

The protected effective-completion and planner/ranking tests passed. The all-candidate/ranking and baseline-to-KB tests requested for a future fix cannot truthfully be claimed as passing contracts today. This sprint stops before defining that new contract. Live integration suites that require a preview server or mutate profiles were not made green by changing environment paths or production data.

Reproduction commands (from `backend`, preserving configured xdist options):

```powershell
.\.venv\Scripts\python.exe scripts/audit_learner_paths.py --name 'Suresh Mogadala' --name 'Gowri Mogadala' --name 'Kusuma Mogadala' --output ../test_reports/learner_paths_audit.json
.\.venv\Scripts\python.exe scripts/audit_kb_generation.py --node pf.intro.core --output ../test_reports/kb_generation_audit.json
# --live adds one real Gateway generation with normal retries; its result stays in memory.
.\.venv\Scripts\python.exe -m pytest tests/test_learner_audit_invariants.py -q
```

## Dead/duplicated code audit — separate from functional findings

Nothing was deleted and no deletion is proposed in this sprint.

- `_default_goal`, `compute_goal_mastery`, and fairness constants in subject progression have no repository call/use sites beyond definitions. They are not driving current mission balance. Goal concepts exist in architecture documentation; public compatibility cannot be dismissed just from call counts.
- `WeekHeatmap` in analytics is a local, unexported null stub with no call site; the actual UI uses `WeeklyActivityWidget`. Its “imports/exports remain stable” comment does not describe an exported symbol.
- `rank_by_priority` has no direct production invocation found, but is publicly re-exported in `learning_engine.__init__`; retain for compatibility.
- `choose_focus_topic`, `rank_candidate_topics`, and `_select_unlocked_roadmap_node` are labeled legacy but have fallback production/test callers. They are not safe deletions. The fallback unlock helper treats row existence as completion, another audit risk distinct from the protected planner path.
- `roadmap_node_progress` is initialized at onboarding/startup and has repository/tests, although KB/planner use `knowledge_nodes`. Do not delete an active compatibility store just because these consumers do not read it.
- Canonical leaf normalization, API leaf normalization, session “mastery,” and dashboard fallback overlap but have differing current contracts. Resolve naming/ownership before consolidating.
- Direct KB writes still bypass the `progress_repository` module's claimed single-writer boundary. Its documentation is stronger than actual enforcement.

## Decisions required before functional implementation

1. **KB display contract:** retain evidence-based completion/mastery with a separately labeled declared baseline (recommended because existing context explicitly distinguishes planner-effective completion), or adopt a documented blended mastery projection and expose its provenance. Decide whether baseline appears only at subject level or has an approved node/module projection. Do not copy the planner's subject effective score into every node.
2. **Legacy baseline rows:** decide how historical declaration-seeded `completed` rows are represented without deleting genuine work. Source provenance is missing; a migration cannot safely assume every undated completion is fake. New baseline and evidence must be distinguishable before track enrichment changes the evidence blend.
3. **Prerequisite credit versus remaining depth:** keep the unified prerequisite-completion contract, but decide how completed-core/effectively-known subjects remain candidates for unfinished advanced study. Do not silently remove the already verified “do not restart PF/Java” behavior.
4. **Onboarding scope:** confirm the requested eleven rated subjects and preferred language become supported fields, rather than silently discarding or inferring them. This needs matching UI, DTO, persistence, and content-cache semantics.

These decisions are required by the user's explicit hard stop, not by a skill or an invented approval policy. The AI corrections described above need no new queue/infrastructure decision, but were not mixed into production while the sprint-wide stop was active.

## Manual verification for the three real profiles

Use each person's normal authenticated session. Do not resubmit onboarding, delete today's mission, or clear shared AI content just to reproduce the audit.

1. **Suresh:** inspect GET `/api/onboarding` for PF9/Java2; GET `/api/roadmap` for PF0 and rounded Java2/DBMS2/OS1. Expand PF and verify it has no fabricated completions. Inspect Java's existing actual completion before comparing a newly replayed mission. Today's stored mission is the earlier JVM introduction; current replay advances to Variables & Data Types. After an approved display change, verify the declared90 is explicitly identified and does not count as completed learning.
2. **Gowri:** inspect PF10/Java7; expand Java → Programming Basics and verify six 85% completed rows and parent85. Inspect all 11 modules: seven85/four70, track79.55→80. Verify no actual completion dates/attempts on seeded Java rows. Current replay selects Prefix Sum because two DSA nodes are already completed; stored today's mission is Traversal & In-Place Ops. After a provenance correction, confirm genuine DSA/OS evidence is retained and high PF/Java does not restart foundations.
3. **Kusuma:** inspect the actual position, target date, hours, targets, and eight stored ratings listed above. Compare stored STAR mission with the read-only script's three scored session candidates and all119 eligible nodes. Verify the HLD representative fails eligibility, LLD work is omitted, and advanced DSA is suppressed by virtual completion. After an approved candidate-boundary correction, verify technical and independent tracks reach the same deterministic comparison; do not require a technical winner merely to satisfy a screenshot expectation.
4. **AI, any profile:** use an existing cached topic and verify Generate returns without a provider call. For a genuine uncached topic in a test environment, keep the request pending and click KB navigation, notes, prerequisites, bookmarks, and another topic. Verify no whole-page lock, no old-topic response replacing the new topic, and completion state surviving navigation. Observe API timing/Gateway logs together. Test two simultaneous requests for one node and forced Gemini fallback with a controlled adapter; verify one shared generation where supported and unrelated requests continue. Do not exercise unrestricted global regeneration against real shared content.

## Next sprint recommendation

First approve the four contracts above. Then implement provenance-aware baseline projection and canonical node→track enrichment, preserving all actual events and effective prerequisite gates. Make one canonical eligible pool feed session representatives/ranking before mission composition; retain authored topic progression and define how unfinished advanced depth participates. Fix asynchronous provider transport and node-scoped pending generation independently within the existing Gateway/React architecture. Add deterministic tests for real persisted row shapes, legacy provenance, module/subject/dashboard representations, advanced technical inclusion, session candidate membership, stale-response navigation, same-key generation concurrency, and Gateway boundaries. Repair stale fixtures separately with their provenance documented. Defer weight tuning until learner-state and candidate-pool correctness are measured.
