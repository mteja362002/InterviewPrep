## PrepOS Company Intelligence — Compilation & Runtime Guide

> Phase 1 deliverable. Covers the compilation pipeline, architecture flow,
> how to add a company, schema evolution, versioning, runtime loading, and the
> read-only API. This layer is **additive** — it does not change the planner,
> mission engine, or readiness calculations.

---

### 1. Overview & Sources of Truth

| Concern | Source of truth | Location |
|---|---|---|
| **Editorial** company knowledge | Markdown profiles | `docs/curriculum/company-intelligence/companies/*.md` |
| Canonical **schema** contract | Schema doc | `docs/curriculum/company-intelligence/schema.md` |
| Canonical company **identity** (ids, names, accents, category) | Registry | `backend/company_intelligence/registry.json` |
| **Runtime** company data | Compiled JSON artifacts | `backend/company_intelligence/compiled/**` |
| Frontend company catalog | Generated from registry | `frontend/src/config/companies.generated.json` |

**Two hard rules:**
1. **Runtime never parses Markdown.** Markdown is read only at *compile time*.
2. **Compiled JSON is the canonical runtime source.** Everything the app serves
   at runtime comes from `compiled/**` via the loader.

---

### 2. Architecture Flow

```
Company Markdown (docs/.../companies/*.md)      EDITORIAL SOURCE
        │  (compile time only)
        ▼
Schema Validator  (company_intelligence/schema_validator.py)
        │  fail-fast, no silent repair
        ▼
Deterministic Compiler (company_intelligence/compiler.py)
        │  ◄── Registry (company_intelligence/registry.json)
        ▼
Compiled JSON Artifacts (company_intelligence/compiled/**)   RUNTIME SOURCE
        │  (runtime — JSON only)
        ▼
Runtime Loader (company_intelligence/loader.py, cached)
        │
        ▼
Read-only REST API (routes_companies.py  →  /api/companies/*)
        │
        ▼
Future consumers: Adaptive Planner · Company Readiness · AI Mentor · Analytics · Mock Interviews

Registry ──(compile CLI)──► frontend/src/config/companies.generated.json ──► config/companies.js
```

---

### 3. Compilation Flow

Compilation is driven by `backend/scripts/compile_companies.py`.

```
python backend/scripts/compile_companies.py            # compile all 14
python backend/scripts/compile_companies.py google      # compile a subset
python backend/scripts/compile_companies.py --check      # validate only, no writes
python backend/scripts/compile_companies.py --clean      # wipe compiled/ first
```

For each company in the registry the CLI:
1. Reads `docs/.../companies/<id>.md`.
2. **Validates** it against the canonical schema (`schema_validator.py`).
3. **Compiles + normalizes** it into a JSON payload (`compiler.py`).
4. Writes an **immutable** `compiled/<id>/v<version>.json` and a `compiled/<id>/latest.json` alias.
5. Rebuilds `compiled/index.json` (the mutable manifest) and regenerates
   `frontend/src/config/companies.generated.json` from the registry.

If **any** company fails validation, the CLI prints structured diagnostics and
exits non-zero. Malformed Markdown is **never** silently repaired.

---

### 4. Validation Flow

`schema_validator.validate_markdown(company_id, markdown)` returns a
`ValidationResult(ok, errors, warnings, summary)`.

**Required sections** (must appear as headings; validation fails otherwise):
`Metadata, Company Overview, Engineering Philosophy, Hiring Philosophy,
Interview Pipeline, Evaluation Signals, Subject Importance, Behavioral,
Role Differences, Evidence Summary, Machine-Readable Summary`.

**Required machine-readable fields** (inside the ```yaml block under
*Machine-Readable Summary*):
- `company.name`
- `profile.version`
- non-empty `subjects` mapping
- one of: non-empty `interview` mapping **or** non-empty `signals` list

**Advisory warnings (non-fatal):** missing `planner` section, missing
`profile.confidence`.

---

### 5. Compiled Artifact Shape (normalized runtime fields)

```jsonc
{
  "company_id": "google",
  "artifact_schema_version": "1.0",
  "registry_schema_version": "1.0",
  "profile_version": "2.0",
  "source_checksum":  "sha256:…",   // sha256 of the raw markdown
  "content_checksum": "sha256:…",   // sha256 of canonical payload (deterministic)
  "metadata": { "name", "display_name", "accent", "primary_category",
                "categories", "last_reviewed", "confidence" },
  "summary_variant": "interview" | "signals",
  "signals":  [ … normalized signal list … ],
  "subjects": { subject_id: importance, … },
  "levels":   { … },
  "trends":   { … },
  "planner":  { philosophy, priority, adaptive, … },
  "summary":  { … full machine-readable YAML, preserved verbatim … },
  "sections": { … raw editorial text — INTERNAL ONLY, not served by the API … },
  "validation": { "warnings": [ … ] }
}
```

**Structural variants normalized:**
- *Standard* profiles expose `interview` + `levels` → `summary_variant: "interview"`.
- *Adobe* exposes a `signals` list plus `priority_by_level`, `signal_classification`,
  `negative_evidence`, `contradictions` → `summary_variant: "signals"`.
- *Salesforce* adds `role_domains`.
All variant-specific data is preserved verbatim under `summary`; nothing is lost.

> The `sections` field carries verbatim editorial Markdown text. It is retained
> in the on-disk artifact for future explainability tooling but is **stripped
> from every public API response** (see `loader._INTERNAL_ONLY_FIELDS`).

---

### 6. Versioning

- **`profile_version`** comes from `profile.version` in the Markdown's
  machine-readable summary. Bump it when the company's *content* changes.
- **`artifact_schema_version`** (`compiler.ARTIFACT_SCHEMA_VERSION`) — bump when
  the compiled artifact *shape* changes.
- **`registry_schema_version`** — bump when `registry.json` structure changes.
- Immutable `compiled/<id>/v<version>.json` files are the traceable record; the
  `latest.json` alias and `index.json` point to the current version.
- **`content_checksum`** lets any runtime decision be traced to an exact,
  reproducible artifact. It excludes wall-clock, so it is stable across recompiles.

**Determinism guarantee:** given identical Markdown + registry metadata, every
`compiled/<id>/v*.json` and `latest.json` is byte-for-byte identical across
recompiles. Only `index.json` changes between runs (its `generated_at`), because
it is the mutable manifest/pointer — not an immutable artifact.

---

### 7. Runtime Loading

`company_intelligence/loader.py` exposes a cached singleton `company_intelligence`
(`CompanyIntelligenceService`). It:
- reads **only** `index.json` and `compiled/<id>/latest.json` (JSON, never Markdown);
- lazily loads + caches artifacts in memory (thread-safe); `refresh()` reloads;
- serves normalized data through:
  - `list_companies()` — catalog rows
  - `get_company(id)` — full artifact **minus** internal-only fields (`sections`)
  - `get_summary(id)` / `get_signals(id)` / `get_metadata(id)`
  - `get_sections(id)` — **internal/admin only**, not wired to any public route.

Other subsystems (planner, readiness, AI mentor, analytics) should consume this
service in later phases rather than reading Markdown or duplicating company data.

---

### 8. API Overview (read-only)

Router: `routes_companies.py`, prefix `/api/companies`.

| Method & Path | Purpose | Response |
|---|---|---|
| `GET /api/companies` | Compiled catalog | `{schema_version, companies:[…]}` |
| `GET /api/companies/{id}` | Full normalized artifact (no `sections`) | artifact object |
| `GET /api/companies/{id}/summary` | Machine-readable summary | `{company_id, profile_version, summary_variant, summary}` |
| `GET /api/companies/{id}/signals` | Evaluation signals + subjects | `{company_id, profile_version, summary_variant, signals, subjects}` |
| `GET /api/companies/{id}/metadata` | Metadata + version + checksums | `{company_id, metadata, profile_version, …, source_checksum, content_checksum}` |

Unknown ids return `404`. **No endpoint exposes raw Markdown.**

---

### 9. Adding a New Company

1. Add the id + display metadata to `backend/company_intelligence/registry.json`.
2. Create `docs/curriculum/company-intelligence/companies/<id>.md` following
   `schema.md` (all required sections + a machine-readable ```yaml block).
3. (If the company participates in the roadmap graph) add its id to
   `backend/scripts/generate_roadmap.py` `COMPANIES` and regenerate the roadmap.
4. Run `python backend/scripts/compile_companies.py --check` then without `--check`.
5. The frontend catalog regenerates automatically; `config/companies.js` picks it up.
6. Run `pytest backend/tests/test_company_intelligence.py`.

Because ids are cross-checked, the registry, roadmap, Markdown, compiled
artifacts, and frontend catalog stay aligned.

---

### 10. Schema Evolution

- **Additive changes** (new optional YAML keys, new sections) are backward
  compatible: they land in `summary` and are preserved without a shape bump.
- **New required section/field** → update `schema_validator.REQUIRED_SECTIONS`
  (or the required-field checks), update all Markdown profiles, and bump each
  affected `profile_version`.
- **Compiled artifact shape change** → update `compiler._build_payload`, bump
  `ARTIFACT_SCHEMA_VERSION`, recompile, and update the loader/consumers + tests.
- **New structural variant** → extend `compiler._normalize_signals` (and add a
  `summary_variant`) rather than forcing the source to a single shape.

Keep Markdown as the editorial source of truth; keep compiled JSON as the runtime
source of truth; keep the registry as the single source of company identity.
