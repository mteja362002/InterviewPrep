# PrepOS Engineering Constitution

**Version:** 1.0  
**Status:** Active  
**Authority:** Chief Software Architect  
**Date:** 2026-08-22  

---

## What This Is

The PrepOS Engineering Constitution is the permanent architectural reference for the PrepOS system. These documents define the immutable engineering principles governing every subsystem.

Every future feature, pull request, and architectural decision MUST comply with the relevant constitution(s). Constitutions change only through the Architecture Review process defined in CONSTITUTION-010.

These are NOT:
- API documentation
- Code walkthroughs
- Implementation guides

These ARE:
- Architectural law
- Ownership boundaries
- Contract definitions
- Extension rules
- Invariants and anti-patterns

---

## Constitution Index

| # | Document | Subsystem | Key Principle |
|---|----------|-----------|--------------|
| 001 | [System Architecture](./CONSTITUTION-001-System-Architecture.md) | Entire System | Unidirectional dependency, single source of truth per domain |
| 002 | [Curriculum Engine](./CONSTITUTION-002-Curriculum-Engine.md) | `problem_bank.py`, `roadmap.py`, `selector.py`, `mission_context.py` | Static at runtime, editorial curation, no cross-contamination |
| 003 | [Mission Engine](./CONSTITUTION-003-Mission-Engine.md) | `mission_engine.py`, `routes_missions.py` | One mission/day, deterministic, composition-driven, AI is post-generation |
| 004 | [Learner Intelligence](./CONSTITUTION-004-Learner-Intelligence.md) | `services/learner_intelligence/` | 10 deterministic signals, bounded nudge, no ML, never raises |
| 005 | [Assessment Engine](./CONSTITUTION-005-Assessment-Engine.md) | `assessment/` | Immutable evidence, deterministic evaluation, exposes never applies |
| 006 | [AI Mentor](./CONSTITUTION-006-AI-Mentor.md) | `ai_mentor/`, `knowledge_generation.py` | Read-only, context-grounded, provider-agnostic, globally cached KB |
| 007 | [Company Intelligence](./CONSTITUTION-007-Company-Intelligence.md) | `company_intelligence/` | Compile-time only, read-only runtime, deterministic scoring |
| 008 | [Content Architecture](./CONSTITUTION-008-Content-Architecture.md) | `knowledge_generation.py`, `prompt_builder.py` | Global cache, first-requester-pays, strict JSON, no logic derivation |
| 009 | [Frontend Experience](./CONSTITUTION-009-Frontend-Experience.md) | `frontend/src/` | Backend drives UI state, no business logic in pages, CTA from backend |
| 010 | [Development Rules](./CONSTITUTION-010-Development-Rules.md) | All code | Sprint workflow, PR checklist, naming conventions, architecture review |
| 011 | [Data Contracts](./CONSTITUTION-011-Data-Contracts.md) | MongoDB + DTOs | Canonical schemas, additive evolution, UTC timestamps, immutable IDs |
| 012 | [Testing and Quality](./CONSTITUTION-012-Testing-and-Quality.md) | All tests | Hermetic tests, no production DB, regression policy, CI gates |

---

## Quick Reference: Key Architectural Invariants

These invariants MUST NEVER be violated:

1. **Problem IDs are immutable.** `lc-N` IDs never change, ever.
2. **Roadmap node IDs are immutable.** Once in `roadmap_v1.json`, a node ID is permanent.
3. **MissionContext is the single curriculum interface.** No subsystem independently infers pattern/stage/difficulty.
4. **Arena and Assessment problems are always disjoint.** `split_arena_assessment()` is an unconditional constraint.
5. **AssessmentEvidence is frozen.** Once created, it cannot be modified.
6. **The planner is deterministic.** Same inputs → same recommendation, always.
7. **Assessment Engine exposes, never applies.** It produces evidence; it does not consume it.
8. **LI is a bounded nudge.** Never a hard veto on any candidate node.
9. **`knowledge_nodes` is the single progress store.** No parallel progress store.
10. **Business logic belongs in the service layer.** Not in route handlers. Not in React pages.

---

## Quick Reference: Forbidden Patterns

These are prohibited in all PrepOS code:

- ❌ Business logic in FastAPI route handlers
- ❌ Business logic in React page components
- ❌ Problem metadata stored in MongoDB
- ❌ Problem selection logic that substitutes problems when the pool is empty
- ❌ Assessment Engine writing to `knowledge_nodes`
- ❌ Learner Intelligence Engine calling Assessment API
- ❌ Mission Engine calling Assessment Engine
- ❌ Company Intelligence parsed from Markdown at runtime
- ❌ LLM calls in the mission generation blocking path
- ❌ Circular imports between service modules
- ❌ Two modules owning the same MongoDB collection
- ❌ `console.log` in committed JavaScript code
- ❌ `print()` in committed Python service code
- ❌ Tests that hit the production database

---

## How to Propose a Constitution Change

1. Create a PR with your proposed changes to the relevant `CONSTITUTION-*.md` file
2. The PR title MUST start with `[ARCH REVIEW]`
3. Tag the Chief Software Architect as reviewer
4. The PR description MUST include:
   - What is changing
   - Why it is changing
   - What existing behavior is preserved
   - What implementation follows from this change
5. Only after the constitution PR is merged may the implementation PR be submitted

---

## Constitution Version History

| Date | Version | Change |
|------|---------|--------|
| 2026-08-22 | 1.0 | Initial publication — 12 constitutions |
