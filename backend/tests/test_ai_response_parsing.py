"""Offline regression coverage for shared LLM JSON response parsing."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ai_gateway.parsers import (
    extract_first_json_object,
    parse_llm_json,
    strip_code_fence,
)
from ai_mentor import mentor_service, mission_planner
from ai_mentor.models import MentorConversation, MentorMessage
from prompt_builder import parse_content


def test_parse_llm_json_accepts_raw_json_and_whitespace():
    assert parse_llm_json(" \n {\"answer\": 42} \t") == {"answer": 42}


def test_parse_llm_json_accepts_markdown_code_fence():
    assert parse_llm_json("```json\n{\"answer\": true}\n```") == {"answer": True}
    assert strip_code_fence(" ```\n{\"answer\": true}\n``` ") == '{"answer": true}'


def test_parse_llm_json_extracts_object_from_surrounding_text():
    raw = "Here is the requested payload: {\"nested\": {\"value\": 1}} Thanks!"
    assert extract_first_json_object(raw) == '{"nested": {"value": 1}}'
    assert parse_llm_json(raw) == {"nested": {"value": 1}}


@pytest.mark.parametrize("raw", ["", "not json", "{\"missing\": ]"])
def test_parse_llm_json_returns_none_for_invalid_json(raw):
    assert parse_llm_json(raw) is None


def test_knowledge_parser_keeps_normalization_and_malformed_fallback():
    content = parse_content("```json\n{\"theory\": {\"beginner\": \"x\"}, \"flashcards\": [{\"q\": \"q\", \"a\": \"a\"}]}\n```")
    assert content["theory"] == {"beginner": "x"}
    assert content["flashcards"] == [{"q": "q", "a": "a"}]

    malformed = parse_content("not valid JSON")
    assert malformed["_parse_error"] is True
    assert malformed["_raw"] == "not valid JSON"
    assert malformed["examples"] == []


def test_mentor_uses_the_canonical_parser_without_legacy_helper():
    assert mentor_service.parse_llm_json is parse_llm_json
    assert not hasattr(mentor_service, "_parse_lesson_json")


@pytest.mark.parametrize(
    ("raw", "expected_style", "expected_structured"),
    [
        ("```json\n{\"executive_summary\": \"Arrays\"}\n```", "lesson", {"executive_summary": "Arrays"}),
        ("not valid JSON", "chat", None),
    ],
)
def test_mentor_lesson_keeps_structured_or_chat_fallback_behavior(
    raw, expected_style, expected_structured,
):
    conversation = MentorConversation(
        id="conversation-1", user_id="user-1", title="Arrays", message_count=3,
        created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
    )
    user_message = MentorMessage(
        id="user-message", conversation_id=conversation.id, user_id="user-1",
        role="user", content="Teach arrays", created_at="2026-01-01T00:00:00Z",
    )
    assistant_message = MentorMessage(
        id="assistant-message", conversation_id=conversation.id, user_id="user-1",
        role="assistant", content=raw, created_at="2026-01-01T00:00:01Z",
    )
    add_message = AsyncMock(side_effect=[user_message, assistant_message])
    with patch("ai_mentor.mentor_service.ensure_conversation", new=AsyncMock(return_value=conversation)), \
         patch("ai_mentor.mentor_service.store.add_message", new=add_message), \
         patch("ai_mentor.mentor_service.store.touch_conversation", new=AsyncMock()), \
         patch("ai_mentor.mentor_service.store.get_conversation", new=AsyncMock(return_value=conversation)), \
         patch("ai_mentor.mentor_service.build_context", new=AsyncMock(return_value={})), \
         patch("ai_mentor.mentor_service.serialize_context", return_value="context"), \
         patch("ai_mentor.mentor_service.current_topic_kb_block", return_value=""), \
         patch("ai_mentor.mentor_service.public_preview", return_value={}), \
         patch("ai_mentor.mentor_service.complete", new=AsyncMock(return_value=raw)):
        asyncio.run(
            mentor_service.answer(
                object(), user_id="user-1", user_message="Teach arrays",
                conversation_id=conversation.id, response_style="lesson",
            )
        )

    persisted = add_message.await_args_list[1].kwargs
    assert persisted["style"] == expected_style
    assert persisted["structured_content"] == expected_structured


def test_mission_planner_uses_shared_parser_and_preserves_empty_fallback():
    mission = {"title": "Arrays", "tasks": []}
    with patch(
        "ai_mentor.mission_planner.build_context", new=AsyncMock(return_value={}),
    ), patch(
        "ai_mentor.mission_planner.serialize_context", return_value="context",
    ), patch(
        "ai_mentor.mission_planner.complete",
        new=AsyncMock(return_value="Narrative: {\"narrative\": \"Keep practicing arrays.\", \"tomorrow_preview\": {\"focus\": \"Hash maps\"}}"),
    ):
        result = asyncio.run(
            mission_planner.generate_narrative_and_previews(
                object(), user_id="user-1", mission=mission,
            )
        )
    assert result == {
        "ai_narrative": "Keep practicing arrays.",
        "tomorrow_preview": {"focus": "Hash maps"},
        "week_goal": None,
    }

    with patch(
        "ai_mentor.mission_planner.build_context", new=AsyncMock(return_value={}),
    ), patch(
        "ai_mentor.mission_planner.serialize_context", return_value="context",
    ), patch(
        "ai_mentor.mission_planner.complete", new=AsyncMock(return_value="not json"),
    ):
        assert asyncio.run(
            mission_planner.generate_narrative_and_previews(
                object(), user_id="user-1", mission=mission,
            )
        ) == {}
