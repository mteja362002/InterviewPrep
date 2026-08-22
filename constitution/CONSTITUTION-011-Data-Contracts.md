# CONSTITUTION-011 — Data Contracts

**Version:** 1.0  
**Status:** Active  
**Scope:** MongoDB collections, Pydantic models, API DTOs, assessment evidence schema, learner snapshot schema, versioning rules  
**Authority:** Chief Software Architect  

---

## Purpose

This constitution defines the authoritative data contracts for PrepOS — the canonical shapes of all persistent data, API payloads, inter-service objects, and versioning rules. Every module that reads or writes data MUST conform to the contracts defined here. The contracts are the stable interface between PrepOS subsystems.

A contract violation (writing data in an unexpected shape, or reading a field that doesn't exist) is a bug, not a feature. Contracts change only through the Architecture Review process.

---

## Responsibilities

### Data Contracts Owns

- MongoDB collection schemas (all 19 collections)
- MongoDB index definitions
- Pydantic model definitions (`models.py`, `assessment/schemas.py`)
- API request/response DTOs
- Inter-service data objects (`MissionContext`, `LearnerIntelligenceSnapshot`, `AssessmentEvidence`)
- Schema versioning rules
- Migration contract

### Data Contracts Does NOT Own

- Data generation logic (owned by the producing subsystem)
- Data consumption logic (owned by the consuming subsystem)
- Data validation beyond schema (business rule validation belongs in the service layer)

---

## Architectural Principles

### DC-001 — Single Authoritative Schema

Every field's type, nullability, and default value MUST be defined in exactly one place. No module may assume a schema that is not documented here. No field is optional in practice if it is required in the schema.

### DC-002 — Additive Changes are Non-Breaking

Adding a new optional field to any schema is non-breaking. Removing, renaming, or changing the type of any field is breaking and requires a migration + version bump.

### DC-003 — Schema Versions are per-Collection

Where a collection's schema has broken backward compatibility, a `schema_version` field tracks which version a document was written with. Consumers MUST check `schema_version` if they read version-sensitive fields.

### DC-004 — Immutable IDs

All document `id` fields are UUIDs, assigned at creation, and NEVER changed. Problem IDs (`lc-N`) are permanent. Roadmap node IDs are permanent.

### DC-005 — UTC Timestamps

All timestamps MUST be stored as ISO 8601 strings in UTC. No timezone information beyond UTC. No UNIX epoch integers. Format: `YYYY-MM-DDTHH:MM:SS.mmmZ`.

---

## MongoDB Collections

### Collection Index Map

| Collection | Primary Index | Secondary Indexes |
|-----------|--------------|------------------|
| `users` | `_id` | `email` (unique) |
| `onboarding` | `_id` | `user_id` (unique) |
| `settings` | `_id` | `user_id` (unique) |
| `login_attempts` | `_id` | `identifier` |
| `password_reset_tokens` | `_id` | TTL on `expires_at` |
| `daily_missions` | `_id` | `(user_id, date)` (unique), `(user_id, date DESC)` |
| `knowledge_progress` | `_id` | `(user_id, topic)` (unique) |
| `knowledge_nodes` | `_id` | `(user_id, roadmap_version, node_id)` (unique) |
| `study_streaks` | `_id` | `user_id` (unique) |
| `revisions` | `_id` | `(user_id, next_review_date)` ← LEGACY |
| `activity_events` | `_id` | `(user_id, ts DESC)`, `(user_id, event_type)` |
| `problem_assignments` | `_id` | `(user_id, mission_id)`, `(user_id, pattern)` |
| `problem_feedback` | `_id` | `(user_id, submitted_at DESC)`, `(user_id, pattern)` |
| `mission_adjustments` | `_id` | `(user_id, for_date DESC)` |
| `weaknesses` | `_id` | `(user_id, pattern)` (unique) |
| `assessments` | `_id` | Managed by `assessment_history.ensure_indexes()` |
| `knowledge_content` | `_id` | `(node_id, roadmap_version)` (unique) |
| `mentor_conversations` | `_id` | `(user_id, updated_at DESC)`, `id` (unique) |
| `mentor_messages` | `_id` | `(conversation_id, created_at ASC)`, `(user_id, created_at DESC)` |

---

## Core Document Schemas

### `users`

```json
{
    "_id": "ObjectId",
    "id": "uuid-string",
    "email": "string (unique)",
    "name": "string",
    "role": "user | admin | editor",
    "avatar_url": "string | null",
    "is_email_verified": "boolean",
    "onboarding_completed": "boolean",
    "roadmap_version": "string (e.g. 'v1')",
    "hashed_password": "string",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

### `onboarding`

```json
{
    "_id": "ObjectId",
    "user_id": "uuid-string",
    "target_companies": ["string"],
    "position": "student | 0-1 | 1-3 | 3-5 | 5+",
    "daily_study_hours": "float",
    "target_date": "ISO date string | null",
    "start_date": "ISO date string",
    "self_assessment": {
        "dsa": "int (0-10)",
        "java": "int (0-10)",
        "lld": "int (0-10)",
        "hld": "int (0-10)",
        "os": "int (0-10)",
        "dbms": "int (0-10)",
        "cn": "int (0-10)",
        "programming_fundamentals": "int (0-10)"
    },
    "goals": ["string"],
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

### `knowledge_nodes`

The primary progress store. One document per `(user_id, roadmap_version, node_id)`.

```json
{
    "_id": "ObjectId",
    "user_id": "uuid-string",
    "roadmap_version": "string",
    "node_id": "string",
    "status": "not_started | in_progress | completed | mastered | revision_due | skipped",
    "confidence": "float (0-10)",
    "mastery_percentage": "float (0-100)",
    "weakness_score": "float (0-100)",
    "attempts": "int",
    "time_spent_minutes": "int",
    "revision_stage": "int (0-5)",
    "next_revision": "ISO date string | null",
    "last_reviewed": "ISO timestamp | null",
    "completed_at": "ISO timestamp | null",
    "notes": "string | null",
    "bookmarked": "boolean",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

### `daily_missions`

```json
{
    "_id": "ObjectId",
    "id": "uuid-string",
    "user_id": "uuid-string",
    "date": "YYYY-MM-DD",
    "title": "string",
    "focus_area": "string",
    "focus_topic": "string (one of TOPIC_KEYS)",
    "difficulty": "easy | medium | hard",
    "estimated_duration_minutes": "int",
    "learning_objective": "string",
    "tasks": ["MissionTask (see below)"],
    "revision_task_ids": ["string"],
    "status": "in_progress | completed | skipped",
    "assessment_id": "uuid-string | null",
    "assessment_available": "boolean",
    "workflow_state": "string | null",
    "recommendation_insight": "dict | null",
    "ai_narrative": "string | null",
    "tomorrow_preview": "dict | null",
    "week_goal": "dict | null",
    "roadmap_version": "string",
    "created_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

### `MissionTask` (embedded in `daily_missions.tasks`)

```json
{
    "id": "uuid-string",
    "title": "string",
    "kind": "practice | study | revise",
    "topic": "string (one of TOPIC_KEYS)",
    "completed": "boolean",
    "pattern": "string | null",
    "problem_count": "int | null",
    "node_id": "string | null",
    "order": "int"
}
```

### `assessments`

```json
{
    "_id": "ObjectId",
    "id": "uuid-string",
    "user_id": "uuid-string",
    "assessment_type": "coding | theory | mcq | debugging | behavioral | system_design | resume | project_explanation",
    "status": "pending | started | submitted | evaluated | completed",
    "schema_version": "string (e.g. '1.0')",
    "roadmap_node_id": "string | null",
    "mission_id": "string | null",
    "target_company": "string | null",
    "difficulty": "easy | medium | hard",
    "question": "Question (see below)",
    "rubric": "Rubric (see below)",
    "attempt": "Attempt | null",
    "result": "Result | null",
    "feedback": "Feedback | null",
    "evidence": "AssessmentEvidence | null",
    "recommendation": "AssessmentRecommendation | null",
    "created_at": "ISO timestamp",
    "started_at": "ISO timestamp | null",
    "submitted_at": "ISO timestamp | null",
    "evaluated_at": "ISO timestamp | null",
    "completed_at": "ISO timestamp | null"
}
```

### `AssessmentEvidence` (embedded in `assessments.evidence`)

```json
{
    "schema_version": "string",
    "assessment_id": "uuid-string",
    "user_id": "uuid-string",
    "assessment_type": "string",
    "roadmap_node_id": "string | null",
    "mission_id": "string | null",
    "accuracy": "float (0-1)",
    "proficiency": "float (0-1)",
    "completion_quality": "float (0-1)",
    "confidence_delta": "float (-1 to 1)",
    "difficulty_achieved": "easy | medium | hard | null",
    "weakness_confirmation": "boolean",
    "revision_trigger": "boolean",
    "repeated_mistakes": "boolean",
    "metrics": {"key": "float"},
    "signals": {"key": "boolean"},
    "tags": ["string"],
    "created_at": "ISO timestamp"
}
```

### `knowledge_content`

```json
{
    "_id": "ObjectId",
    "id": "uuid-string",
    "node_id": "string",
    "roadmap_version": "string",
    "provider": "string",
    "model_name": "string",
    "theory": "dict",
    "examples": ["dict"],
    "interview_tips": ["string"],
    "common_mistakes": ["dict"],
    "flashcards": ["dict"],
    "related_topics": ["dict"],
    "prerequisites": ["dict"],
    "generated_by": "uuid-string",
    "generated_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

### `problem_feedback`

```json
{
    "_id": "ObjectId",
    "id": "uuid-string",
    "user_id": "uuid-string",
    "problem_id": "string (lc-N)",
    "mission_id": "string | null",
    "pattern": "string",
    "difficulty": "easy | medium | hard",
    "confidence": "int (1-10)",
    "solved": "boolean",
    "time_taken_minutes": "int | null",
    "hints_used": "boolean",
    "notes": "string | null",
    "submitted_at": "ISO timestamp"
}
```

---

## Inter-Service Data Contracts

### `MissionContext` (Python dataclass — in-memory, never persisted)

```python
MissionContext {
    node_id: str                        # roadmap node being studied
    topic: Optional[str]                # human label
    activity_type: Optional[str]        # study|coding|quiz|behavioral|design|system_design|flashcards
    assessment_type: Optional[str]      # mirrors activity_type
    subject: Optional[str]              # track id
    domain: Optional[str]               # domain label
    subdomain: Optional[str]            # module id
    difficulty: Optional[str]           # easy|medium|hard
    learning_stage: Optional[str]       # foundation|core|advanced
    estimated_time: Optional[int]       # minutes
    coding_pattern: Optional[str]       # pattern slug
    knowledge_base_node: Optional[str]  # = node_id
    representative_problem_ids: List[str]  # IDs only
    prerequisites: List[str]            # prerequisite node IDs
    related_topics: List[str]
    learning_objectives: List[str]
    target_companies: List[str]
    revision_context: Optional[Dict]
    mission_id: Optional[str]
}
```

### `LearnerIntelligenceSnapshot` (in-memory, not persisted)

```python
LearnerIntelligenceSnapshot {
    velocity: VelocitySignal {label: str, score: float}
    retention: RetentionSignal {label: str, score: float}
    confidence_trend: ConfidenceTrendSignal {label: str, score: float}
    consistency: ConsistencySignal {label: str, score: float}
    revision_health: RevisionHealthSignal {label: str, score: float}
    weakness_stability: WeaknessStabilitySignal {label: str, score: float}
    mastery_trends: dict[str, MasteryTrendSignal]
    coding_growth: CodingGrowthSignal {label: str, score: float}
    difficulty_adaptation: DifficultyAdaptationSignal {label: str, score: float}
    readiness_trend: ReadinessTrendSignal {label: str, score: float}
    empty: bool
}
```

---

## API DTO Contracts

### Mission API

#### `GET /api/mission/today` → `DailyMission`

Response type: `DailyMission` document (see above).

#### `POST /api/arena/problem/feedback`

```json
{
    "problem_id": "string",
    "mission_id": "string | null",
    "confidence": "int (1-10)",
    "solved": "boolean",
    "time_taken_minutes": "int | null",
    "hints_used": "boolean",
    "notes": "string | null"
}
```

#### `GET /api/arena/problem`

```json
{
    "problem": {
        "id": "string",
        "leetcode_id": "int",
        "title": "string",
        "difficulty": "string",
        "estimated_minutes": "int",
        "leetcode_url": "string",
        "pattern": "string",
        "frequency": "string",
        "companies": ["string"],
        "source_lists": ["string"]
    },
    "mission_context": "MissionContext.to_dict()"
}
```

### Roadmap API

#### `GET /api/roadmap/node/{id}/content`

Response: `knowledge_content` document (see above).

### Assessment API

#### `POST /api/assessment`

Request:
```json
{
    "assessment_type": "string",
    "roadmap_node_id": "string | null",
    "mission_id": "string | null",
    "target_company": "string | null",
    "difficulty": "string | null"
}
```

#### `POST /api/assessment/{id}/submit`

Request:
```json
{
    "passed_tests": "int",
    "total_tests": "int",
    "edge_cases_passed": "int",
    "edge_cases_total": "int",
    "claimed_time_complexity": "string | null",
    "time_taken_seconds": "int | null",
    "explanation": "string | null",
    "code": "string | null",
    "solved": "boolean | null"
}
```

---

## Schema Versioning Rules

| Change Type | Version Impact | Migration Required |
|------------|---------------|-------------------|
| Add optional field | Non-breaking — no version bump | No |
| Add required field with default | Non-breaking if default is sensible | No |
| Remove field | Breaking — bump `schema_version` | Yes |
| Rename field | Breaking — bump `schema_version` | Yes |
| Change field type | Breaking — bump `schema_version` | Yes |
| Add enum value | Non-breaking | No |
| Remove enum value | Breaking — bump `schema_version` | Yes |

### Migration Protocol

1. Add new field (optional, with default) in deployment N
2. Write migration script that backfills existing documents
3. Run migration in deployment N+1
4. Mark old field as deprecated (add `deprecated_at` field)
5. Remove old field in deployment N+2 (after verifying no reads from old field)

---

## Invariants

1. All document `id` fields are UUIDs generated at creation and NEVER changed.
2. All timestamps are UTC ISO 8601 strings.
3. `(user_id, roadmap_version, node_id)` uniquely identifies a `knowledge_nodes` document.
4. `(user_id, date)` uniquely identifies a `daily_missions` document.
5. `(node_id, roadmap_version)` uniquely identifies a `knowledge_content` document.
6. `AssessmentEvidence.schema_version` is set at creation time and NEVER changed.
7. `problem_feedback.problem_id` MUST reference a valid ID in `problem_bank.PROBLEMS`.

---

## Anti-patterns

❌ Storing derived data (readiness scores, progress rollups) in MongoDB — compute at runtime  
❌ Storing full problem text in `knowledge_content` or `assessments`  
❌ Using sequential integer IDs for user-facing documents  
❌ Storing UNIX epoch integers for timestamps (use ISO 8601 strings)  
❌ Using Python `dict` type annotations where a Pydantic model is possible  
❌ Querying MongoDB by non-indexed fields at query time  
❌ Nested MongoDB array updates without understanding concurrency semantics  
❌ Two collections both claiming to store the same logical entity  

---

## Future Evolution

- **Assessment evidence versioning:** When `AssessmentEvidence` schema changes (e.g., adding a new normalized scalar), bump `schema_version` to `"1.1"`. Consumers MUST check `schema_version` before reading new fields.
- **Sharding:** If the `knowledge_nodes` collection outgrows a single MongoDB shard, the shard key is `user_id`. No application code change required — only deployment configuration.
- **Time-series collections:** `activity_events` MAY be migrated to a MongoDB time-series collection for improved aggregation performance. The document schema is unchanged; only the storage engine changes.
- **Read replicas:** The LI engine and AI Mentor context builder are read-heavy. Adding a read replica and routing their queries there is a deployment change with no application code change.
