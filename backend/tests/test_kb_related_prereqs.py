"""
Tests for Knowledge Base related/prerequisites hydration + AI generation regression.
"""
import os
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://repo-validator-15.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@prepos.io"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="module")
def auth_headers():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, r.text
    # Use cookie jar
    return s


def test_kadane_node_related_populated(auth_headers):
    r = auth_headers.get(f"{BASE_URL}/api/roadmap/nodes/dsa.foundations.arrays.kadane", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    print("KADANE keys:", list(data.keys()))
    print("KADANE related:", data.get("related"))
    print("KADANE prerequisites:", data.get("prerequisites"))
    related = data.get("related") or []
    assert isinstance(related, list)
    assert len(related) >= 3, f"Expected >=3 related, got {len(related)}: {related}"
    for item in related:
        assert "id" in item and "label" in item


def test_prefix_sum_node_prereqs_and_related(auth_headers):
    r = auth_headers.get(f"{BASE_URL}/api/roadmap/nodes/dsa.foundations.arrays.prefix_sum", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    prereqs = data.get("prerequisites") or []
    related = data.get("related") or []
    print("PREFIX_SUM prereqs:", prereqs)
    print("PREFIX_SUM related:", related)
    assert len(prereqs) >= 1, f"Expected prereqs for prefix_sum, got {prereqs}"
    assert len(related) >= 1, f"Expected related for prefix_sum, got {related}"


def test_traversal_related_via_reverse_prereq(auth_headers):
    r = auth_headers.get(f"{BASE_URL}/api/roadmap/nodes/dsa.foundations.arrays.traversal", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    related = data.get("related") or []
    related_ids = [x.get("id") for x in related]
    print("TRAVERSAL related_ids:", related_ids)
    assert len(related) >= 1


def test_roadmap_tracks_endpoint(auth_headers):
    # KB page needs some listing endpoint
    r = auth_headers.get(f"{BASE_URL}/api/roadmap", timeout=30)
    print("Roadmap status:", r.status_code)
    assert r.status_code == 200
    data = r.json()
    # roadmap could return tracks list
    if isinstance(data, dict):
        tracks = data.get("tracks") or data.get("data") or []
    else:
        tracks = data
    print("Tracks count:", len(tracks) if hasattr(tracks, "__len__") else "n/a")


def test_settings_has_model(auth_headers):
    r = auth_headers.get(f"{BASE_URL}/api/settings", timeout=30)
    assert r.status_code == 200
    data = r.json()
    print("Settings keys:", list(data.keys()))
    # look for gemini model field
    for k, v in data.items():
        if "model" in k.lower() or "gemini" in str(v).lower():
            print(f"  {k}: {v}")


def test_ai_generation_java_exceptions(auth_headers):
    r = auth_headers.post(
        f"{BASE_URL}/api/roadmap/nodes/java.exceptions.core/content/generate",
        timeout=180,
    )
    print("Gen status:", r.status_code)
    print("Gen body (truncated):", r.text[:500])
    assert r.status_code == 200, r.text
    data = r.json()
    # Look for theory/examples/tips in some shape
    body = data.get("content") or data
    keys = list(body.keys()) if isinstance(body, dict) else []
    print("Payload keys:", keys)
    assert r.status_code == 200
