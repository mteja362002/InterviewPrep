"""Mentor Service — the orchestration layer.

Flow for a single `answer()` call:
  1. Load / create the conversation (persisted).
  2. Persist the user's message.
  3. Build the learner context (context_builder).
  4. Assemble system + user turn (mentor_prompt). Two modes:
       - "chat"   → free-form markdown reply
       - "lesson" → strict 9-card JSON, parsed and persisted as structured_content
  5. Call the AI Gateway via `ai_service.complete()` (reused — no duplication).
  6. Persist the assistant's reply, bump the conversation counters.
  7. Return (conversation, user_msg, assistant_msg, context_preview).

Streaming is not enabled yet but the architecture supports it — replace the
`complete` call with a streamed variant later.
Everything else stays identical.
"""
from __future__ import annotations
import logging
from typing import Optional, Tuple

from ai_service import complete, AICapability, AIProviderError
from ai_gateway.parsers import parse_llm_json

from . import conversation_store as store
from .context_builder import (
    build_context, serialize_context, current_topic_kb_block, public_preview,
)
from .mentor_prompt import (
    build_system_message, build_lesson_system_message,
    build_user_message, summarise_title,
)
from .models import MentorConversation, MentorMessage

logger = logging.getLogger(__name__)

_HISTORY_TAIL = 16  # Number of past turns fed to the LLM.


async def ensure_conversation(db, *, user_id: str,
                              conversation_id: Optional[str],
                              seed_message: Optional[str] = None,
                              topic_node_id: Optional[str] = None) -> MentorConversation:
    """Return an existing conversation or create a new one with a seed title."""
    if conversation_id:
        existing = await store.get_conversation(
            db, conversation_id=conversation_id, user_id=user_id,
        )
        if existing:
            return existing
    title = summarise_title(seed_message or "New conversation")
    return await store.create_conversation(
        db, user_id=user_id, title=title, topic_node_id=topic_node_id,
    )


async def answer(db, *, user_id: str, user_message: str,
                 conversation_id: Optional[str],
                 topic_node_id: Optional[str] = None,
                 response_style: str = "chat") -> Tuple[
                     MentorConversation, MentorMessage, MentorMessage, dict,
                 ]:
    """The single public entry-point for a mentor turn.

    `response_style="chat"`   → free-form markdown reply (default).
    `response_style="lesson"` → strict 9-card JSON persisted as
        `assistant_msg.structured_content`. `content` still holds the raw JSON
        text so the transcript survives deserialisation issues.

    Any future feature (mock interviews, revision planner, etc.) can call this
    directly — either persistently (with a conversation_id) or ephemerally by
    creating a throwaway conversation.
    """
    style = response_style if response_style in ("chat", "lesson") else "chat"

    # 1. Conversation.
    convo = await ensure_conversation(
        db, user_id=user_id, conversation_id=conversation_id,
        seed_message=user_message, topic_node_id=topic_node_id,
    )
    effective_topic = topic_node_id or convo.topic_node_id

    # 2. Persist user turn immediately.
    user_msg = await store.add_message(
        db, conversation_id=convo.id, user_id=user_id, role="user",
        content=user_message, topic_node_id=effective_topic, style=style,
    )
    await store.touch_conversation(
        db, conversation_id=convo.id, user_id=user_id,
        preview=f"You: {user_message}", delta_count=1,
    )

    # 3. Context.
    context = await build_context(db, user_id=user_id, node_id=effective_topic)
    context_block = serialize_context(context)
    if style == "lesson":
        system_message = build_lesson_system_message(context_block)
    else:
        system_message = build_system_message(context_block)
    kb_block = current_topic_kb_block(context)

    # 4. Prior transcript (short-term memory) — skip in lesson mode because a
    # lesson is a single-shot structured emit.
    history = []
    if style == "chat":
        history = await store.recent_messages(
            db, conversation_id=convo.id, user_id=user_id, limit=_HISTORY_TAIL,
        )
        history = [m for m in history if m.id != user_msg.id]

    prompt = build_user_message(
        new_message=user_message, history=history, node_kb_block=kb_block,
    )

    # 5. LLM call — routed through the AI Gateway.
    capability = AICapability.MENTOR_LESSON if style == "lesson" else AICapability.MENTOR_CHAT
    raw = await complete(
        capability=capability,
        system_message=system_message,
        prompt=prompt,
        session_id=f"mentor::{convo.id}",
    )
    reply = (raw or "").strip()
    if not reply:
        raise AIProviderError(
            "Mentor returned an empty reply. Please retry.",
            kind="empty_response", status_code=502,
        )

    structured = None
    if style == "lesson":
        structured = parse_llm_json(reply)
        # If parsing failed, fall back to chat mode gracefully — the raw text
        # still gets persisted so the user sees SOMETHING useful.
        if structured is None:
            logger.warning("mentor_service: failed to parse lesson JSON; falling back to chat mode")
            style = "chat"

    # 6. Persist assistant turn.
    assistant_msg = await store.add_message(
        db, conversation_id=convo.id, user_id=user_id, role="assistant",
        content=reply, topic_node_id=effective_topic, style=style,
        structured_content=structured,
    )
    await store.touch_conversation(
        db, conversation_id=convo.id, user_id=user_id,
        preview=f"Mentor: {reply}", delta_count=1,
    )
    fresh = await store.get_conversation(db, conversation_id=convo.id, user_id=user_id)
    if fresh and fresh.message_count <= 2:
        await store.rename_conversation(
            db, conversation_id=convo.id, user_id=user_id,
            title=summarise_title(user_message),
        )
        fresh = await store.get_conversation(db, conversation_id=convo.id, user_id=user_id)

    return fresh or convo, user_msg, assistant_msg, public_preview(context)
