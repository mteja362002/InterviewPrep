"""Mission Engine V2 — adaptive.

Builds tomorrow's mission from yesterday's feedback (confidence, hints, time),
inserts prerequisite root-cause revisions, and honors company weighting +
target date. Task-level toggling is idempotent.
"""
import hashlib
import random
from datetime import datetime, timezone, timedelta, date as date_cls
from typing import Dict, List, Optional, Tuple

from models import (
    DailyMission, MissionTask, TOPIC_KEYS,
)
from problem_bank import (
    SUBTOPIC_TO_PATTERN, PATTERN_TO_DOMAIN, PATTERN_PREREQUISITES,
    problems_by_pattern,
)
from roadmap import get_roadmap, topic_meta, pattern_for_node
from services.learning_engine.composition import (
    CompositionPlan, MissionConstraints, plan_composition, validate_mission,
)


# --------------------- Content library ---------------------
# The roadmap owns the learning catalog.  Keep this legacy-shaped name because
# routes and the mission builder already consume it, but derive it once from
# the versioned graph rather than maintaining a second, incomplete catalog.
TOPIC_META = topic_meta()

# Weighted readiness formula per company.
# Missing companies default to READINESS_WEIGHTS.
COMPANY_READINESS_WEIGHTS = {
    "google":      {"dsa": 0.45, "hld": 0.20, "lld": 0.10, "java": 0.05, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
    "microsoft":   {"dsa": 0.35, "lld": 0.20, "hld": 0.15, "java": 0.10, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
    "amazon":      {"dsa": 0.40, "lld": 0.20, "hld": 0.15, "java": 0.05, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
    "adobe":       {"dsa": 0.30, "lld": 0.25, "hld": 0.10, "java": 0.15, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
    "atlassian":   {"dsa": 0.30, "lld": 0.25, "hld": 0.20, "java": 0.05, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
    "stripe":      {"dsa": 0.30, "hld": 0.25, "java": 0.15, "lld": 0.10, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
    "uber":        {"dsa": 0.30, "hld": 0.30, "lld": 0.10, "java": 0.05, "operating_systems": 0.07, "dbms": 0.10, "computer_networks": 0.08},
    "phonepe":     {"dsa": 0.30, "hld": 0.25, "lld": 0.15, "java": 0.05, "operating_systems": 0.07, "dbms": 0.10, "computer_networks": 0.08},
    "flipkart":    {"dsa": 0.35, "lld": 0.20, "hld": 0.15, "java": 0.05, "operating_systems": 0.08, "dbms": 0.10, "computer_networks": 0.07},
    "salesforce":  {"dsa": 0.20, "java": 0.25, "lld": 0.20, "hld": 0.10, "operating_systems": 0.08, "dbms": 0.10, "computer_networks": 0.07},
    "oracle":      {"dsa": 0.20, "java": 0.20, "dbms": 0.25, "lld": 0.10, "hld": 0.10, "operating_systems": 0.08, "computer_networks": 0.07},
    "linkedin":    {"dsa": 0.30, "hld": 0.25, "lld": 0.15, "java": 0.10, "operating_systems": 0.07, "dbms": 0.07, "computer_networks": 0.06},
}

DEFAULT_READINESS = {
    "dsa": 0.35, "java": 0.15, "lld": 0.15, "hld": 0.15,
    "operating_systems": 0.0667, "dbms": 0.0667, "computer_networks": 0.0666,
}


# --------------------- Helpers ---------------------

def today_date_str() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _seeded_random(user_id: str, ds: str) -> random.Random:
    h = hashlib.sha256(f"{user_id}:{ds}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _pattern_from_subtopic(sub: str) -> Optional[str]:
    return SUBTOPIC_TO_PATTERN.get(sub)


# Experience-aware difficulty calibration. The roadmap authors each node's
# inherent difficulty once; this maps the learner's self-reported experience
# band to a difficulty ceiling/floor so a Student is never handed a "hard"
# mission and a Senior is never left on "easy" alone — symmetric in both
# directions, unlike a single narrow bump condition.
_EXPERIENCE_DIFFICULTY_CEILING = {
    "student": "medium",
    "0-1": "medium",
    "1-3": "hard",
    "3-5": "hard",
    "5+": "hard",
}
_EXPERIENCE_DIFFICULTY_FLOOR = {
    "student": "easy",
    "0-1": "easy",
    "1-3": "easy",
    "3-5": "medium",
    "5+": "medium",
}
_DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _clamp_difficulty_to_experience(
    difficulty: str, position: str, confidence: Optional[float] = None,
) -> str:
    """Clamp a roadmap node's authored difficulty into the learner's experience band.

    Foundation RC1.2 item 4: difficulty now also reacts to the learner's
    actual confidence on today's node (from the same Learning Engine insight
    already computed by `services/learning_engine/ranking.py` — no second
    confidence signal). Confidence only moves the result *within* the
    existing experience floor/ceiling band — a low-confidence Senior is
    never bumped above their band's floor, and a high-confidence Student is
    never bumped past their band's ceiling ("hard" stays earned, not just
    handed out). `confidence` defaults to None, a strict no-op that leaves
    every existing call site's behavior unchanged.
    """
    ceiling = _EXPERIENCE_DIFFICULTY_CEILING.get(position, "hard")
    floor = _EXPERIENCE_DIFFICULTY_FLOOR.get(position, "easy")
    order = _DIFFICULTY_ORDER
    clamped = difficulty if difficulty in order else "medium"

    if confidence is not None:
        step = 0
        if confidence < 4.0:
            step = -1
        elif confidence >= 8.0:
            step = 1
        if step:
            new_order = max(0, min(2, order[clamped] + step))
            clamped = next(name for name, value in order.items() if value == new_order)

    if order[clamped] > order.get(ceiling, 2):
        clamped = ceiling
    if order[clamped] < order.get(floor, 0):
        clamped = floor
    return clamped


def _roadmap_study_task(node: dict, action: str = "Study") -> MissionTask:
    return MissionTask(
        title=f"{action}: {node.get('label') or node.get('id')}",
        kind="study",
        topic=node.get("track", "dsa"),
        node_id=node.get("id"),
    )


def _find_roadmap_node_by_id(node_id: Optional[str]) -> Optional[dict]:
    if not node_id:
        return None
    return get_roadmap().get(node_id)


def _select_unlocked_roadmap_node(track: str, knowledge_nodes: Optional[dict]) -> Optional[dict]:
    completed = {
        row.get("node_id")
        for row in (knowledge_nodes or {}).values()
        if row.get("node_id")
    }
    unlocked = get_roadmap().get_unlocked_nodes(completed)
    for node in unlocked:
        if node.get("track") == track and node.get("id") not in completed:
            return node
    return None


# --------------------- Legacy topic selection helpers (deprecated) -----
# These functions remain only for backward compatibility and tests.
# Production mission generation should use the Learning Engine recommendation
# pipeline as the canonical source of today's topic selection.

def choose_focus_topic(
    onboarding: dict, knowledge: List[dict], target_companies: List[str], rng: random.Random,
) -> str:
    baseline = onboarding.get("self_assessment", {}) if onboarding else {}
    progress = {kp["topic"]: kp.get("score", 0.0) for kp in knowledge}
    weights = {}
    for t in TOPIC_KEYS:
        base = baseline.get(t, 5) * 10
        score = progress.get(t, base)
        weights[t] = max(0.0, 100.0 - score)
    # Company weighting is sourced from roadmap.company_importance() (0-5 per
    # track) instead of a second hardcoded bias table.
    roadmap = get_roadmap()
    for c in target_companies or []:
        company_id = str(c).lower()
        for t in TOPIC_KEYS:
            importance = roadmap.company_importance(t, company_id)
            if importance:
                weights[t] = weights.get(t, 0) * (1 + importance / 10.0)
    total = sum(weights.values()) or 1.0
    r = rng.random() * total
    acc = 0.0
    for t in TOPIC_KEYS:
        acc += weights[t]
        if r <= acc:
            return t
    return TOPIC_KEYS[0]


# --------------------- Adaptive analysis ---------------------

def analyze_recent_feedback(feedbacks: List[dict]) -> dict:
    """Summarize signals from recent feedback (last 24-48 hours worth).

    Returns:
      { avg_confidence, hint_ratio, timeout_ratio, weak_patterns [set], strong_patterns [set], failed_patterns [set] }
    """
    if not feedbacks:
        return {"avg_confidence": None, "hint_ratio": 0, "timeout_ratio": 0,
                "weak_patterns": set(), "strong_patterns": set(), "failed_patterns": set()}

    total = len(feedbacks)
    confs = [f["confidence"] for f in feedbacks]
    avg_conf = sum(confs) / total
    hints = sum(1 for f in feedbacks if f["solved_status"] in ("one_hint", "multi_hints"))
    fails = sum(1 for f in feedbacks if f["solved_status"] == "could_not_solve")

    weak, strong, failed = set(), set(), set()
    for f in feedbacks:
        low = f["confidence"] <= 4 or f["solved_status"] in ("multi_hints", "could_not_solve")
        high = f["confidence"] >= 8 and f["solved_status"] == "without_hints"
        if f["solved_status"] == "could_not_solve":
            failed.add(f["pattern"])
        if low:
            weak.add(f["pattern"])
        if high:
            strong.add(f["pattern"])

    return {
        "avg_confidence": avg_conf,
        "hint_ratio": hints / total,
        "timeout_ratio": fails / total,
        "weak_patterns": weak,
        "strong_patterns": strong,
        "failed_patterns": failed,
    }


def determine_mode(analysis: dict) -> str:
    """Return one of: 'revise', 'advance', 'continue'."""
    if not analysis["avg_confidence"]:
        return "continue"
    if analysis["failed_patterns"] or analysis["avg_confidence"] < 5 or analysis["hint_ratio"] > 0.5:
        return "revise"
    if analysis["avg_confidence"] >= 8 and analysis["hint_ratio"] < 0.2:
        return "advance"
    return "continue"


def prerequisite_revisions_for(pattern: str) -> List[Tuple[str, str]]:
    """Return list of (domain, subtopic) prerequisites for a pattern."""
    return PATTERN_PREREQUISITES.get(pattern, [])


def get_candidate_topics(topic: str) -> List[dict]:
    """Return roadmap-backed learning topics eligible within one track."""
    roadmap = get_roadmap()
    track = roadmap.get(topic)
    if not track:
        return []

    candidates = []
    for module in roadmap.children(track["id"]):
        candidates.extend(
            node for node in roadmap.children(module["id"])
            if node.get("type") == "topic"
        )
    return candidates


def rank_candidate_topics(
    candidates: List[dict],
    knowledge_nodes: Dict[str, dict],
    target_companies: List[str],
    rng: random.Random,
) -> dict:
    """Return the best learner-aware candidate, using RNG for exact ties."""
    roadmap = get_roadmap()

    def ranking_key(candidate: dict) -> tuple:
        progress = knowledge_nodes.get(candidate["id"], {})
        status = progress.get("status", "not_started")
        company_importance = sum(
            roadmap.company_importance(candidate["id"], str(company).lower())
            for company in target_companies
        )
        return (
            candidate.get("status") != "locked",
            -float(progress.get("confidence", 0.0)),
            float(progress.get("weakness_score", 0.0)),
            status not in ("completed", "mastered"),
            company_importance,
            -float(progress.get("mastery_percentage", 0.0)),
        )

    best_key = max(ranking_key(candidate) for candidate in candidates)
    tied_candidates = [
        candidate for candidate in candidates if ranking_key(candidate) == best_key
    ]
    # Phase 3C.1 freeze: deterministic tie-break (no randomness in selection).
    return sorted(tied_candidates, key=lambda c: str(c.get("id")))[0]


def select_primary_topic(
    onboarding: dict,
    knowledge: List[dict],
    target_companies: List[str],
    analysis: dict,
    mode: str,
    rng: random.Random,
    knowledge_nodes: Optional[Dict[str, dict]] = None,
) -> Tuple[str, str, str]:
    """Deprecated compatibility fallback.

    Select the primary mission track, topic label, and base difficulty.

    This function is retained for legacy callers and should not be used by
    production mission generation once the Learning Engine is fully canonical.
    """
    if mode == "revise" and analysis["weak_patterns"]:
        weak_pattern = sorted(analysis["weak_patterns"])[0]
        domain, subtopic = PATTERN_TO_DOMAIN.get(weak_pattern, ("dsa", "Arrays"))
        return domain, subtopic, "easy"

    if mode == "advance" and analysis["strong_patterns"]:
        # Move to next challenging DSA area. Phase 3C.1 freeze: deterministic
        # (no random topic selection); first by a fixed priority order.
        pattern_choice = "dp"
        domain, subtopic = PATTERN_TO_DOMAIN.get(pattern_choice, ("dsa", "Dynamic Programming"))
        return domain, subtopic, "hard"

    focus_topic = choose_focus_topic(onboarding, knowledge, target_companies, rng)
    candidate = rank_candidate_topics(
        get_candidate_topics(focus_topic),
        knowledge_nodes or {},
        target_companies,
        rng,
    )
    return focus_topic, candidate["label"], candidate.get("difficulty", "medium")


# --------------------- Mission builder V2 ---------------------

def build_mission_for_user(
    user_id: str,
    onboarding: dict,
    knowledge: List[dict],
    revisions_due: List[dict],
    recent_feedback: Optional[List[dict]] = None,
    extra_practice_count_yesterday: int = 0,
    ds: Optional[str] = None,
    knowledge_nodes: Optional[Dict[str, dict]] = None,
    learning_recommendation: Optional[dict] = None,
    pacing_state: Optional[dict] = None,
    composition_plan: Optional[CompositionPlan] = None,
) -> tuple[DailyMission, dict]:
    """Return (mission, adjustment_meta). adjustment_meta describes adaptive decisions.

    The primary mission topic is supplied via the canonical Learning Engine
    recommendation DTO. This function composes the mission document and tasks,
    but does not independently choose today's roadmap topic when a recommendation
    is provided.

    `pacing_state` (services/learning_engine/pacing.py) is optional and
    defaults to a no-op ("standard"/urgency 0.0) — existing callers that
    don't pass it get the exact same mission shape as before. When urgency is
    high, study hours still cap the daily workload; only how densely that
    same time budget is used changes.

    RC1.3.2A ``composition_plan`` (services/learning_engine/composition.py)
    is optional. When None, the historical inline heuristics run — the
    function is byte-identical to before this parameter existed. When
    provided, it drives practice_count, revision cap, supporting/core
    inclusion, and the mission is validated against the plan; the
    ``adjustment`` return dict carries the validator's result so callers
    can persist it into ``mission_adjustments`` for audit.
    """
    ds = ds or today_date_str()
    rng = _seeded_random(user_id, ds)
    pacing_state = pacing_state or {}
    pacing_mode = pacing_state.get("pacing_mode", "standard")
    urgency = float(pacing_state.get("urgency", 0.0))

    target_companies = onboarding.get("target_companies", []) if onboarding else []
    daily_hours = float(onboarding.get("daily_study_hours", 2)) if onboarding else 2.0
    duration_minutes = int(round(daily_hours * 60))

    # Extra practice yesterday → increase intensity today.
    if extra_practice_count_yesterday >= 2:
        daily_hours = min(daily_hours + 0.5, 8.0)
        duration_minutes = int(round(daily_hours * 60))

    analysis = analyze_recent_feedback(recent_feedback or [])
    mode = determine_mode(analysis)

    if learning_recommendation is not None:
        focus_topic = learning_recommendation.get("track") or "dsa"
        subtopic = learning_recommendation.get("label") or learning_recommendation.get("subtopic") or ""
        base_difficulty = learning_recommendation.get("difficulty") or "medium"
        primary_node_id = learning_recommendation.get("node_id")
    else:
        # Legacy compatibility fallback only.
        focus_topic, subtopic, base_difficulty = select_primary_topic(
            onboarding, knowledge, target_companies, analysis, mode, rng, knowledge_nodes,
        )
        primary_node_id = None

    meta = TOPIC_META[focus_topic]

    position = (onboarding or {}).get("current_position", "0-1")
    node_confidence = None
    if learning_recommendation is not None:
        node_confidence = (learning_recommendation.get("insight") or {}).get("confidence")
    base_difficulty = _clamp_difficulty_to_experience(base_difficulty, position, node_confidence)

    # ---- Composition plan (RC1.3.2A) --------------------------------------
    # Prefer the caller-supplied plan (planner.py orchestrator computes it
    # with the same signals). Fall back to computing it inline so this
    # function remains callable in isolation (tests, legacy callers).
    if composition_plan is None:
        composition_plan = plan_composition(
            pacing_state=pacing_state,
            position=position,
            revisions_due_count=len(revisions_due or []),
            primary_track=focus_topic,
            primary_confidence=node_confidence,
            extra_practice_yesterday=extra_practice_count_yesterday,
        )
    practice_count = composition_plan.practice_count

    tasks: List[MissionTask] = []
    inserted_prereqs: List[str] = []
    detected_weaknesses: List[str] = []

    # -------- Root cause: prerequisite revisions (only in revise mode) --------
    if mode == "revise" and analysis["weak_patterns"]:
        seen = set()
        for weak_p in sorted(analysis["weak_patterns"]):  # deterministic order
            for (pre_domain, pre_sub) in prerequisite_revisions_for(weak_p):
                key = (pre_domain, pre_sub)
                if key in seen:
                    continue
                seen.add(key)
                tasks.append(MissionTask(
                    title=f"Revise: {pre_sub} ({TOPIC_META[pre_domain]['label']})",
                    kind="revise",
                    topic=pre_domain,
                ))
                inserted_prereqs.append(f"{pre_domain}::{pre_sub}")
            detected_weaknesses.append(weak_p)
        # cap at 2 prereqs
        if len(tasks) > 2:
            tasks = tasks[:2]

    # -------- Primary task on focus topic --------
    # `pattern` is authored once per topic in the roadmap (e.g. sliding_window),
    # not duplicated on every leaf learning node — so a leaf-level recommendation
    # (the norm for DSA, e.g. "Minimum Window Substring") must resolve its pattern
    # via the roadmap graph. Fall back to the legacy label lookup only when no
    # roadmap node id is available (e.g. the deprecated select_primary_topic path).
    pattern = pattern_for_node(primary_node_id) if primary_node_id else None
    if not pattern:
        pattern = _pattern_from_subtopic(subtopic)
    if focus_topic == "dsa" and pattern:
        # Real practice: coding problems attached (populated by route caller)
        tasks.append(MissionTask(
            title=f"Solve {practice_count} {subtopic} problems",
            kind="practice",
            topic=focus_topic,
            pattern=pattern,
            problem_count=practice_count,
            node_id=primary_node_id,
        ))
    elif focus_topic in ("java", "lld", "hld"):
        tasks.append(MissionTask(
            title=f"Work through: {subtopic}",
            kind="practice",
            topic=focus_topic,
            node_id=primary_node_id,
        ))
    else:
        tasks.append(MissionTask(
            title=f"Deep-dive: {subtopic}",
            kind="study",
            topic=focus_topic,
            node_id=primary_node_id,
        ))

    # Supporting study task
    support_node = None
    support_topic = None
    support_meta = None
    if learning_recommendation is not None:
        support_node = _find_roadmap_node_by_id(learning_recommendation.get("support_node"))
        support_topic = learning_recommendation.get("support_track")
        # TOPIC_META (roadmap.topic_meta()) is keyed by every real roadmap
        # track — dsa/java/lld/hld/os/dbms/cn plus behavioral/projects/resume
        # and any future track. TOPIC_KEYS is a legacy 7-track subset used only
        # for onboarding self-assessment sliders; validating against it here
        # silently dropped the support recommendation for any other track.
        if support_topic not in TOPIC_META:
            support_topic = learning_recommendation.get("support_topic")
            if support_topic not in TOPIC_META:
                support_topic = None

    if support_topic in TOPIC_META:
        support_meta = TOPIC_META[support_topic]

    if support_node is None and support_topic is not None:
        support_node = _select_unlocked_roadmap_node(support_topic, knowledge_nodes)

    if support_node is not None:
        tasks.append(_roadmap_study_task(support_node, action="Study"))
    elif support_topic is None or support_meta is None:
        # Compatibility safeguard: only use legacy topic meta when the support
        # recommendation payload is invalid or the track is unknown. Phase 3C.1
        # freeze: this substitution is now DETERMINISTIC (no random unrelated
        # topic) — first eligible track + first subtopic by stable ordering.
        support_pool = sorted(t for t in TOPIC_META if t != focus_topic)
        support_topic = support_pool[0]
        support_meta = TOPIC_META[support_topic]
        support_sub = sorted(support_meta["subtopics"], key=lambda s: s[0])[0][0]
        tasks.append(MissionTask(
            title=f"Study {support_meta['label']} · {support_sub}",
            kind="study",
            topic=support_topic,
        ))
    else:
        # Valid roadmap-backed support track exists but no unlocked roadmap node is
        # currently available. Do not fall back to legacy TOPIC_META in normal flow.
        pass

    if daily_hours >= 3:
        core_node = _find_roadmap_node_by_id(learning_recommendation.get("core_node") if learning_recommendation else None)
        if core_node is None:
            for core_track in ("operating_systems", "dbms", "computer_networks"):
                core_node = _select_unlocked_roadmap_node(core_track, knowledge_nodes)
                if core_node is not None:
                    break
        if core_node is not None:
            tasks.append(_roadmap_study_task(core_node, action="Read"))
        else:
            # No eligible unlocked roadmap node exists for core tracks. Do not
            # revert to legacy TOPIC_META when roadmap-backed core selection fails.
            pass

    # Revision tasks (from spaced-repetition queue). Revision cap is now
    # sourced from the composition plan (which already applied the
    # critical-mode +1 slot) rather than recomputed here.
    revision_cap = composition_plan.revision_slots if composition_plan else (
        3 if pacing_mode == "critical" else 2
    )
    revision_task_ids: List[str] = []
    for rev in revisions_due[:revision_cap]:
        rt = MissionTask(
            title=f"Revise: {rev['task_title']}",
            kind="revise",
            topic=rev["topic"],
            node_id=rev.get("node_id"),
        )
        tasks.append(rt)
        revision_task_ids.append(rt.id)

    if mode == "revise":
        title = f"Consolidate {subtopic}"
        objective = (
            f"Yesterday's signals showed weak spots — reinforce fundamentals of "
            f"{subtopic} and its prerequisites before advancing."
        )
    elif mode == "advance":
        title = f"Advance: {subtopic}"
        objective = (
            f"Strong performance yesterday. Push into {subtopic} at hard difficulty "
            f"to build interview-grade depth."
        )
    else:
        title = f"Focus on {subtopic}"
        objective = (
            f"Strengthen your {meta['label']} baseline via {subtopic}. "
            f"Consolidate with a supporting {support_meta['label']} concept."
        )

    mission = DailyMission(
        user_id=user_id,
        date=ds,
        title=title,
        focus_area=f"{meta['label']} · {subtopic}",
        focus_topic=focus_topic,
        difficulty=base_difficulty,
        estimated_duration_minutes=duration_minutes,
        learning_objective=objective,
        tasks=tasks,
        revision_task_ids=revision_task_ids,
        recommendation_insight=learning_recommendation.get("insight") if learning_recommendation else None,
    )

    # ---- Internal validation (RC1.3.2A) -----------------------------------
    # Never raises. If severity == 'regenerate' the CALLER
    # (routes_missions._generate_today_mission) is responsible for retrying
    # with a different primary node — we surface the hint via
    # ``adjustment["validation"]`` and let the caller decide.
    task_dicts = [t.model_dump() if hasattr(t, "model_dump") else dict(t) for t in tasks]
    validation = validate_mission(task_dicts, composition_plan)

    # Fold composition + validation into the recommendation insight so
    # every downstream consumer (Mission Control, AI Mentor) can render
    # them without another network round-trip.
    if mission.recommendation_insight is not None:
        mission.recommendation_insight.setdefault(
            "composition", composition_plan.to_dict()
        )
        mission.recommendation_insight.setdefault(
            "validation", validation.to_dict()
        )

    adjustment = {
        "mode": mode,
        "reason": _mode_reason(mode, analysis, extra_practice_count_yesterday),
        "detected_weaknesses": detected_weaknesses,
        "inserted_prerequisites": inserted_prereqs,
        "advance": mode == "advance",
        "pacing_mode": pacing_mode,
        "urgency": urgency,
        "composition": composition_plan.to_dict(),
        "validation": validation.to_dict(),
    }
    return mission, adjustment


def _mode_reason(mode: str, analysis: dict, extra: int) -> str:
    if mode == "revise":
        return (
            f"Detected weak signals (avg confidence "
            f"{round(analysis['avg_confidence'] or 0, 1)}, "
            f"hint ratio {int(analysis['hint_ratio']*100)}%). "
            f"Inserted prerequisite revisions before advancing."
        )
    if mode == "advance":
        return (
            f"Strong performance yesterday (avg confidence "
            f"{round(analysis['avg_confidence'] or 0, 1)}). "
            f"Progressing into harder patterns."
        )
    if extra >= 2:
        return "Extra practice yesterday — extended today's mission."
    return "Standard progression from baseline."


# --------------------- Spaced repetition ---------------------
#
# Canonical spaced-repetition math (schedule_next_revision, first_revision_date,
# REVISION_STAGES_DAYS) now lives in services/revision_engine.py — the single
# Revision Engine consumed by Mission Engine, the Knowledge Base, and AI
# Mentor. See that module for implementation.


# --------------------- Interview readiness ---------------------

def compute_readiness(knowledge: List[dict], onboarding: dict) -> float:
    baseline = (onboarding or {}).get("self_assessment", {})
    by_topic = {kp["topic"]: kp.get("score", 0.0) for kp in knowledge}
    total = 0.0
    for t, w in DEFAULT_READINESS.items():
        score = by_topic.get(t)
        if score is None:
            score = baseline.get(t, 5) * 10
        total += w * score
    return round(min(max(total, 0.0), 100.0), 1)


def compute_company_readiness(company_id: str, knowledge: List[dict], onboarding: dict) -> float:
    weights = COMPANY_READINESS_WEIGHTS.get(company_id, DEFAULT_READINESS)
    baseline = (onboarding or {}).get("self_assessment", {})
    by_topic = {kp["topic"]: kp.get("score", 0.0) for kp in knowledge}
    total = 0.0
    for t, w in weights.items():
        score = by_topic.get(t)
        if score is None:
            score = baseline.get(t, 5) * 10
        total += w * score
    return round(min(max(total, 0.0), 100.0), 1)



# --------------------- Knowledge gain ---------------------

def apply_knowledge_gain(current_score: float, difficulty: str, kind: str) -> float:
    base = {"easy": 1.2, "medium": 2.0, "hard": 2.8}[difficulty]
    mult = {"practice": 1.0, "study": 0.6, "revise": 1.4}[kind]
    return round(min(current_score + base * mult, 100.0), 2)


def apply_feedback_gain(current_score: float, confidence: int, solved_status: str) -> float:
    """Bigger gains when solved cleanly; smaller when hints were needed."""
    base = 3.5
    status_mult = {"without_hints": 1.0, "one_hint": 0.7,
                   "multi_hints": 0.35, "could_not_solve": 0.1}[solved_status]
    conf_mult = 0.5 + (confidence / 10.0)  # 0.6 → 1.5
    delta = base * status_mult * conf_mult
    return round(min(current_score + delta, 100.0), 2)
