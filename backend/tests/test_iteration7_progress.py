"""Iteration 7 tests — new roadmap tracks + progress endpoints."""
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prep-foundation.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    email = f"TEST_iter7_{uuid.uuid4().hex[:8]}@prepos.io"
    pwd = "Test@1234"
    r = s.post(f"{API}/auth/register", json={"email": email, "password": pwd, "name": "Iter7 Tester"})
    assert r.status_code in (200, 201), r.text
    # Login sets httpOnly cookies
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pwd})
    assert r.status_code == 200, r.text
    # Complete onboarding
    payload = {
        "current_position": "sde-1",
        "target_companies": ["google"],
        "daily_study_hours": 2,
        "interview_target_date": "2026-12-01",
        "self_assessment": {"dsa": 5, "java": 5, "lld": 5, "hld": 5,
                             "os": 4, "dbms": 4, "cn": 4},
    }
    r = s.post(f"{API}/onboarding", json=payload)
    assert r.status_code in (200, 201), r.text
    return s


# ---------- Roadmap shape ----------

def test_roadmap_tracks_10_and_companies_14(client):
    r = client.get(f"{API}/roadmap")
    assert r.status_code == 200
    data = r.json()
    ids = {t["id"] for t in data["tracks"]}
    expected = {"dsa", "java", "lld", "hld", "operating_systems", "dbms",
                "computer_networks", "projects", "behavioral", "resume"}
    assert expected.issubset(ids), f"missing tracks: {expected - ids}"
    assert len(data["tracks"]) == 10
    assert len(data["companies"]) == 14


def test_roadmap_tree_yields_1000_unique_nodes(client):
    r = client.get(f"{API}/roadmap")
    data = r.json()
    seen = set()

    def walk(n):
        seen.add(n["id"])
        for c in n.get("children") or []:
            walk(c)
    for t in data["tracks"]:
        walk(t)
    assert len(seen) >= 1000, f"only {len(seen)} nodes"


NEW_IDS = [
    "projects.build.url_shortener", "projects.build.chat_app",
    "projects.showcase.readme", "projects.deploy.ci_cd",
    "behavioral.framework.star", "behavioral.stories.leadership",
    "behavioral.stories.conflict", "behavioral.values.amazon_lp",
    "behavioral.negotiation.scripts",
    "resume.craft.format", "resume.craft.action_verbs",
    "resume.craft.ats", "resume.linkedin.headline",
    "resume.cover.letter", "resume.cover.cold_outreach",
]

@pytest.mark.parametrize("node_id", NEW_IDS)
def test_new_nodes_resolve(client, node_id):
    r = client.get(f"{API}/roadmap/nodes/{node_id}")
    assert r.status_code == 200, f"{node_id} => {r.status_code} {r.text[:200]}"


# ---------- Summary ----------

def test_summary_fresh_user(client):
    r = client.get(f"{API}/roadmap/summary")
    assert r.status_code == 200
    data = r.json()
    assert len(data["tracks"]) == 10
    for t in data["tracks"]:
        assert t["total_topics"] > 0
    assert data["overall"]["readiness"] == 0
    assert data["counts"]["revision_due"] == 0
    assert data["counts"]["bookmarked"] == 0
    assert data["counts"]["favorite"] == 0
    assert data["today"]["completed_count"] == 0


# ---------- Status endpoint ----------

def test_status_completed_stamps_dates(client):
    nid = "dsa.foundations.arrays.kadane"
    r = client.post(f"{API}/roadmap/nodes/{nid}/status", json={"status": "completed"})
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    r = client.get(f"{API}/roadmap/nodes/{nid}")
    assert r.status_code == 200
    prog = r.json()["node"]["progress"]
    assert prog["status"] == "completed"
    assert prog["completion_date"]
    assert prog["next_revision"]
    assert prog["mastery_percentage"] == 80


def test_status_invalid_returns_422(client):
    r = client.post(f"{API}/roadmap/nodes/dsa.foundations.arrays.kadane/status",
                    json={"status": "garbage"})
    assert r.status_code == 422


def test_status_unknown_node_returns_404(client):
    r = client.post(f"{API}/roadmap/nodes/notavalidid/status", json={"status": "completed"})
    assert r.status_code == 404


# ---------- Bookmark / Favorite ----------

def test_bookmark_toggle(client):
    nid = "dsa.foundations.arrays.traversal"
    r1 = client.post(f"{API}/roadmap/nodes/{nid}/bookmark")
    assert r1.status_code == 200
    v1 = r1.json()["bookmarked"]
    r2 = client.post(f"{API}/roadmap/nodes/{nid}/bookmark")
    v2 = r2.json()["bookmarked"]
    assert v1 != v2
    # Persistence
    r3 = client.get(f"{API}/roadmap/nodes/{nid}")
    assert r3.json()["node"]["progress"]["bookmarked"] == v2


def test_favorite_toggle_and_summary_count(client):
    nid = "behavioral.framework.star"
    r1 = client.post(f"{API}/roadmap/nodes/{nid}/favorite")
    assert r1.status_code == 200
    assert r1.json()["favorite"] is True
    s = client.get(f"{API}/roadmap/summary").json()
    assert s["counts"]["favorite"] >= 1


# ---------- Attempt ----------

def test_attempt_increments(client):
    nid = "dsa.foundations.arrays.prefix_sum"
    r1 = client.post(f"{API}/roadmap/nodes/{nid}/attempt", json={"actual_minutes": 18})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["attempts"] == 1
    assert d1["actual_solve_minutes"] == 18

    r2 = client.post(f"{API}/roadmap/nodes/{nid}/attempt", json={})
    d2 = r2.json()
    assert d2["attempts"] == 2
    assert d2["actual_solve_minutes"] == 18  # unchanged when omitted

    # First-attempt seeds in_progress
    detail = client.get(f"{API}/roadmap/nodes/{nid}").json()
    assert detail["node"]["progress"]["status"] in ("in_progress", "completed", "mastered")


# ---------- Today + rollup ----------

def test_today_and_rollup_increment(client):
    # Kadane was completed above — today.completed_ids should include it.
    s = client.get(f"{API}/roadmap/summary").json()
    assert s["today"]["completed_count"] >= 1
    assert "dsa.foundations.arrays.kadane" in s["today"]["completed_ids"]
    assert s["overall"]["completed_topics"] >= 1

    prog = client.get(f"{API}/roadmap/progress").json()
    dsa = next(t for t in prog["tracks"] if t["id"] == "dsa")
    assert dsa["progress"]["completed_topics"] >= 1
    assert dsa["progress"]["mastery_percentage"] > 0


# ---------- Revision-due validation ----------

def test_status_accepts_revision_due(client):
    nid = "dsa.foundations.arrays.diff_array"
    r = client.post(f"{API}/roadmap/nodes/{nid}/status", json={"status": "revision_due"})
    assert r.status_code == 200


# ---------- Regression: legacy IDs ----------

@pytest.mark.parametrize("nid", [
    "dsa.foundations.arrays.kadane", "java.collections.hashmap",
    "lld.cases.parking_lot", "hld.cases.url_shortener",
])
def test_legacy_ids_still_work(client, nid):
    r = client.get(f"{API}/roadmap/nodes/{nid}")
    assert r.status_code == 200
    prog = r.json()["node"]["progress"]
    # Extended fields present
    for k in ["bookmarked", "favorite", "attempts", "actual_solve_minutes",
              "completion_date", "total_topics", "completed_topics",
              "remaining_topics", "completion_pct", "estimated_hours_remaining"]:
        assert k in prog, f"missing {k}"


# ---------- Regression: existing endpoints ----------

def test_roadmap_progress_has_new_tracks(client):
    r = client.get(f"{API}/roadmap/progress")
    assert r.status_code == 200
    data = r.json()
    by_id = {t["id"]: t for t in data["tracks"]}
    assert len(by_id["dsa"]["modules"]) == 7
    assert len(by_id["projects"]["modules"]) == 3
    assert len(by_id["behavioral"]["modules"]) == 4
    assert len(by_id["resume"]["modules"]) == 3


def test_missions_today_ok(client):
    r = client.get(f"{API}/missions/today")
    assert r.status_code == 200


def test_profile_and_me_ok(client):
    assert client.get(f"{API}/profile").status_code == 200
    assert client.get(f"{API}/auth/me").status_code == 200
    assert client.get(f"{API}/onboarding").status_code == 200
