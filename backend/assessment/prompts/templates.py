"""Concrete provider-agnostic prompt builders for non-coding assessments.

Each builder reads ONLY the MissionContext + learner signals the freeze
enumerates: learning objectives, prerequisites, difficulty, learning stage,
confidence, mastery, companies, excluded topics. The roadmap stays the
curriculum designer; the (future) LLM is only a content generator.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import PromptSpec, register_prompt


def _signals(learner_signals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    s = dict(learner_signals or {})
    return {
        "confidence": s.get("confidence"),
        "mastery": s.get("mastery"),
        "excluded_topics": list(s.get("excluded_topics", []) or []),
    }


def _common_variables(context: Any, learner_signals: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sig = _signals(learner_signals)
    return {
        "topic": getattr(context, "topic", None),
        "subject": getattr(context, "subject", None),
        "learning_stage": getattr(context, "learning_stage", None),
        "difficulty": getattr(context, "difficulty", None),
        "learning_objectives": list(getattr(context, "learning_objectives", []) or []),
        "prerequisites": list(getattr(context, "prerequisites", []) or []),
        "related_topics": list(getattr(context, "related_topics", []) or []),
        "target_companies": list(getattr(context, "target_companies", []) or []),
        "confidence": sig["confidence"],
        "mastery": sig["mastery"],
        "excluded_topics": sig["excluded_topics"],
    }


def _objectives_block(v: Dict[str, Any]) -> str:
    objs = v.get("learning_objectives") or []
    return "\n".join(f"- {o}" for o in objs) or "- (none provided)"


_QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer_index": {"type": "integer"},
                    "explanation": {"type": "string"},
                },
            },
        }
    },
}


@register_prompt("quiz")
def build_quiz_prompt(context: Any, learner_signals: Optional[Dict[str, Any]] = None) -> PromptSpec:
    v = _common_variables(context, learner_signals)
    system = (
        "You are an interview-prep quiz author. Generate conceptual questions "
        "that validate the given learning objectives at the specified stage "
        "and difficulty. Never test topics outside the objectives/prerequisites "
        "or any excluded topics."
    )
    user = (
        f"Subject: {v['subject']}\nTopic: {v['topic']}\n"
        f"Learning stage: {v['learning_stage']}\nDifficulty: {v['difficulty']}\n"
        f"Learning objectives:\n{_objectives_block(v)}\n"
        f"Prerequisites: {v['prerequisites']}\n"
        f"Excluded topics (do NOT test): {v['excluded_topics']}\n"
        f"Target companies (flavour only): {v['target_companies']}\n"
    )
    return PromptSpec("quiz", system, user, variables=v, output_schema=_QUIZ_SCHEMA)


@register_prompt("behavioral")
def build_behavioral_prompt(context: Any, learner_signals: Optional[Dict[str, Any]] = None) -> PromptSpec:
    v = _common_variables(context, learner_signals)
    system = (
        "You are a behavioral interviewer. Produce STAR-style behavioral "
        "questions aligned to the learning objectives. Stay within scope."
    )
    user = (
        f"Topic: {v['topic']}\nLearning objectives:\n{_objectives_block(v)}\n"
        f"Target companies: {v['target_companies']}\n"
        f"Difficulty: {v['difficulty']}\n"
    )
    schema = {
        "type": "object",
        "properties": {
            "questions": {"type": "array", "items": {"type": "object", "properties": {
                "prompt": {"type": "string"},
                "what_good_looks_like": {"type": "string"},
            }}}
        },
    }
    return PromptSpec("behavioral", system, user, variables=v, output_schema=schema)


@register_prompt("design")
def build_design_prompt(context: Any, learner_signals: Optional[Dict[str, Any]] = None) -> PromptSpec:
    v = _common_variables(context, learner_signals)
    system = (
        "You are a low-level design (OOD) interviewer. Produce a design prompt "
        "validating the objectives at the given stage/difficulty."
    )
    user = (
        f"Topic: {v['topic']}\nLearning objectives:\n{_objectives_block(v)}\n"
        f"Prerequisites: {v['prerequisites']}\nDifficulty: {v['difficulty']}\n"
    )
    schema = {
        "type": "object",
        "properties": {
            "scenario": {"type": "string"},
            "requirements": {"type": "array", "items": {"type": "string"}},
            "evaluation_rubric": {"type": "array", "items": {"type": "string"}},
        },
    }
    return PromptSpec("design", system, user, variables=v, output_schema=schema)


@register_prompt("system_design")
def build_system_design_prompt(context: Any, learner_signals: Optional[Dict[str, Any]] = None) -> PromptSpec:
    v = _common_variables(context, learner_signals)
    system = (
        "You are a system design (HLD) interviewer. Produce a scalable-systems "
        "design prompt validating the objectives at the given stage/difficulty."
    )
    user = (
        f"Topic: {v['topic']}\nLearning objectives:\n{_objectives_block(v)}\n"
        f"Prerequisites: {v['prerequisites']}\nDifficulty: {v['difficulty']}\n"
        f"Target companies: {v['target_companies']}\n"
    )
    schema = {
        "type": "object",
        "properties": {
            "scenario": {"type": "string"},
            "functional_requirements": {"type": "array", "items": {"type": "string"}},
            "non_functional_requirements": {"type": "array", "items": {"type": "string"}},
            "evaluation_rubric": {"type": "array", "items": {"type": "string"}},
        },
    }
    return PromptSpec("system_design", system, user, variables=v, output_schema=schema)
