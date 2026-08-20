"""PrepOS FastAPI backend entrypoint."""
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
import logging
import certifi
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from auth_utils import hash_password, verify_password
from routes_auth import router as auth_router
from routes_user import router as user_router
from routes_missions import router as missions_router
from routes_roadmap import router as roadmap_router
from routes_leetcode_catalog import router as leetcode_catalog_router
from ai_mentor.mentor_routes import router as mentor_router
from routes_companies import router as companies_router

# ------------------------- DB -------------------------
mongo_url = os.environ["MONGO_URL"]
# Only enforce TLS CA when talking to a TLS-enabled cluster (Atlas / mongodb+srv
# style). Local development mongo (no TLS) trips over an unused tlsCAFile.
_low = mongo_url.lower()
_needs_tls = mongo_url.startswith("mongodb+srv://") or "tls=true" in _low or "ssl=true" in _low
_client_kwargs = {"tz_aware": True}
if _needs_tls:
    _client_kwargs["tlsCAFile"] = certifi.where()
client = AsyncIOMotorClient(mongo_url, **_client_kwargs)
db = client[os.environ["DB_NAME"]]

# ------------------------- App -------------------------
app = FastAPI(title="PrepOS API", version="0.1.0")

# CORS — must allow credentials for cookie-based auth. Cannot use wildcard with credentials.
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
cors_env = os.environ.get("CORS_ORIGINS", frontend_url)
if cors_env == "*":
    origins = [frontend_url]
else:
    origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------- Health -------------------------
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "PrepOS API", "version": "0.1.0"}


@api_router.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


app.include_router(api_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(missions_router)
app.include_router(roadmap_router)
app.include_router(leetcode_catalog_router)
app.include_router(mentor_router)
app.include_router(companies_router)

# ------------------------- Startup -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("prepos")


@app.on_event("startup")
async def on_startup():
    # Indexes
    await db.users.create_index("email", unique=True)
    await db.settings.create_index("user_id", unique=True)
    await db.onboarding.create_index("user_id", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index(
        "expires_at", expireAfterSeconds=0
    )
    # Mission engine indexes
    await db.daily_missions.create_index([("user_id", 1), ("date", -1)])
    await db.daily_missions.create_index([("user_id", 1), ("date", 1)], unique=True)
    await db.knowledge_progress.create_index([("user_id", 1), ("topic", 1)], unique=True)
    await db.study_streaks.create_index("user_id", unique=True)
    await db.revisions.create_index([("user_id", 1), ("next_review_date", 1)])
    await db.activity_events.create_index([("user_id", 1), ("ts", -1)])
    # V2 adaptive engine indexes
    await db.problem_assignments.create_index([("user_id", 1), ("mission_id", 1)])
    await db.problem_assignments.create_index([("user_id", 1), ("pattern", 1)])
    await db.problem_feedback.create_index([("user_id", 1), ("submitted_at", -1)])
    await db.problem_feedback.create_index([("user_id", 1), ("pattern", 1)])
    await db.mission_adjustments.create_index([("user_id", 1), ("for_date", -1)])
    await db.weaknesses.create_index([("user_id", 1), ("pattern", 1)])
    # Roadmap knowledge graph
    await db.knowledge_nodes.create_index(
        [("user_id", 1), ("roadmap_version", 1), ("node_id", 1)],
        unique=True,
    )
    # AI Mentor
    await db.mentor_conversations.create_index([("user_id", 1), ("updated_at", -1)])
    await db.mentor_conversations.create_index("id", unique=True)
    await db.mentor_messages.create_index([("conversation_id", 1), ("created_at", 1)])
    await db.mentor_messages.create_index([("user_id", 1), ("created_at", -1)])
    logger.info("MongoDB indexes ensured.")

    # ---- Roadmap migration: backfill knowledge_nodes from legacy tables ----
    from roadmap import get_roadmap, CURRENT_VERSION
    from problem_bank import problem_by_id
    from services.roadmap_progress import (
        RoadmapNodeProgressRepository,
        RoadmapProgressInitializer,
    )
    roadmap = get_roadmap(CURRENT_VERSION)
    roadmap_progress_repository = RoadmapNodeProgressRepository(db)
    await roadmap_progress_repository.ensure_indexes()
    roadmap_progress_initializer = RoadmapProgressInitializer(
        roadmap_progress_repository, roadmap,
    )

    async for u in db.users.find({}, {"id": 1, "roadmap_version": 1}):
        uid = u["id"]
        if not u.get("roadmap_version"):
            await db.users.update_one({"id": uid}, {"$set": {"roadmap_version": CURRENT_VERSION}})

        # Backfill track-level knowledge_nodes from existing knowledge_progress
        kp_cur = db.knowledge_progress.find({"user_id": uid}, {"_id": 0})
        async for kp in kp_cur:
            track_id = kp["topic"]  # legacy topic string == track id
            if not roadmap.get(track_id):
                continue
            score = float(kp.get("score", 0))
            conf = min(10.0, score / 10.0)
            existing = await db.knowledge_nodes.find_one(
                {"user_id": uid, "roadmap_version": CURRENT_VERSION, "node_id": track_id},
                {"_id": 0},
            )
            if existing:
                # Only refresh derived fields — preserve any user notes
                await db.knowledge_nodes.update_one(
                    {"user_id": uid, "roadmap_version": CURRENT_VERSION, "node_id": track_id},
                    {"$set": {
                        "confidence": conf,
                        "mastery_percentage": score,
                        "weakness_score": max(0.0, 100 - score),
                        "status": "in_progress" if score > 0 else "available",
                        "revision_bucket": "green" if conf >= 7 else "yellow" if conf >= 4 else "red",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
            else:
                await db.knowledge_nodes.insert_one({
                    "user_id": uid, "roadmap_version": CURRENT_VERSION,
                    "node_id": track_id,
                    "confidence": conf, "mastery_percentage": score,
                    "weakness_score": max(0.0, 100 - score),
                    "status": "in_progress" if score > 0 else "available",
                    "revision_bucket": "green" if conf >= 7 else "yellow" if conf >= 4 else "red",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "notes": None,
                })

        # Backfill pattern-level knowledge_nodes from problem_feedback
        fb_cur = db.problem_feedback.aggregate([
            {"$match": {"user_id": uid}},
            {"$group": {
                "_id": "$pattern",
                "avg_conf": {"$avg": "$confidence"},
                "count": {"$sum": 1},
            }},
        ])
        async for row in fb_cur:
            pat = row["_id"]
            pattern_nodes = roadmap.by_pattern(pat)
            if not pattern_nodes:
                continue
            nid = pattern_nodes[0]["id"]
            conf = float(row.get("avg_conf") or 0)
            mastery = min(100.0, row["count"] * 12.5)
            weak = max(0.0, 100 - conf * 10)
            existing = await db.knowledge_nodes.find_one(
                {"user_id": uid, "roadmap_version": CURRENT_VERSION, "node_id": nid},
                {"_id": 0},
            )
            if existing:
                await db.knowledge_nodes.update_one(
                    {"user_id": uid, "roadmap_version": CURRENT_VERSION, "node_id": nid},
                    {"$set": {
                        "confidence": round(conf, 2),
                        "mastery_percentage": round(mastery, 2),
                        "weakness_score": round(weak, 2),
                        "status": "in_progress",
                        "revision_bucket": "green" if conf >= 7 else "yellow" if conf >= 4 else "red",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    }},
                )
            else:
                await db.knowledge_nodes.insert_one({
                    "user_id": uid, "roadmap_version": CURRENT_VERSION,
                    "node_id": nid,
                    "confidence": round(conf, 2),
                    "mastery_percentage": round(mastery, 2),
                    "weakness_score": round(weak, 2),
                    "status": "in_progress",
                    "revision_bucket": "green" if conf >= 7 else "yellow" if conf >= 4 else "red",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "notes": None,
                })

        await roadmap_progress_initializer.initialize_for_user(uid)
    logger.info("Roadmap knowledge_nodes backfill complete.")

    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@prepos.io")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        import uuid
        admin_id = str(uuid.uuid4())
        await db.users.insert_one({
            "id": admin_id,
            "email": admin_email,
            "name": "PrepOS Admin",
            "password_hash": hash_password(admin_password),
            "role": "admin",
            "avatar_url": None,
            "onboarding_completed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Seeded admin user: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        admin_id = existing["id"]
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )
        logger.info(f"Updated admin password hash for {admin_email}")
    else:
        admin_id = existing["id"]

    await roadmap_progress_initializer.initialize_for_user(admin_id)


@app.on_event("shutdown")
async def on_shutdown():
    client.close()
