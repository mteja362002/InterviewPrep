"""Prompt template interface + registry (provider-agnostic)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class PromptSpec:
    """A provider-agnostic prompt. No model / provider is referenced here."""
    assessment_type: str
    system: str
    user: str
    variables: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_type": self.assessment_type,
            "system": self.system,
            "user": self.user,
            "variables": self.variables,
            "output_schema": self.output_schema,
        }


# A builder takes (context, learner_signals) -> PromptSpec.
PromptTemplate = Callable[[Any, Optional[Dict[str, Any]]], PromptSpec]

PROMPT_REGISTRY: Dict[str, PromptTemplate] = {}


def register_prompt(assessment_type: str) -> Callable[[PromptTemplate], PromptTemplate]:
    def _wrap(fn: PromptTemplate) -> PromptTemplate:
        PROMPT_REGISTRY[assessment_type] = fn
        return fn
    return _wrap


def get_prompt_template(assessment_type: str) -> Optional[PromptTemplate]:
    """Return the prompt builder for an assessment_type, or None.

    Note: ``coding`` intentionally has NO prompt template — coding assessments
    are powered by representative problems, not AI generation.
    """
    return PROMPT_REGISTRY.get(assessment_type)
