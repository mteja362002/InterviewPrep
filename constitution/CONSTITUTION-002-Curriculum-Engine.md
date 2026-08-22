# CONSTITUTION-002 — Curriculum Engine

**Version:** 1.0  
**Status:** Active  
**Scope:** `backend/problem_bank.py`, `backend/roadmap.py`, `backend/data/roadmap_v1.json`, `backend/services/mission_context.py`, `backend/services/problem_selection/`  
**Authority:** Chief Software Architect  

---

## Purpose

The Curriculum Engine is the authoritative owner of PrepOS's learning content. It defines what exists to be learned, how problems are organized, and what constitutes a canonical learning objective. Every other subsystem consumes curriculum — none may produce or redefine it.

The Curriculum Engine is a **static content system with a deterministic retrieval layer**. It has no runtime mutation path. It does not call external services. It does not modify learner state. It reads and serves.

---

## Responsibilities

### Curriculum Engine Owns

- The roadmap knowledge graph (`roadmap_v1.json` + `roadmap.py`)
- The curated problem catalog (`problem_bank.py`)
- The `representative` designation of each problem
- The `MissionContext` dataclass and its builder
- The problem selection pipeline (`services/problem_selection/selector.py`)
- The canonical mapping of patterns to domains (`PATTERN_TO_DOMAIN`)
- The prerequisite dependency map (`PATTERN_PREREQUISITES`)
- The company registry (`COMPANIES` dict in `problem_bank.py`)
- The `SUBTOPIC_TO_PATTERN` mapping

### Curriculum Engine Does NOT Own

- Learner progress or mastery state
- Which problem a specific learner should see next (that is Problem Selection's job, consuming the curriculum)
- Assessment evaluation or scoring
- AI-generated content (that is the Content Architecture's domain)
- Company importance scores (authored by Company Intelligence, read by Curriculum)

---

## Scope

This constitution governs:

1. **Roadmap Engine** — `roadmap.py` + `data/roadmap_v1.json`
2. **Problem Bank** — `problem_bank.py`
3. **Problem Selector** — `services/problem_selection/selector.py`
4. **Mission Context** — `services/mission_context.py`

It does NOT govern mission generation logic, assessment generation, or AI content production.

---

## Architectural Principles

### CP-001 — Curriculum is Static at Runtime

The roadmap and problem bank MUST be loaded once at process startup and treated as immutable for the process lifetime. No runtime code may modify `PROBLEMS`, `roadmap_v1.json`, or any curriculum data structure. Changes require a deployment.

### CP-002 — No Cross-Contamination of Patterns

A problem MUST belong to exactly one `primary_pattern`. The `pattern` field on a problem MUST equal `primary_pattern`. `tags` may include related patterns for search, but selection MUST use only `primary_pattern`. A selector MUST NOT return problems from Pattern A when asked for Pattern B.

### CP-003 — No Cross-Contamination of Learning Stages

A `representative_pool(pattern, learning_stage)` call MUST return problems scoped to exactly that stage. It MUST NOT return problems from adjacent stages. Empty pool → return empty. NEVER substitute a different stage.

### CP-004 — MissionContext is the Curriculum-to-Learner Interface

All downstream consumers receive curriculum knowledge through `MissionContext`. No consumer may read `roadmap_v1.json`, `PROBLEMS`, or call `representative_pool()` directly — they consume `MissionContext` fields. The only exceptions are the Mission Engine (builds MissionContext) and the Assessment Generator (reads problem bank directly for question generation).

### CP-005 — Representative Problems are Editorially Curated

The `representative: True` flag is a **human editorial decision**. It MUST NOT be assigned algorithmically. It represents: "This problem is the canonical example for this pattern and stage in PrepOS." It is used across Mission Arena, Assessment, AI Mentor, and Revision.

### CP-006 — Problem IDs are Immutable and Permanent

Once a problem is assigned an `id` (e.g., `lc-3`), that ID MUST NEVER change. It is referenced in `assessments`, `problem_assignments`, `problem_feedback`, and all historical records. Changing an ID is a breaking data corruption event.

### CP-007 — Roadmap Node IDs are Immutable

Once published in `roadmap_v1.json`, a node's `id` MUST NEVER change. It is a permanent key in `knowledge_nodes`. A new roadmap version introduces new IDs; it does not rename existing ones.

### CP-008 — Pattern Inheritance via Ancestor Walk

Patterns are authored once per topic-level node in the roadmap. Leaf nodes inherit pattern by walking up their ancestor chain. This is the only valid pattern resolution mechanism. No module may hardcode a node_id → pattern mapping outside of `roadmap.py::pattern_for_node()`.

---

## Design Philosophy

The Curriculum Engine exists because PrepOS needs a **curated, stable, human-verified foundation** that all adaptive algorithms can trust. Adaptive systems that operate on uncurated or dynamically generated curriculum produce incoherent learning paths.

By making the curriculum a static file system (JSON + Python dict), PrepOS achieves:

1. **Editorial control** — curriculum designers control what is taught and in what order
2. **Testability** — the curriculum can be tested in isolation from all learner state
3. **Determinism** — the selection pipeline always produces the same output for the same inputs
4. **Auditability** — every representative problem assignment is a deliberate editorial choice visible in version control

The roadmap is a **directed acyclic graph** (DAG), not a linear sequence. This allows learners on different tracks to progress in parallel while the prerequisite system ensures logical sequencing within each track.

---

## Roadmap Structure

### Node Hierarchy

```
Track (11 total: dsa, java, lld, hld, os, dbms, cn,
       projects, behavioral, resume, programming_fundamentals)
  └── Module
        └── Topic  ← pattern is authored HERE
              └── Subtopic
                    └── LearningNode (leaf)
                          ├── activity_type: study|coding|quiz|behavioral|design|system_design|flashcards
                          ├── assessment_type: mirrors activity_type
                          ├── learning_stage: foundation|core|advanced  [intermediate = tech debt]
                          ├── problem_ids: [...] (explicit problem bank references)
                          ├── prerequisites: [...] (other node IDs)
                          ├── difficulty: easy|medium|hard
                          └── company_importance: {company_id: 0-5}
```

### Learning Stage Canonical Values

| Stage | Meaning |
|-------|---------|
| `foundation` | Entry-level; beginner-accessible; essential for all learners |
| `core` | Standard proficiency; required for all target companies |
| `advanced` | Expert level; FAANG-tier difficulty; senior+ interview focus |

> **KNOWN TECHNICAL DEBT:** The `intermediate` stage appears on Trees/Graphs/Heap roadmap nodes but does not exist in the problem bank's `LEARNING_STAGES` enum. It MUST be resolved in a future sprint by either renaming nodes to `core` or adding `intermediate` to the bank's schema. See CONSTITUTION-010.

---

## Problem Bank Schema

Every problem in `PROBLEMS` MUST conform to this schema:

```python
{
    "id": str,                    # REQUIRED. Stable slug, format: "lc-<N>". IMMUTABLE.
    "leetcode_id": int,           # REQUIRED. Numeric LeetCode problem number.
    "title": str,                 # REQUIRED. Official problem title.
    "difficulty": str,            # REQUIRED. One of: "easy" | "medium" | "hard"
    "learning_stage": str,        # REQUIRED. One of: "foundation" | "core" | "advanced"
    "pattern": str,               # REQUIRED. Must equal primary_pattern.
    "primary_pattern": str,       # REQUIRED. The one canonical pattern for selection.
    "estimated_minutes": int,     # REQUIRED. Expected solve time in minutes.
    "leetcode_url": str,          # REQUIRED. Full URL to the LeetCode problem page.
    "tags": [str],                # OPTIONAL. Related patterns/topics for search.
    "prerequisite_patterns": [str], # OPTIONAL. Patterns required before this problem.
    "frequency": str,             # REQUIRED. One of: "low" | "medium" | "high" | "very_high"
    "companies": [str],           # REQUIRED. Keys from the COMPANIES registry.
    "source_lists": [str],        # OPTIONAL. blind75 | leetcode150 | neetcode150 | striver
    "representative": bool        # REQUIRED. True = canonical for pattern+stage in PrepOS.
}
```

### Representative Problem Rules

A problem SHOULD be designated `representative: True` when:

1. It is the canonical exemplar of its pattern and learning stage
2. It appears in at least two major source lists (Blind75, NeetCode150, LeetCode150, Striver)
3. It has `frequency` of `high` or `very_high`
4. It has a clear, unambiguous problem statement suitable for timed assessment
5. Its solution demonstrates the pattern with minimal noise from other patterns

A problem MUST NOT be designated `representative: True` when:

- It requires knowledge of a different pattern as a prerequisite (without that prerequisite being in `prerequisite_patterns`)
- It is a specialty variant (contest-only, extremely long problem statement)
- It is a duplicate of an already-representative problem in the same pattern+stage

---

## Problem Selection Pipeline

### `representative_pool(pattern, learning_stage)`

Returns a sorted list of all problems where:
- `primary_pattern == pattern` AND
- `learning_stage == learning_stage` AND
- `representative == True`

Sorted by: `_rank_key` = (representative DESC, frequency DESC, leetcode_id ASC)

**Guarantees:**
- NEVER mixes patterns
- NEVER mixes learning stages
- Returns `[]` on empty pool (never substitutes)
- Deterministic for the same inputs

### `split_arena_assessment(pattern, learning_stage, arena_count, assessment_count)`

Returns two DISJOINT lists: `(arena_problems, assessment_problems)`.

**Guarantee:** A problem appearing in `arena_problems` MUST NOT appear in `assessment_problems`. This is an invariant. It is NEVER relaxed, even when the pool is small.

### `select_representative(count, pattern, learning_stage, exclude_ids, target_companies)`

Returns up to `count` representative problems from the pool, excluding `exclude_ids`. Applies a soft company preference reorder (not a hard filter).

---

## MissionContext Contract

`MissionContext` is a pure dataclass (no I/O, no DB). It is built by `build_mission_context(node_id, ...)` and passed to all consuming subsystems.

### Invariants

- MUST NOT be built by any module other than `services/mission_context.py`
- MUST NOT be cached across missions (built fresh per generation)
- `representative_problem_ids` MUST come from `representative_pool()` only
- `coding_pattern` MUST come from `roadmap.pattern_for_node()` only
- `activity_type` and `assessment_type` MUST be read from the roadmap node; never re-derived

### Fields (canonical)

| Field | Source | Notes |
|-------|--------|-------|
| `node_id` | Planner recommendation | The roadmap node being studied |
| `activity_type` | `node["activity_type"]` | Determines CTA routing |
| `assessment_type` | `node["assessment_type"]` | Drives Assessment Engine |
| `coding_pattern` | `roadmap.pattern_for_node()` | Used by problem selection |
| `learning_stage` | `node["learning_stage"]` | Stage-scoped selection |
| `representative_problem_ids` | `representative_pool()` | IDs only, no full problem objects |
| `prerequisites` | `node["prerequisites"]` | Used by Mission Engine for revision tasks |

---

## Sprint 2 Principles

Sprint 2 expands problem coverage in `problem_bank.py`. The following rules MUST be followed:

1. **No architectural changes.** Only `problem_bank.py` is modified.
2. **No schema changes.** Every new problem MUST conform to the existing schema.
3. **No selector changes.** The selection pipeline is frozen.
4. **No roadmap changes.** The `problem_ids` linkage in `roadmap_v1.json` is not modified.
5. **Correct `learning_stage`.** New problems MUST use `foundation`, `core`, or `advanced`. Do NOT use `intermediate`.
6. **Correct `representative` flag.** Only editorially curated canonical problems receive `representative: True`.
7. **Module-by-module delivery.** One module per PR. Do NOT batch multiple modules.
8. **ID format.** All IDs follow `lc-<leetcode_number>` format without exception.

---

## Data Ownership

| Asset | Owner | Consumers |
|-------|-------|----------|
| `problem_bank.py` | Curriculum Engine | Problem Selector, Mission Engine, Assessment Generator, AI Mentor |
| `data/roadmap_v1.json` | Curriculum Engine | Roadmap Engine (`roadmap.py`) |
| `roadmap.py` (runtime graph) | Curriculum Engine | Mission Engine, Learning Engine, Progress Engine, AI Mentor |
| `services/mission_context.py` | Curriculum Engine | Mission Engine, Coding Arena API, Assessment API, AI Mentor |
| `services/problem_selection/` | Curriculum Engine | Mission Engine, Assessment Engine, routes_missions |

---

## Allowed Dependencies

The Curriculum Engine modules MAY depend on:

- Standard Python library
- Each other (within the Curriculum Engine vertical slice)
- No external service or MongoDB

### `roadmap.py`
- `data/roadmap_v1.json` (static load)
- Standard Python only

### `problem_bank.py`
- Standard Python only

### `services/problem_selection/selector.py`
- `problem_bank.py`

### `services/mission_context.py`
- `roadmap.py`
- `problem_bank.py`
- `services/problem_selection/`

---

## Forbidden Dependencies

The Curriculum Engine MUST NOT depend on:

❌ MongoDB or any database  
❌ `ai_service.py` or any LLM  
❌ `mission_engine.py`  
❌ `assessment/`  
❌ `services/learner_intelligence/`  
❌ `services/learning_engine/`  
❌ Any FastAPI router  
❌ Any frontend module  

---

## Extension Points

### New Roadmap Track

1. Add the track JSON object to `data/roadmap_v1.json`
2. Add track ID to `models.py::TOPIC_KEYS` if it requires progress tracking
3. Add track to `mission_engine.py::DEFAULT_READINESS` and `COMPANY_READINESS_WEIGHTS`
4. No changes to `roadmap.py` required

### New Pattern

1. Add to `PATTERN_TO_DOMAIN` in `problem_bank.py`
2. Add to `PATTERN_PREREQUISITES` if applicable
3. Add to `SUBTOPIC_TO_PATTERN` for display mapping
4. Add representative problems with the new pattern
5. No changes to selectors or engines required

### New Problem

1. Add dict to `PROBLEMS` list in `problem_bank.py`
2. Follow the schema exactly
3. Set `representative: True` only if editorially curated
4. Optionally add `id` to `roadmap_v1.json::problem_ids` for the relevant node

### New Source List

Add the source list key to `source_lists` field of relevant problems. No structural changes needed.

---

## Invariants

1. `PROBLEMS` list is append-only. No problem is ever removed (it may be marked deprecated via a new field).
2. Every problem's `id` is globally unique across the entire `PROBLEMS` list.
3. Every problem's `leetcode_id` is unique.
4. `pattern` always equals `primary_pattern` in every problem dict.
5. `representative_pool()` result is always a subset of the full `PROBLEMS` list for that pattern+stage.
6. `build_mission_context()` never returns a `MissionContext` with problems from a different pattern than the node's `coding_pattern`.

---

## Anti-patterns

❌ Storing problem metadata in MongoDB  
❌ Generating problem metadata via AI at runtime  
❌ Having two `representative: True` problems for the same pattern+stage at the same difficulty if the pool is already large enough  
❌ Using `tags` for primary selection (tags are search helpers, not selection criteria)  
❌ Adding `intermediate` as a new `learning_stage` in the bank without resolving existing roadmap nodes  
❌ Hardcoding node_id → pattern mappings anywhere outside `roadmap.py::pattern_for_node()`  
❌ Calling `representative_pool()` with a mixed or fabricated learning_stage  
❌ Building `MissionContext` inside a route handler  
❌ Returning full problem objects from `MissionContext` (it returns IDs only)  

---

## Future Evolution

- **Versioned problem bank:** Add a `roadmap_version` constraint to problems to allow different roadmap versions to reference different problem sets without modifying existing entries.
- **New learning stages:** If `intermediate` is formally adopted, update both `roadmap_v1.json` nodes and the bank schema together, not independently.
- **Problem difficulty calibration:** Add community-sourced difficulty feedback as a separate `community_difficulty` field. MUST NOT replace the curated `difficulty` field.
- **Multi-language support:** Add `language` metadata to problems for Java/Python/Go variants. The selection pipeline adds a language filter parameter. No structural change to the bank schema.
- **Curriculum versioning:** Future `roadmap_v2.json` introduces new tracks/nodes with new IDs. It MUST NOT rename or delete v1 node IDs. The `roadmap_version` field on each user determines which graph they use.
