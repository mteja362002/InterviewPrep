# CONSTITUTION-012 — Testing and Quality

**Version:** 1.0  
**Status:** Active  
**Scope:** All PrepOS test infrastructure, CI quality gates, code review standards, performance benchmarks  
**Authority:** Chief Software Architect  

---

## Purpose

This constitution establishes the testing standards, quality gates, and code review process for PrepOS. It defines what must be tested, how tests are structured, what constitutes a quality regression, and how quality is verified before code reaches production.

Testing is not optional. A feature without tests is not complete. A bug without a regression test is not fixed.

---

## Responsibilities

### Testing and Quality Owns

- Unit test standards and coverage requirements
- Integration test standards and environment setup
- Regression test policy
- Performance benchmark definitions
- CI/CD quality gate definitions
- Code review standards

### Testing and Quality Does NOT Own

- Test data (owned by the producing subsystem's test fixtures)
- Test infrastructure provisioning beyond `pytest` configuration (owned by DevOps)

---

## Architectural Principles

### TQ-001 — Hermetic Tests

Every test MUST be hermetic: it MUST produce the same result regardless of execution order, time of day, external network state, or other tests that ran before or after it. No test may leave side effects that affect other tests.

### TQ-002 — No Production Database in Tests

Unit tests MUST use in-memory data structures or mock objects. Integration tests MUST use a test-only MongoDB instance configured via the `TEST_MONGO_URI` environment variable. `MONGO_URI` MUST NEVER point to a production database during test execution.

### TQ-003 — No External API Calls in Tests

Tests MUST NOT call Google Gemini, any LLM, SMTP, or any external HTTP service. All external calls MUST be mocked. `pytest-monkeypatch` or `unittest.mock` are the canonical mocking tools.

### TQ-004 — Tests are the Safety Net for Architecture

Tests MUST verify the architectural invariants defined in the constitutions — not just functional correctness. A test that passes but allows a forbidden dependency is not a good test.

### TQ-005 — Coverage as a Minimum, Not a Goal

Coverage targets are minimum thresholds, not objectives. 100% coverage with poor assertions is worthless. 70% coverage with strong assertions on critical paths is better. Prioritize tests on correctness-critical paths (scoring, selection, evaluation, evidence).

---

## Test Taxonomy

| Level | Scope | Tools | Speed | DB |
|-------|-------|-------|-------|----|
| Unit | Single function or class | `pytest`, `unittest.mock` | <1s/test | None |
| Integration | Multiple modules + real DB | `pytest`, Motor, test MongoDB | <10s/test | Test DB |
| System | Full API endpoint | `pytest`, FastAPI `TestClient` | <5s/test | Test DB |
| Performance | Throughput and latency | `pytest`, `time.perf_counter` | As needed | Test DB |

---

## Unit Testing Standards

### Required Coverage by Module

| Module | Minimum Coverage | Priority |
|--------|-----------------|----------|
| `services/problem_selection/selector.py` | 90% | Critical |
| `services/learning_engine/ranking.py` | 85% | Critical |
| `assessment/evaluation_engine.py` | 90% | Critical |
| `assessment/evidence.py` | 90% | Critical |
| `services/learner_intelligence/engine.py` | 80% | High |
| `services/mission_context.py` | 85% | Critical |
| `roadmap.py` | 80% | High |
| `services/progress_engine.py` | 75% | High |
| `services/revision_engine.py` | 75% | High |
| `prompt_builder.py` | 70% | Medium |

### Unit Test Requirements for Critical Modules

#### `services/problem_selection/selector.py`

Every test MUST verify:
- `representative_pool()` returns only problems matching the given pattern
- `representative_pool()` returns only problems matching the given learning_stage
- `representative_pool()` returns empty list when no match (NEVER substitutes)
- `split_arena_assessment()` produces disjoint sets
- `split_arena_assessment()` Arena problems are NOT in Assessment problems
- Selection result is deterministic (same input → same output)
- `select_one()` returns `None` when pool is empty (NEVER falls back to a different problem)

#### `assessment/evaluation_engine.py`

Every test MUST verify:
- Rubric weights sum to 1.0 (for every defined rubric)
- Correct (≥80) / Partially Correct (≥50) / Incorrect (<50) verdict thresholds
- `confidence_delta` is within [-1, 1] for all inputs
- `accuracy` is within [0, 1] for all inputs
- `proficiency` is within [0, 1] for all inputs
- Evaluation result is deterministic

#### `assessment/evidence.py`

Every test MUST verify:
- `AssessmentEvidence` is frozen after construction (no field mutation)
- `weakness_confirmation` is True only when conditions are met
- `revision_trigger` is True only when conditions are met
- `schema_version` is always set

#### `services/mission_context.py`

Every test MUST verify:
- `coding_pattern` comes from `roadmap.pattern_for_node()` only
- `representative_problem_ids` comes from `representative_pool()` only
- `activity_type` comes from the roadmap node, never re-derived
- `MissionContext` is `None` when node_id is invalid

---

## Integration Testing Standards

### Test MongoDB Setup

```python
# conftest.py
@pytest.fixture(scope="session")
def test_db():
    client = AsyncMotorClient(os.environ["TEST_MONGO_URI"])
    db = client["prepos_test"]
    yield db
    client.close()

@pytest.fixture(autouse=True)
async def clear_collections(test_db):
    """Wipe test collections before each test."""
    for coll in TEST_COLLECTIONS:
        await test_db[coll].delete_many({})
```

### Integration Test Coverage

| Flow | Test File | What to Verify |
|------|-----------|---------------|
| Mission generation | `tests/integration/test_mission_generation.py` | Full flow from node_id → DailyMission |
| Assessment lifecycle | `tests/integration/test_assessment_lifecycle.py` | PENDING → COMPLETED state machine |
| Evidence integration | `tests/integration/test_evidence_integration.py` | Evidence → knowledge_nodes update |
| Roadmap unlock logic | `tests/integration/test_roadmap_unlock.py` | Prerequisites gate unlock correctly |
| Revision scheduling | `tests/integration/test_revision_engine.py` | Stages advance correctly |

---

## System Tests (API Level)

System tests call the FastAPI `TestClient` (from `httpx`) and exercise full request → response cycles.

### Required System Tests

| Endpoint | Test | Assertion |
|----------|------|-----------|
| `GET /api/mission/today` | No existing mission → generates new | DailyMission returned with tasks |
| `GET /api/mission/today` | Existing mission → returns cached | Same DailyMission, no regeneration |
| `POST /api/arena/problem/feedback` | Valid feedback → stored | Returns 200 with feedback_id |
| `GET /api/arena/problem` | Mission exists → returns representative problem | Problem matches mission's pattern |
| `POST /api/assessment` | Valid request → assessment created | Status: PENDING, question present |
| `POST /api/assessment/{id}/evaluate` | After submit → returns evidence | Evidence fields are within bounds |
| `GET /api/roadmap/node/{id}/content` | Cache miss → generates content | All content sections present |
| `GET /api/roadmap/node/{id}/content` | Cache hit → no LLM call | Same content returned faster |
| `POST /api/mentor/message` | Valid message → response | Non-empty response string |

---

## Regression Test Policy

### Definition of a Regression

A regression is any change that:
1. Changes the output of a deterministic function for the same inputs
2. Breaks an architectural invariant
3. Changes an API response shape in a non-additive way
4. Fails a test that previously passed

### Regression Test Requirement

**Every bug fix MUST include a regression test** that:
1. Reproduces the bug (test FAILS before the fix)
2. Verifies the fix (test PASSES after the fix)
3. Is named `test_regression_<bug_description>` or annotated with `@pytest.mark.regression`

This prevents the same bug from recurring silently.

---

## Performance Benchmarks

### Target Latency (P95 under typical load)

| Operation | P95 Target |
|-----------|-----------|
| `GET /api/mission/today` (cache hit) | <200ms |
| `GET /api/mission/today` (generation) | <800ms |
| `GET /api/arena/problem` | <100ms |
| `POST /api/arena/problem/feedback` | <150ms |
| `POST /api/assessment/{id}/evaluate` | <150ms |
| `GET /api/roadmap/node/{id}/content` (cache hit) | <50ms |
| `POST /api/mentor/message` (first token) | <2000ms |

### Performance Test Procedure

Performance tests MUST be run against the test MongoDB with realistic test data (~200 knowledge_nodes per user, ~50 feedback entries). They MUST NOT be run against production.

Performance tests MUST be tagged `@pytest.mark.performance` and excluded from the standard test run:
```
pytest -m "not performance"  # standard
pytest -m performance        # performance only
```

---

## Code Review Standards

### Review Requirements

| Change Type | Required Reviewers |
|------------|-------------------|
| Bug fix (non-critical path) | 1 reviewer |
| Bug fix (critical path: selector, ranking, evaluation) | 2 reviewers |
| New feature | 1 reviewer + author walkthrough |
| Architecture change | Chief Architect + 1 team reviewer |
| Constitution change | Chief Architect only |
| `problem_bank.py` curriculum addition | 1 Curriculum team reviewer |
| Database migration | 1 reviewer + DBA review |

### Review Checklist for Reviewers

- [ ] Tests are present and meaningful (not just coverage theater)
- [ ] No business logic in presentation layers
- [ ] No new forbidden dependency introduced
- [ ] No hardcoded values that should be configurable
- [ ] Error handling is explicit (no silent swallowing of exceptions)
- [ ] Logging is appropriate (not too verbose, not missing)
- [ ] Performance implications considered (no O(n²) in hot path)
- [ ] Backward compatibility maintained for API contracts

---

## Test File Organization

```
backend/
└── tests/
    ├── conftest.py                    # Shared fixtures
    ├── unit/
    │   ├── test_selector.py           # Problem selection unit tests
    │   ├── test_ranking.py            # Learning engine ranking
    │   ├── test_evaluation.py         # Assessment evaluation
    │   ├── test_evidence.py           # Evidence construction
    │   ├── test_mission_context.py    # MissionContext builder
    │   ├── test_roadmap.py            # Roadmap graph logic
    │   ├── test_progress_engine.py    # Progress rollup
    │   ├── test_revision_engine.py    # Spaced repetition
    │   └── test_learner_intelligence/ # LI signal unit tests (one file per signal)
    ├── integration/
    │   ├── test_mission_generation.py
    │   ├── test_assessment_lifecycle.py
    │   ├── test_evidence_integration.py
    │   └── test_revision_scheduling.py
    ├── system/
    │   ├── test_mission_api.py
    │   ├── test_assessment_api.py
    │   ├── test_roadmap_api.py
    │   └── test_mentor_api.py
    └── performance/
        ├── test_mission_generation_perf.py
        └── test_selection_perf.py
```

---

## CI/CD Quality Gates

### Required Gates (all must pass before merge)

1. **Formatting:** `black --check backend/` → must exit 0
2. **Imports:** `isort --check-only backend/` → must exit 0
3. **Linting:** `flake8 backend/` → must exit 0 (no errors)
4. **Unit tests:** `pytest backend/tests/unit/ -x` → must pass all tests
5. **System tests:** `pytest backend/tests/system/ -x` → must pass all tests

### Optional Gates (run on schedule, not blocking)

- **Integration tests:** `pytest backend/tests/integration/ -m integration` — run nightly
- **Performance tests:** `pytest backend/tests/performance/ -m performance` — run weekly
- **Coverage report:** `pytest --cov=backend --cov-report=html` — generated but not a blocker in v1

---

## `test_result.md` Protocol

The `test_result.md` file is the communication log between human engineers and AI agents. It documents:

1. Which tests passed/failed on the most recent test run
2. Known failures and their workaround status
3. Architectural decisions confirmed by tests

Format:
```yaml
# test_result.md
# Last updated: YYYY-MM-DD by <agent or human>

summary:
  total: N
  passed: N
  failed: N
  skipped: N

failed_tests:
  - test_name: "test_selector_returns_empty_on_no_match"
    reason: "Known issue: intermediate stage not in problem bank"
    status: "open | workaround | fixed"
    sprint: "Sprint 2"

architecture_confirmations:
  - "selector.split_arena_assessment() always produces disjoint sets — VERIFIED"
  - "AssessmentEvidence is frozen — VERIFIED"
```

Every AI agent that runs tests MUST update `test_result.md` with the results of each test run.

---

## Invariants

1. All PRs to `main`/`develop` must have all required CI gates passing.
2. No test may hit the production database.
3. Every bug fix MUST include a regression test.
4. `test_result.md` is updated every time a test run is performed.
5. Performance tests are tagged and excluded from the standard test run.

---

## Anti-patterns

❌ Tests that pass due to coincidental test ordering  
❌ Tests that use production environment variables  
❌ Mock objects that don't match the real interface they're mocking  
❌ Test fixtures that mutate global state  
❌ Skipping tests with `@pytest.mark.skip` without a documented reason and a deadline for removal  
❌ Coverage as a proxy for quality (100% coverage with trivial assertions is not quality)  
❌ System tests that test only the happy path (error paths MUST also be tested)  
❌ Performance tests run against production (always use test infrastructure)  

---

## Future Evolution

- **CI/CD pipeline:** GitHub Actions workflow running all required gates automatically on PR creation and push.
- **Coverage enforcement:** `pytest-cov` with `--fail-under=70` for `backend/services/` modules, enforced in CI.
- **Mutation testing:** `mutmut` or `cosmic-ray` to verify that tests actually catch bugs (not just satisfy coverage).
- **Contract testing:** `pact` or similar for verifying that frontend API consumption matches backend API contracts.
- **Load testing:** `locust` scripts for simulating concurrent user mission generation under load.
- **Architecture linting:** `import-linter` configured to enforce the dependency rules from CONSTITUTION-001 automatically in CI.
