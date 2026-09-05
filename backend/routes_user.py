"""Onboarding & Profile & Settings routes."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from models import (
    OnboardingPayload, OnboardingRecord,
    ProfileUpdate, UserPublic,
    UserSettings, SettingsUpdate,
)
from roadmap import get_roadmap, CURRENT_VERSION
from services.progress_engine import seed_knowledge_nodes_from_self_assessment

router = APIRouter(prefix="/api", tags=["user"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _estimate_prep_days(payload: OnboardingPayload) -> int:
    """Simple estimation for now. Real logic comes in future phase."""
    avg_skill = sum([
        payload.self_assessment.dsa,
        payload.self_assessment.java,
        payload.self_assessment.lld,
        payload.self_assessment.hld,
        payload.self_assessment.operating_systems,
        payload.self_assessment.dbms,
        payload.self_assessment.computer_networks,
    ]) / 7.0
    # Lower skill = more days. Range roughly 45-180.
    base = 180 - (avg_skill * 12)  # 10 -> 60 days, 1 -> 168 days
    hours_factor = 4.0 / max(payload.daily_study_hours, 1)  # more hours = fewer days
    return max(30, int(base * hours_factor / 2))


# ============ Onboarding ============

@router.post("/onboarding", response_model=OnboardingRecord)
async def submit_onboarding(payload: OnboardingPayload, user=Depends(get_current_user)):
    from server import db
    estimated = _estimate_prep_days(payload)
    record = OnboardingRecord(
        user_id=user["id"],
        target_companies=payload.target_companies,
        current_position=payload.current_position,
        daily_study_hours=payload.daily_study_hours,
        self_assessment=payload.self_assessment,
        interview_target_date=payload.interview_target_date,
        estimated_prep_days=estimated,
    )
    # Upsert
    existing = await db.onboarding.find_one({"user_id": user["id"]})
    doc = record.model_dump()
    if existing:
        doc["id"] = existing["id"]
        doc["created_at"] = existing["created_at"]
        doc["updated_at"] = _now_iso()
        await db.onboarding.replace_one({"user_id": user["id"]}, doc)
    else:
        await db.onboarding.insert_one(doc)

    await db.users.update_one(
        {"id": user["id"]}, {"$set": {"onboarding_completed": True}}
    )
    from services.roadmap_progress import initialize_roadmap_progress_for_user
    await initialize_roadmap_progress_for_user(db, user["id"])
    # Canonical planner input: seed `knowledge_nodes` (not `roadmap_node_progress`)
    # so the Learning Engine ranks tracks per this user's self-assessment from day one.
    await seed_knowledge_nodes_from_self_assessment(
        db, user["id"], payload.self_assessment.model_dump(), get_roadmap(CURRENT_VERSION),
    )
    return OnboardingRecord(**doc)


@router.get("/onboarding", response_model=OnboardingRecord | None)
async def get_onboarding(user=Depends(get_current_user)):
    from server import db
    doc = await db.onboarding.find_one({"user_id": user["id"]})
    if not doc:
        return None
    return OnboardingRecord(**_clean(doc))


# ============ Profile ============

@router.get("/profile", response_model=UserPublic)
async def get_profile(user=Depends(get_current_user)):
    return user


@router.patch("/profile", response_model=UserPublic)
async def update_profile(payload: ProfileUpdate, user=Depends(get_current_user)):
    from server import db
    # exclude_unset (not exclude_none) so a field explicitly sent as null
    # (e.g. avatar_url: null to remove the profile picture) is still applied,
    # while fields simply omitted from the request are left untouched.
    updates = payload.model_dump(exclude_unset=True)
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        from models import ActivityEvent
        ev = ActivityEvent(
            user_id=user["id"], kind="profile_updated",
            title="Profile updated",
            description=", ".join(updates.keys()),
        )
        await db.activity_events.insert_one(ev.model_dump())
    updated = await db.users.find_one({"id": user["id"]})
    updated.pop("_id", None)
    updated.pop("password_hash", None)
    return updated


# ============ Settings ============

@router.get("/settings", response_model=UserSettings)
async def get_settings(user=Depends(get_current_user)):
    from server import db
    doc = await db.settings.find_one({"user_id": user["id"]})
    if not doc:
        # Create default
        settings = UserSettings(user_id=user["id"])
        await db.settings.insert_one(settings.model_dump())
        return settings
    return UserSettings(**_clean(doc))


@router.patch("/settings", response_model=UserSettings)
async def update_settings(payload: SettingsUpdate, user=Depends(get_current_user)):
    from server import db
    updates = payload.model_dump(exclude_none=True)
    # ai_config is no longer part of SettingsUpdate (AI Gateway owns
    # provider selection).  Old clients may still send it — Pydantic
    # silently drops unknown fields, but we also explicitly strip it
    # as a defence-in-depth measure before writing to MongoDB.
    updates.pop("ai_config", None)
    if updates:
        updates["updated_at"] = _now_iso()
        await db.settings.update_one(
            {"user_id": user["id"]}, {"$set": updates}, upsert=True
        )
        # Activity log
        from models import ActivityEvent
        ev = ActivityEvent(
            user_id=user["id"], kind="settings_changed",
            title="Settings updated",
            description=", ".join(updates.keys()),
        )
        await db.activity_events.insert_one(ev.model_dump())
    doc = await db.settings.find_one({"user_id": user["id"]})
    return UserSettings(**_clean(doc))
