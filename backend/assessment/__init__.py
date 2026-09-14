"""Assessment Engine (Sprint 3A) — reusable, deterministic assessment platform.

The single evidence source between learning and planning. Modular by design:

    schemas.py               -- domain objects + vocabulary
    rubrics.py               -- reusable weighted rubrics
    difficulty.py            -- difficulty mapping / recommendation
    assessment_types.py      -- extensible type registry
    assessment_generator.py  -- coding question generation (reuses problem_bank)
    ai_generator.py          -- non-coding AI generation (Sprint 3A)
    evaluators.py            -- type-specific evaluator registry (Sprint 3A)
    evaluation_engine.py     -- deterministic coding rubric scoring
    feedback_engine.py       -- structured feedback
    evidence.py              -- structured evidence (exposed, never applied)
    recommendations.py       -- next-step recommendation
    assessment_session.py    -- lifecycle state machine
    assessment_history.py    -- persistence (assessments collection)
    assessment_engine.py     -- orchestrator (application service)
    api.py                   -- REST API router
"""
from .api import router
from .assessment_history import ensure_indexes

# Sprint 3A: import new modules so their registrations execute at load time.
from . import ai_generator as _ai_generator    # noqa: F401 — registers non-coding generators
from . import evaluators as _evaluators        # noqa: F401 — registers evaluators

__all__ = ["router", "ensure_indexes"]

