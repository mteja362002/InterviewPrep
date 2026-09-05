"""AI Mentor — HTTP surface."""
from __future__ import annotations
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from ai_service import AIProviderError

from . import conversation_store as store
from . import mentor_service
from .context_builder import build_context, public_preview
from .models import (
    ChatRequest, ChatResponse, NewChatRequest,
    ConversationDetail, ConversationListItem, MentorConversation,
)

router = APIRouter(prefix="/api/mentor", tags=["mentor"])
log = logging.getLogger(__name__)


def _ai_error_to_http(err: AIProviderError) -> HTTPException:
    return HTTPException(
        status_code=err.status_code or 500,
        detail={"error": err.kind, "message": str(err)},
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user=Depends(get_current_user)):
    """Main chat endpoint — creates a conversation on demand, persists both
    turns, calls the AI via the mentor service."""
    from server import db
    try:
        convo, user_msg, assistant_msg, preview = await mentor_service.answer(
            db,
            user_id=user["id"],
            user_message=payload.message,
            conversation_id=payload.conversation_id,
            topic_node_id=payload.topic_node_id,
            response_style=payload.response_style or "chat",
        )
    except AIProviderError as e:
        raise _ai_error_to_http(e)
    return ChatResponse(
        conversation_id=convo.id,
        user_message=user_msg,
        message=assistant_msg,
        conversation=convo,
        context_summary=preview,
    )


@router.post("/new-chat", response_model=MentorConversation)
async def new_chat(payload: NewChatRequest, user=Depends(get_current_user)):
    """Explicit new-conversation endpoint. Useful when the UI wants a blank
    thread before the user has typed a first message (e.g. "New chat" button)."""
    from server import db
    convo = await store.create_conversation(
        db,
        user_id=user["id"],
        title=payload.seed_title or "New conversation",
        topic_node_id=payload.topic_node_id,
    )
    return convo


@router.get("/history", response_model=List[ConversationListItem])
async def history(user=Depends(get_current_user)):
    from server import db
    convos = await store.list_conversations(db, user_id=user["id"])
    return [
        ConversationListItem(
            id=c.id, title=c.title, topic_node_id=c.topic_node_id,
            message_count=c.message_count,
            last_message_preview=c.last_message_preview,
            updated_at=c.updated_at,
        )
        for c in convos
    ]


@router.get("/conversation/{conversation_id}", response_model=ConversationDetail)
async def conversation_detail(conversation_id: str, user=Depends(get_current_user)):
    from server import db
    convo = await store.get_conversation(
        db, conversation_id=conversation_id, user_id=user["id"],
    )
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await store.list_messages(
        db, conversation_id=conversation_id, user_id=user["id"],
    )
    return ConversationDetail(conversation=convo, messages=messages)


@router.delete("/conversation/{conversation_id}")
async def delete_conversation_route(conversation_id: str, user=Depends(get_current_user)):
    from server import db
    ok = await store.delete_conversation(
        db, conversation_id=conversation_id, user_id=user["id"],
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "id": conversation_id}


@router.get("/context/preview")
async def context_preview(node_id: str | None = None, user=Depends(get_current_user)):
    """Slim view of what the mentor sees. Powers a "Mentor knows about you"
    UI card so users understand the personalisation."""
    from server import db
    ctx = await build_context(db, user_id=user["id"], node_id=node_id)
    return public_preview(ctx)
