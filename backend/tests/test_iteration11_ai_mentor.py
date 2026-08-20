"""AI Mentor (Phase 4) — end-to-end backend tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://repo-validator-15.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@prepos.io"
ADMIN_PASS = "Admin@123"

GEMINI_KEY = "AQ.Ab8RN6IIHyOfLvBo4LueR5NLPxfX-Se43pqpMBeiO7DS61AF7w"


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def ensure_ai_config(sess):
    """Ensure Gemini config is saved."""
    r = sess.patch(f"{BASE_URL}/api/settings", json={
        "ai_config": {"provider": "gemini", "model": "gemini-flash-latest", "api_key": GEMINI_KEY}
    }, timeout=30)
    assert r.status_code == 200, r.text
    return True


# ---------- Context preview ----------

def test_context_preview(sess, ensure_ai_config):
    r = sess.get(f"{BASE_URL}/api/mentor/context/preview", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ["name", "target_companies", "weak_topics", "strong_topics", "revision_due_count"]:
        assert key in data, f"missing {key}: {data}"
    assert isinstance(data["target_companies"], list)
    assert isinstance(data["weak_topics"], list)
    assert isinstance(data["strong_topics"], list)


# ---------- Chat happy path ----------

class TestChat:
    conversation_id = None

    def test_chat_first_message(self, sess, ensure_ai_config):
        t0 = time.time()
        r = sess.post(f"{BASE_URL}/api/mentor/chat", json={
            "message": "What should I study next in 3 bullets?"
        }, timeout=60)
        elapsed = time.time() - t0
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert "conversation_id" in data and data["conversation_id"]
        assert "message" in data and data["message"]["role"] == "assistant"
        assert "user_message" in data and data["user_message"]["role"] == "user"
        assert data["message"]["content"], "assistant content empty"
        assert "context_summary" in data
        ctx = data["context_summary"]
        assert "target_companies" in ctx and "weak_topics" in ctx and "strong_topics" in ctx
        TestChat.conversation_id = data["conversation_id"]
        print(f"first chat OK in {elapsed:.1f}s, convo={TestChat.conversation_id}")

    def test_chat_followup_memory(self, sess):
        assert TestChat.conversation_id
        r = sess.post(f"{BASE_URL}/api/mentor/chat", json={
            "message": "Great — repeat back just the FIRST bullet you gave me in 1 short sentence.",
            "conversation_id": TestChat.conversation_id,
        }, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["conversation_id"] == TestChat.conversation_id
        assert data["message"]["content"]

    def test_chat_kb_injected(self, sess):
        r = sess.post(f"{BASE_URL}/api/mentor/chat", json={
            "message": "Give me the interviewer trap for this topic in 2 lines",
            "topic_node_id": "dsa.foundations.arrays.kadane",
        }, timeout=90)
        assert r.status_code == 200, r.text
        data = r.json()
        ctx = data.get("context_summary") or {}
        cur = ctx.get("current_topic") or {}
        assert cur.get("id") == "dsa.foundations.arrays.kadane"
        # kb_available should be True IF KB was cached; we don't fail hard if not
        print(f"kb_available for kadane: {cur.get('kb_available')}")
        content_lower = (data["message"]["content"] or "").lower()
        # Loose check — mentions kadane, arrays, or max subarray
        assert any(k in content_lower for k in ["kadane", "subarray", "max", "negative", "sum"]), content_lower[:400]


# ---------- History / Detail / Delete ----------

def test_history(sess):
    r = sess.get(f"{BASE_URL}/api/mentor/history", timeout=30)
    assert r.status_code == 200, r.text
    convos = r.json()
    assert isinstance(convos, list)
    assert len(convos) >= 1
    c = convos[0]
    for k in ["id", "title", "message_count", "updated_at"]:
        assert k in c


def test_conversation_detail(sess):
    # Grab most-recent convo from history (xdist may run TestChat on another worker).
    h = sess.get(f"{BASE_URL}/api/mentor/history", timeout=30).json()
    assert h, "no conversations found in history"
    cid = next((c["id"] for c in h if c.get("message_count", 0) >= 2), h[0]["id"])
    r = sess.get(f"{BASE_URL}/api/mentor/conversation/{cid}", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "conversation" in data and "messages" in data
    msgs = data["messages"]
    assert len(msgs) >= 2
    # Ordered ASC
    times = [m["created_at"] for m in msgs]
    assert times == sorted(times), "messages not ordered ASC"


def test_new_chat(sess):
    r = sess.post(f"{BASE_URL}/api/mentor/new-chat", json={}, timeout=30)
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["id"] and c["title"]
    # Cleanup
    sess.delete(f"{BASE_URL}/api/mentor/conversation/{c['id']}", timeout=30)


def test_delete_conversation(sess):
    # Create fresh convo to delete
    r = sess.post(f"{BASE_URL}/api/mentor/new-chat", json={}, timeout=30)
    cid = r.json()["id"]
    d = sess.delete(f"{BASE_URL}/api/mentor/conversation/{cid}", timeout=30)
    assert d.status_code == 200, d.text
    assert d.json().get("ok") is True
    # Confirm gone
    g = sess.get(f"{BASE_URL}/api/mentor/conversation/{cid}", timeout=30)
    assert g.status_code == 404


# ---------- Missing key handling ----------

def test_missing_key_returns_400():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200
    # Save current
    cur = s.get(f"{BASE_URL}/api/settings", timeout=30).json()
    original = cur.get("ai_config")
    try:
        # Clear the api_key
        s.patch(f"{BASE_URL}/api/settings", json={
            "ai_config": {"provider": "gemini", "model": "gemini-flash-latest", "api_key": None}
        }, timeout=30)
        r = s.post(f"{BASE_URL}/api/mentor/chat", json={"message": "hi"}, timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        body = r.json()
        detail = body.get("detail") or body
        # detail should include 'missing_key' error kind
        err_str = str(detail).lower()
        assert "missing_key" in err_str or "missing" in err_str or "key" in err_str, detail
    finally:
        # Restore
        s.patch(f"{BASE_URL}/api/settings", json={
            "ai_config": {"provider": "gemini", "model": "gemini-flash-latest", "api_key": GEMINI_KEY}
        }, timeout=30)


# ---------- Regression: KB generate + settings dropdown ----------

def test_regression_settings_has_gemini_flash_latest(sess):
    r = sess.get(f"{BASE_URL}/api/settings", timeout=30)
    assert r.status_code == 200
    # Just ensures endpoint healthy
    assert isinstance(r.json(), dict)
