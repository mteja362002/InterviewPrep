"""Phase 1 Company Intelligence — unit/in-process test suite.

Pure unit tests. They do NOT require MongoDB, a running server, or any env
files: they exercise the registry, schema validator, deterministic compiler,
runtime loader, and the read-only company APIs (via an in-process TestClient
that mounts only the companies router).
"""
import copy

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from company_intelligence import registry
from company_intelligence.compiler import (
    ARTIFACT_SCHEMA_VERSION,
    CompilationError,
    compile_company,
)
from company_intelligence.loader import CompanyIntelligenceService
from company_intelligence.schema_validator import (
    REQUIRED_SECTIONS,
    extract_machine_readable_yaml,
    validate_markdown,
)
from routes_companies import router as companies_router

EXPECTED_IDS = {
    "google", "microsoft", "uber", "adobe", "atlassian", "linkedin", "stripe",
    "salesforce", "phonepe", "flipkart", "oracle", "paypal", "goldman_sachs", "zoho",
}

_VALID_YAML = """company:
  name: TestCo
profile:
  version: "1.0"
  confidence: Medium
interview:
  coding:
    importance: Critical
    confidence: Medium
subjects:
  dsa: Critical
planner:
  priority:
    - DSA
"""


def _make_markdown(sections=None, yaml_body=_VALID_YAML):
    """Build a synthetic company markdown doc from a list of section titles."""
    sections = REQUIRED_SECTIONS if sections is None else sections
    parts = []
    for i, title in enumerate(sections, start=1):
        parts.append(f"# {i}. {title}\n\nsome body text\n")
        if title == "Machine-Readable Summary" and yaml_body is not None:
            parts.append("```yaml\n" + yaml_body + "```\n")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# 1. Registry
# --------------------------------------------------------------------------- #
class TestRegistry:
    def test_exactly_14_unique_ids(self):
        ids = registry.company_ids()
        assert len(ids) == 14
        assert len(set(ids)) == 14
        assert set(ids) == EXPECTED_IDS

    def test_registry_matches_markdown_and_artifacts(self):
        from company_intelligence.compiler import MARKDOWN_DIR
        md = {p.stem for p in MARKDOWN_DIR.glob("*.md")}
        assert md == EXPECTED_IDS

    def test_get_meta_and_known(self):
        assert registry.is_known_company("google")
        assert not registry.is_known_company("amazon")
        meta = registry.get_company_meta("google")
        assert meta and meta["name"] == "Google" and meta["accent"]


# --------------------------------------------------------------------------- #
# 2. Schema validator
# --------------------------------------------------------------------------- #
class TestValidator:
    def test_valid_document_passes(self):
        res = validate_markdown("testco", _make_markdown())
        assert res.ok, res.errors
        assert res.summary["company"]["name"] == "TestCo"

    def test_missing_required_section_fails(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "Evidence Summary"]
        res = validate_markdown("testco", _make_markdown(sections))
        assert not res.ok
        assert any("Evidence Summary" in e for e in res.errors)

    def test_missing_yaml_block_fails(self):
        res = validate_markdown("testco", _make_markdown(yaml_body=None))
        assert not res.ok
        assert any("yaml" in e.lower() for e in res.errors)

    def test_unparseable_yaml_fails(self):
        bad = "company:\n  name: x\n : : bad : :\n"
        res = validate_markdown("testco", _make_markdown(yaml_body=bad))
        assert not res.ok

    def test_missing_subjects_fails(self):
        y = "company:\n  name: X\nprofile:\n  version: \"1.0\"\ninterview:\n  coding:\n    importance: High\n"
        res = validate_markdown("testco", _make_markdown(yaml_body=y))
        assert not res.ok
        assert any("subjects" in e for e in res.errors)

    def test_missing_interview_and_signals_fails(self):
        y = "company:\n  name: X\nprofile:\n  version: \"1.0\"\nsubjects:\n  dsa: Critical\n"
        res = validate_markdown("testco", _make_markdown(yaml_body=y))
        assert not res.ok
        assert any("interview" in e or "signals" in e for e in res.errors)

    def test_missing_planner_is_warning_not_error(self):
        y = "company:\n  name: X\nprofile:\n  version: \"1.0\"\ninterview:\n  coding:\n    importance: High\nsubjects:\n  dsa: Critical\n"
        res = validate_markdown("testco", _make_markdown(yaml_body=y))
        assert res.ok
        assert any("planner" in w for w in res.warnings)

    def test_extract_yaml_anchor(self):
        assert extract_machine_readable_yaml(_make_markdown()) is not None
        assert extract_machine_readable_yaml("# no anchor here") is None

    def test_all_real_profiles_validate(self):
        from company_intelligence.compiler import MARKDOWN_DIR
        for cid in registry.company_ids():
            md = (MARKDOWN_DIR / f"{cid}.md").read_text(encoding="utf-8")
            res = validate_markdown(cid, md)
            assert res.ok, f"{cid}: {res.errors}"


# --------------------------------------------------------------------------- #
# 3. Compiler
# --------------------------------------------------------------------------- #
class TestCompiler:
    def test_compile_google_shape(self):
        art = compile_company("google")
        for key in ("company_id", "profile_version", "source_checksum",
                    "content_checksum", "metadata", "signals", "subjects",
                    "summary", "summary_variant"):
            assert key in art
        assert art["company_id"] == "google"
        assert art["artifact_schema_version"] == ARTIFACT_SCHEMA_VERSION
        assert art["source_checksum"].startswith("sha256:")
        assert art["content_checksum"].startswith("sha256:")

    def test_compilation_is_deterministic(self):
        a = compile_company("google")
        b = compile_company("google")
        assert a == b
        assert a["content_checksum"] == b["content_checksum"]

    def test_variant_detection(self):
        assert compile_company("google")["summary_variant"] == "interview"
        assert compile_company("adobe")["summary_variant"] == "signals"

    def test_adobe_variant_preserves_extra_fields(self):
        art = compile_company("adobe")
        assert "negative_evidence" in art["summary"]
        assert "contradictions" in art["summary"]

    def test_unknown_company_raises(self):
        with pytest.raises(CompilationError):
            compile_company("does_not_exist")

    def test_all_14_compile(self):
        for cid in registry.company_ids():
            art = compile_company(cid)
            assert art["company_id"] == cid


# --------------------------------------------------------------------------- #
# 4. Runtime loader
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def svc():
    return CompanyIntelligenceService()


class TestLoader:
    def test_ready_and_lists_14(self, svc):
        assert svc.is_ready()
        assert len(svc.list_companies()) == 14

    def test_public_view_excludes_sections(self, svc):
        art = svc.get_company("google")
        assert art is not None
        assert "sections" not in art  # raw editorial text must NOT leak
        assert "signals" in art and "subjects" in art

    def test_sections_available_internally(self, svc):
        sections = svc.get_sections("google")
        assert isinstance(sections, dict) and sections  # internal accessor

    def test_summary_signals_metadata(self, svc):
        assert svc.get_summary("google")["summary"]["company"]["name"] == "Google"
        sig = svc.get_signals("google")
        assert sig["signals"] and sig["subjects"]
        meta = svc.get_metadata("google")
        assert meta["source_checksum"].startswith("sha256:")
        assert meta["content_checksum"].startswith("sha256:")

    def test_unknown_returns_none(self, svc):
        assert svc.get_company("amazon") is None
        assert svc.get_summary("amazon") is None
        assert svc.get_signals("amazon") is None
        assert svc.get_metadata("amazon") is None

    def test_caching_reuses_same_dict(self, svc):
        svc._ensure_loaded()
        cache_id = id(svc._cache)
        svc.list_companies()
        svc.get_company("uber")
        assert id(svc._cache) == cache_id

    def test_get_company_returns_copy(self, svc):
        a = svc.get_company("google")
        a["metadata"]["name"] = "MUTATED"
        b = svc.get_company("google")
        assert b["metadata"]["name"] == "Google"


# --------------------------------------------------------------------------- #
# 5. Company APIs
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def api():
    app = FastAPI()
    app.include_router(companies_router)
    return TestClient(app)


class TestCompanyAPI:
    def test_list(self, api):
        r = api.get("/api/companies")
        assert r.status_code == 200
        body = r.json()
        assert body["schema_version"] == "1.0"
        assert len(body["companies"]) == 14
        assert {c["company_id"] for c in body["companies"]} == EXPECTED_IDS

    def test_full_artifact_has_no_raw_markdown(self, api):
        r = api.get("/api/companies/google")
        assert r.status_code == 200
        body = r.json()
        assert "sections" not in body            # editorial text stripped
        assert "```yaml" not in r.text           # no markdown fences
        assert "# 1. Metadata" not in r.text     # no markdown headings
        assert body["signals"] and body["subjects"]

    def test_summary_endpoint(self, api):
        r = api.get("/api/companies/google/summary")
        assert r.status_code == 200
        b = r.json()
        assert set(b) >= {"company_id", "profile_version", "summary_variant", "summary"}

    def test_signals_endpoint(self, api):
        r = api.get("/api/companies/adobe/signals")
        assert r.status_code == 200
        b = r.json()
        assert b["summary_variant"] == "signals"
        assert b["signals"] and b["subjects"]

    def test_metadata_endpoint(self, api):
        r = api.get("/api/companies/google/metadata")
        assert r.status_code == 200
        b = r.json()
        assert b["source_checksum"].startswith("sha256:")
        assert b["content_checksum"].startswith("sha256:")

    def test_unknown_company_404(self, api):
        for suffix in ("", "/summary", "/signals", "/metadata"):
            r = api.get(f"/api/companies/amazon{suffix}")
            assert r.status_code == 404
