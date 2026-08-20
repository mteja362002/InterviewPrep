# Mission Experience — Frontend Integration (Phase 3D)

This document describes how the PrepOS frontend consumes the frozen backend
architecture. It is the reference for how the learning pages stay synchronized.
The golden rule: **React is a presentation layer. It never decides what the
learner studies, never infers activity types, never filters problems, and
never generates explanations.** Everything comes from the backend's canonical
Mission Context.

---

## 1. Mission Context flow

```
Roadmap → Learning Node → Mission Planner → MissionContext (backend, frozen)
                                              │
                        GET /api/missions/today/context  (read-only projection)
                                              │
                                   MissionContextProvider  (fetch ONCE, shared)
                                              │
     ┌────────────┬───────────────┬──────────────┬───────────────┬────────────┐
     ▼            ▼               ▼              ▼               ▼            ▼
 MissionControl  KnowledgeBase  CodingArena   Assessment      AIMentor    Analytics
```

- **Backend endpoint:** `GET /api/missions/today/context` (`routes_missions.py`).
  A pure projection of `services.mission_context.build_mission_context` for each
  of today's tasks, plus the canonical `activity_type → cta` map
  (`cta_for_activity`). It performs no planner logic, scoring, filtering,
  ranking or inference.
- **Provider:** `src/contexts/MissionContextProvider.jsx` fetches that endpoint
  exactly once per session (React Query, `staleTime` 5 min, key
  `qk.missionContext(userId)`), and shares it via `useMissionContext()`.
  Mounted in `App.js` around all routes.

`useMissionContext()` exposes:
`missionId, date, status, title, focusArea, estimatedDurationMinutes,
recommendationInsight, aiNarrative, tasks, executionState, isLoading, refetch,
refresh(), getTaskContext({taskId,nodeId}), getContextByNodeId(nodeId),
isTodaysNode(nodeId)`.

Each task carries: `task_id, title, kind, topic, node_id, completed, status,
is_revision, activity_type, cta, mission_context`. `mission_context` is the full
frozen object (topic, activity_type, assessment_type, subject, domain,
subdomain, difficulty, learning_stage, estimated_time, coding_pattern,
knowledge_base_node, representative_problem_ids, prerequisites, related_topics,
learning_objectives, target_companies, revision_context).

---

## 2. Page responsibilities

| Page | Reads from Mission Context | Never does |
| --- | --- | --- |
| **Mission Control** | per-task `cta` (the button), status | infer activity/topic |
| **Knowledge Base** (DeepTopicPage) | today's node banner, objectives | search for the topic |
| **Coding Arena** | today's representative problems (backend-selected), banner, empty state | pick/filter problems in React |
| **Assessment** | pre-start banner + objectives, empty state | choose topic/questions |
| **AI Mentor** | passes `topic_node_id`; backend assembles context | re-assemble context |
| **Analytics** | today's mission banner | recompute mission metrics |

---

## 3. CTA rendering rules (Mission Control)

The primary button per task comes **entirely** from `taskCtx.cta` — a static
backend map. Exactly one primary CTA renders (never both KB and Arena):

| activity_type | cta.action | Button |
| --- | --- | --- |
| study | open_knowledge_base | Open Knowledge Base |
| coding | open_coding_arena | Open Coding Arena |
| quiz / behavioral / design / system_design | start_assessment | Start Assessment |
| flashcards | open_flashcards | Open Flashcards |

If a coding task has an empty `representative_problem_ids`, the Arena CTA is
shown disabled ("No problems available") — no unrelated fallback.

---

## 4. Coding Arena integration

- Loads today's problems from `/missions/coding-arena` (already backed by the
  canonical Problem Selector on the server). React does **no** selection.
- Shows `TodaysMissionBanner` and an explicit empty state
  ("No representative problems available for this learning node.").
- **Practice More** remains fully independent: it uses `dev_seed.json` via the
  LeetCode Catalog and never touches Mission / Assessment / Learner
  Intelligence / representative problems.
- Arena and Assessment never present identical representative problems — the
  server splits the representative pool into disjoint subsets
  (`split_arena_assessment`).

---

## 5. Assessment integration

- Consumes the Mission Context for the pre-start panel (Topic, Assessment Type,
  Difficulty, Estimated Time, Learning Objectives, Target Companies).
- If generation fails, shows the explicit empty state
  ("Assessment is currently unavailable for this topic.") instead of bouncing.
- Assessment type is driven by `assessment_type` from the backend, never
  inferred in React.

---

## 6. Knowledge Base integration

- "Open Knowledge Base" navigates directly to
  `/app/knowledge-base/nodes/:nodeId` (today's roadmap node) — no manual search.
- When the open node is today's mission node (`isTodaysNode`), a
  `TodaysMissionBanner` is shown with topic, stage, difficulty, time, companies.

---

## 7. Explainability flow ("Why this mission?")

- Reuses the existing `components/mission/WhyThisMissionDialog.jsx`.
- Renders **only** backend `recommendation_insight` (weakness, mastery,
  confidence, revision/pacing, company relevance, prerequisite highlights,
  estimated readiness delta). React never generates explanation text.

---

## 8. Progress synchronization (§10)

- The provider derives `MissionExecutionState`
  (`status, progressPct, completedCount, totalCount, kbCompleted,
  arenaCompleted, assessmentCompleted, lastUpdated`) from the shared context.
- `refresh()` invalidates both `qk.missionContext` and `qk.missionToday`.
- Completing work calls `refresh()` so Mission Control updates without a manual
  reload and without duplicate fetches:
  - Knowledge Base: on "Mark completed" (`setStatusM` onSuccess).
  - Coding Arena: on feedback submit (`onSubmitted`).
  - Assessment: after `completeMission` on evaluate.
  - Mission Control: on task toggle / complete mission.
- Status transitions: Not Started → In Progress → Completed.

---

## 9. Performance

- Mission Context is fetched once and shared via React Query cache + the
  provider. No page calls the context endpoint independently.

---

## 10. Why React contains no learning logic

The backend is the single source of truth (roadmap = curriculum,
`problem_bank` = representative problems, canonical selector = problem choice,
planner = what to study, Mission Context = today's objective). The frontend
only *renders* projections of that state and *routes* between pages. This keeps
every page synchronized, makes new subjects/activities work with zero frontend
changes, and prevents drift between pages. See `docs/adr/ADR-001-foundation-freeze.md`.
