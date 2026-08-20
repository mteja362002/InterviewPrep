"""Assessment Engine (Phase 3A) — reusable, deterministic assessment platform.

The single evidence source between learning and planning. Modular by design:

    schemas.py               -- domain objects + vocabulary
    rubrics.py               -- reusable weighted rubrics
    difficulty.py            -- difficulty mapping / recommendation
    assessment_types.py      -- extensible type registry (coding implemented)
    assessment_generator.py  -- question generation (reuses problem_bank)
    evaluation_engine.py     -- deterministic rubric scoring
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

__all__ = ["router", "ensure_indexes"]
