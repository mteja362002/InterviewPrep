# CONSTITUTION-010 — Development Rules

**Version:** 1.0  
**Status:** Active  
**Scope:** All PrepOS contributors and all PrepOS code  
**Authority:** Chief Software Architect  

---

## Purpose

This constitution defines the mandatory development standards, process rules, naming conventions, and quality gates that govern all contributions to PrepOS. Compliance is required for all pull requests. Non-compliant code MUST NOT be merged.

---

## Coding Standards

### Python (Backend)

| Rule | Standard |
|------|---------|
| Formatter | `black` (line length 88) |
| Imports | `isort` (profile=black) |
| Linter | `flake8` |
| Type checker | `mypy` (strict for new service modules) |
| Docstrings | Required on all public functions, classes, and modules |
| Type hints | Required on all public function signatures |
| Python version | 3.11+ |

### JavaScript/React (Frontend)

| Rule | Standard |
|------|---------|
| Framework | React 18 (functional components + hooks only) |
| Styling | Tailwind CSS (no inline styles, no CSS modules) |
| State management | React Context + hooks (no Redux, no Zustand) |
| API calls | Via `src/services/` only (no inline fetch) |
| Component pattern | Presentational components in `src/components/`, smart components in `src/pages/` |
| Class components | FORBIDDEN — functional components only |
| `console.log` | FORBIDDEN in committed code |

---

## Folder Ownership

| Folder | Owner | Rules |
|--------|-------|-------|
| `backend/data/` | Curriculum team | Read-only for all runtime code |
| `backend/problem_bank.py` | Curriculum team | Edit only via Sprint curriculum PRs |
| `backend/assessment/` | Assessment team | No external imports to this folder |
| `backend/services/learner_intelligence/` | LI team | No write paths to DB outside `evidence_integration.py` |
| `backend/services/learning_engine/` | Planning team | No LLM calls |
| `backend/services/problem_selection/` | Curriculum team | Architecture frozen |
| `backend/company_intelligence/` | Company Intelligence team | No runtime Markdown parsing |
| `backend/ai_mentor/` | AI Mentor team | No writes to learner-state collections |
| `frontend/src/pages/` | Frontend team | No business logic |
| `frontend/src/services/` | Frontend team | Only API calls — no logic |
| `constitution/` | Chief Architect | Changes require arch review |

---

## Naming Conventions

### Python

| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case.py` | `mission_engine.py` |
| Functions | `snake_case` | `build_mission_for_user()` |
| Classes | `PascalCase` | `LearnerIntelligenceSnapshot` |
| Constants | `UPPER_SNAKE_CASE` | `COMPANY_READINESS_WEIGHTS` |
| Private functions | `_leading_underscore` | `_clamp_difficulty_to_experience()` |
| Type aliases | `PascalCase` | `NodeId = str` |
| Dataclasses | `PascalCase` | `MissionContext` |
| MongoDB collections | `snake_case` (plural) | `knowledge_nodes`, `daily_missions` |

### JavaScript/React

| Element | Convention | Example |
|---------|-----------|---------|
| Components | `PascalCase.jsx` | `MissionControl.jsx` |
| Services | `camelCase.js` | `missionService.js` |
| Contexts | `PascalCase + Context` | `AuthContext.js` |
| Custom hooks | `use + PascalCase` | `useMission.js` |
| Constants | `UPPER_SNAKE_CASE` | `API_BASE_URL` |

### API Endpoints

| Pattern | Rule |
|---------|------|
| Resources | Plural nouns: `/api/missions`, `/api/assessments` |
| Actions | POST with action path: `/api/mission/complete`, `/api/assessment/{id}/evaluate` |
| Identifiers | UUID slugs, not sequential integers |
| Versions | No versioning prefix in v1 (future: `/api/v2/...`) |

---

## Sprint Workflow

### Sprint Structure

Each sprint MUST:
1. Be scoped to a specific subsystem or feature area
2. Have a defined start and end date
3. Begin with an architecture review if touching constitutionally-governed modules
4. Produce no more than one major subsystem change per sprint

### Architecture Freeze Rules

When a module is marked **Architecture Freeze** (Phase 3C.1):
- Its external contracts MUST NOT change
- Its internal logic MAY be refactored only if behavior is byte-identical for the same inputs
- New capabilities MUST be added via extension points defined in the relevant constitution, not by modifying frozen code
- Any change to a frozen module REQUIRES an explicit Architecture Review (see below)

### Sprint 2 (Curriculum Expansion) Specific Rules

Sprint 2 modifies `backend/problem_bank.py` ONLY:
1. One module per PR (arrays, hashing, two_pointers, etc.)
2. Every problem MUST pass schema validation (see CONSTITUTION-002)
3. No changes to `selector.py`, `mission_context.py`, `roadmap_v1.json`, or any engine
4. `representative: True` requires a written editorial justification in the PR description
5. All problem IDs MUST be globally unique within the bank

---

## Pull Request Checklist

Every PR MUST address all applicable items before merge:

### Code Quality

- [ ] `black` formatting passes
- [ ] `isort` import ordering passes
- [ ] `flake8` linting passes with no errors
- [ ] No `console.log` in JavaScript files
- [ ] No `print()` debug statements in Python (use `logging`)
- [ ] All new public functions have type hints and docstrings

### Architecture

- [ ] No circular imports introduced
- [ ] No new cross-layer dependency that violates CONSTITUTION-001
- [ ] No business logic added to a route handler
- [ ] No business logic added to a React page component
- [ ] No new MongoDB collection introduced without constitution update
- [ ] No frozen module modified without Architecture Review sign-off

### Curriculum PRs (Sprint 2)

- [ ] Only `problem_bank.py` modified
- [ ] All new problems have: id, leetcode_id, title, difficulty, learning_stage, pattern, primary_pattern, estimated_minutes, leetcode_url, frequency, companies, representative
- [ ] `pattern == primary_pattern` for every new problem
- [ ] No new problem uses `learning_stage: "intermediate"`
- [ ] Representative problems are justified in PR description
- [ ] No duplicate `id` or `leetcode_id` in the full `PROBLEMS` list

### Testing

- [ ] New service functions have unit tests
- [ ] Existing tests pass: `pytest backend/tests/ -x`
- [ ] No test file deleted without explicit justification
- [ ] Test fixtures don't reach production database

### Documentation

- [ ] Inline docstring updated for changed public functions
- [ ] `test_result.md` updated with changes affecting tested behavior
- [ ] Constitution updated if a new module is introduced that changes ownership boundaries

---

## Testing Expectations

### Unit Tests

All service layer functions MUST have unit tests. Test coverage MUST be maintained at ≥70% for all `backend/services/` modules.

| Module | Test File |
|--------|----------|
| `services/learning_engine/ranking.py` | `tests/test_ranking.py` |
| `services/problem_selection/selector.py` | `tests/test_selector.py` |
| `services/learner_intelligence/engine.py` | `tests/test_learner_intelligence.py` |
| `assessment/evaluation_engine.py` | `tests/test_evaluation.py` |
| `services/mission_context.py` | `tests/test_mission_context.py` |

### Test Rules

- Tests MUST NOT hit the production database
- Tests MUST NOT call external APIs (LLM, SMTP)
- Tests MUST be hermetic (no shared mutable state between tests)
- Fixtures in `conftest.py` are preferred over per-test setup
- `pytest-xdist` SHOULD be used for parallel test execution

### Integration Tests

Integration tests MUST use a test-only MongoDB instance (configured via `TEST_MONGO_URI` env var). Integration tests MUST be tagged with `@pytest.mark.integration` and run separately from unit tests.

---

## Backward Compatibility Rules

### Database Schema

- New fields on existing MongoDB documents MUST have default values (backward compatible reads)
- Removing a field from a MongoDB document requires a migration + grace period
- Renaming a MongoDB field is a breaking change — add the new field first, migrate data, remove old field
- No field rename is ever atomic — it requires at least two deployments

### API Contracts

- Removing an API endpoint requires a 2-sprint deprecation period
- Adding new required fields to request bodies is a breaking change — use optional fields with defaults
- Response shape additions are backward-compatible (callers ignore unknown fields)

### Problem Bank

- Problem IDs (`lc-N`) MUST NEVER change — immutable forever
- `representative` designation MAY be revoked, but the problem MUST remain in the bank
- Learning stage MAY be changed only in a curriculum review sprint, with Assessment team sign-off

### Roadmap

- Node IDs MUST NEVER change — immutable forever
- Node hierarchy MAY be restructured in a new roadmap version
- Existing roadmap version (`v1`) content is immutable after publish

---

## Versioning

### Roadmap Versioning

- Format: `v{N}` (e.g., `v1`, `v2`)
- Stored on each `DailyMission` and `KnowledgeNode` document
- All users on `v1` when `v2` deploys; migration is per-user (each user migrates when they next generate a mission)

### API Versioning

- No versioning prefix in v1
- Future version: `/api/v2/` prefix for breaking changes
- Existing v1 endpoints remain active for a grace period

### Problem Bank Versioning

No explicit version number — it is tracked via git. The `id` field is the stable key.

---

## Architecture Review Process

An Architecture Review is required when:
1. A new cross-service dependency is proposed
2. A frozen module is proposed for modification
3. A new MongoDB collection is proposed
4. A new subsystem is proposed
5. A constitution document is proposed for modification

**Review process:**
1. Author files an Architecture Review Request (a PR against `constitution/`) describing the proposed change and its rationale
2. Chief Software Architect reviews within 2 business days
3. Approval + merge of the constitution change constitutes the architectural decision record (ADR)
4. The implementation PR may only be submitted after the constitution change is merged

---

## Incident Rules

### Production Incidents

- No hotfix may bypass testing
- Hotfixes to the planning pipeline require both the LI team and Planning team to review
- Any hotfix that changes problem selection behavior requires Assessment team sign-off
- Hotfixes to `problem_bank.py` must be reviewed by the Curriculum team

### Data Incidents

- No MongoDB collection may be dropped without explicit command-by-command user approval (see accidental-data-loss-prevention)
- Database migrations require a rollback plan documented before execution
- `knowledge_nodes` deletions affect all progress data — MUST be irreversibility-flagged

---

## Invariants

1. Every merged PR leaves the test suite green.
2. No PR is merged without at least one review approval.
3. Constitution documents are the authoritative source of architectural decisions.
4. The `test_result.md` file is updated whenever tested behavior changes.
5. All environment variables are documented in `.env.example` — no undocumented env vars in production code.

---

## Anti-patterns

❌ Merging without tests passing  
❌ Adding `# noqa` comments to suppress lint errors (fix the error instead)  
❌ Direct database connection in test code (use fixtures + test DB)  
❌ Committing `.env` files with real credentials  
❌ Implementing features in the wrong layer (backend logic in frontend, planning logic in routes)  
❌ Architecture changes without an Architecture Review PR  
❌ Curriculum changes (Sprint 2) without an editorial justification for `representative: True`  
❌ Copying logic from one service module to another instead of extracting a shared utility  
❌ Python `print()` in non-CLI code  
❌ JavaScript `console.log` in committed code  

---

## Future Evolution

- **CI/CD pipeline:** Add GitHub Actions to run `black`, `isort`, `flake8`, `mypy`, `pytest` on every PR automatically.
- **Code coverage gates:** Enforce minimum 70% coverage via `pytest-cov` in CI.
- **Architectural lint:** A future custom linter checks cross-layer dependency violations using `import-linter` or `dependency-cruiser`.
- **Constitution review cadence:** Constitutions are reviewed quarterly. Changes are proposed via PR against `constitution/` — the review process is the same as Architecture Review.
