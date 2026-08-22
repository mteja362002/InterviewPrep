# CONSTITUTION-007 — Company Intelligence

**Version:** 1.0  
**Status:** Active  
**Scope:** `backend/company_intelligence/`, `backend/mission_engine.py::COMPANY_READINESS_WEIGHTS`  
**Authority:** Chief Software Architect  

---

## Purpose

Company Intelligence governs how PrepOS understands, models, and applies company-specific hiring preferences to the learner's preparation. It ensures that a learner targeting Google is prepared differently from one targeting Oracle — with higher DSA weight for Google and higher DBMS weight for Oracle.

Company Intelligence is a **compile-time editorial system with read-only runtime consumption**. Company profiles are authored in Markdown, compiled to JSON, and never reparsed at runtime.

---

## Responsibilities

### Company Intelligence Owns

- The canonical company registry (`registry.json`)
- Company profile editorial content (compiled JSON artifacts)
- The company importance scoring API (`scoring.py`)
- The company bias engine (`bias_engine.py`)
- The Markdown → JSON compilation pipeline (`compiler.py`)
- The runtime loader (`loader.py`)
- The schema validation rules for company profiles (`schema_validator.py`)
- The company-specific readiness weights in `mission_engine.py::COMPANY_READINESS_WEIGHTS`

### Company Intelligence Does NOT Own

- Learner state (owned by Progress Engine)
- Mission generation (owned by Mission Engine)
- Roadmap structure (owned by Curriculum Engine)
- Problem selection (owned by Problem Selector)

---

## Scope

This constitution governs:

1. `company_intelligence/__init__.py` — runtime exports
2. `company_intelligence/registry.json` — canonical company list
3. `company_intelligence/compiler.py` — build-time compilation
4. `company_intelligence/loader.py` — runtime JSON loading
5. `company_intelligence/scoring.py` — company importance scoring
6. `company_intelligence/bias_engine.py` — mission planning bias nudges
7. `company_intelligence/explainability.py` — human-readable company relevance
8. `mission_engine.py::COMPANY_READINESS_WEIGHTS` — per-company track weights

---

## Architectural Principles

### CI-001 — Compile-Time Not Runtime

Company profiles are authored in Markdown. They are validated and compiled to JSON at build time by `compiler.py`. The runtime MUST ONLY load compiled JSON artifacts. It MUST NEVER parse Markdown at runtime.

**Pipeline:**
```
Markdown (editorial source)
    → schema_validator.py (build time)
    → compiler.py (build time)
    → compiled/*.json (runtime source)
    → loader.py (runtime load)
    → bias_engine.py, scoring.py (runtime consumption)
```

### CI-002 — Read-Only Runtime

The Company Intelligence runtime layer is entirely read-only. No user action may modify company profiles. Profile updates require a new build + deployment.

### CI-003 — Deterministic Scoring

`scoring.company_importance(node_id, company_id)` MUST return a deterministic float for the same inputs. No randomness. No external dependencies at runtime.

### CI-004 — Separation of Compilation and Runtime

The `compiler.py` and `schema_validator.py` MUST NOT be imported at runtime. They are build tools only. The runtime MUST only consume `loader.py` and the compiled JSON artifacts.

### CI-005 — Registry is the Canonical Company List

The `registry.json` file is the single source of truth for which companies are supported. The frontend's company selector, the problem bank's `companies` field, and all APIs MUST reference only company IDs defined in `registry.json`.

---

## Design Philosophy

Company intelligence exists because interview preparation is not generic — it is company-specific. Google's interviews emphasize DSA and systems thinking. Oracle's interviews emphasize DBMS. A learner should not spend 45% of their time on DSA if they are targeting Oracle.

PrepOS models this at two levels:

1. **Track-level readiness weights** (`COMPANY_READINESS_WEIGHTS` in `mission_engine.py`): How much each topic track contributes to overall readiness for a given company. These are percentage weights summing to 1.0.

2. **Node-level company importance** (`roadmap.company_importance(node_id, company_id)`): How important a specific roadmap node is for a given company, on a 0-5 scale. Authored directly in `roadmap_v1.json` and inherited down the node hierarchy.

The track weights drive readiness scoring. The node importance scores drive candidate ranking in the Learning Engine.

---

## Company Registry

The `registry.json` file defines:

```json
{
    "companies": [
        {
            "id": "google",
            "name": "Google",
            "tier": "FAANG",
            "region": "global"
        },
        ...
    ]
}
```

**Rules:**
- Company IDs MUST be lowercase, snake_case
- IDs MUST be stable and IMMUTABLE once published
- New companies are added by appending to `registry.json`
- Companies are never removed (only deprecated with a `status: "inactive"` field)

### Supported Companies (as of v1)

| Tier | Companies |
|------|----------|
| FAANG & Big Tech | Google, Amazon, Microsoft, Meta, Apple, Netflix, Uber, Airbnb |
| Enterprise / Cloud | Adobe, Atlassian, LinkedIn, Salesforce, Oracle, ServiceNow, Intuit, NVIDIA |
| FinTech | Stripe, PayPal, Razorpay, PhonePe |
| Indian Product | Flipkart, Zoho, Walmart Global Tech |
| Finance | Goldman Sachs, JPMorgan Chase, American Express |

---

## Readiness Weight Model

Track-level readiness weights are defined in `mission_engine.py::COMPANY_READINESS_WEIGHTS`. Each company has a dict mapping track ID → weight (0..1, summing to 1.0).

**Editorial rules for weight authoring:**

1. Weights MUST sum to 1.0 per company (within floating-point tolerance)
2. Weight changes require an editorial review documenting the source (e.g., "Updated based on Google 2024 interview reports")
3. Companies not in `COMPANY_READINESS_WEIGHTS` fall back to `DEFAULT_READINESS`
4. New tracks introduced to the roadmap MUST be added to ALL company weight dicts

---

## Company Importance on Roadmap Nodes

Each roadmap node in `roadmap_v1.json` MAY carry:

```json
{
    "company_importance": {
        "google": 5,
        "amazon": 4,
        "microsoft": 3
    }
}
```

Scale: 0 (not relevant) to 5 (critical).

**Inheritance:** `roadmap.company_importance(node_id, company_id)` walks up the ancestor chain. A leaf node without `company_importance` inherits from its parent topic, module, or track. This prevents repetitive data entry.

---

## Allowed Dependencies

Company Intelligence MAY depend on:

- Standard Python library
- `registry.json` (static load)
- `compiled/*.json` (static load at runtime)

The runtime layer (`loader.py`, `scoring.py`, `bias_engine.py`) MUST NOT depend on:

- MongoDB
- `roadmap.py`
- `problem_bank.py`
- Any service module

---

## Forbidden Dependencies

❌ Parsing Markdown at runtime  
❌ MongoDB queries  
❌ LLM calls  
❌ `mission_engine.py` (Company Intelligence is consumed BY mission engine, not vice versa)  
❌ `services/learner_intelligence/`  
❌ `assessment/`  

---

## Data Ownership

| Asset | Owner | Consumers |
|-------|-------|----------|
| `registry.json` | Company Intelligence | Frontend company selector, problem bank validation |
| `compiled/*.json` | Company Intelligence | `loader.py` at runtime |
| `COMPANY_READINESS_WEIGHTS` (in `mission_engine.py`) | Company Intelligence | Mission Engine readiness computation |
| `roadmap_v1.json::company_importance` | Curriculum Engine (authored) / Company Intelligence (schema) | Learning Engine ranking |

---

## Extension Points

### New Company

1. Add to `registry.json` with a new stable ID
2. Author Markdown profile (if editorial content exists)
3. Compile with `scripts/compile_companies.py`
4. Add to `COMPANIES` dict in `problem_bank.py`
5. Add to `COMPANY_READINESS_WEIGHTS` in `mission_engine.py`
6. Add `company_importance` entries to relevant `roadmap_v1.json` nodes

### New Company Data Field

Add to company Markdown profile schema. Update `schema_validator.py` and `compiler.py`. The compiled JSON grows a new field. Consumers read it from `loader.py`. No runtime changes to non-consuming modules.

### Company-Specific Problem Curation

Problems already carry a `companies: [str]` field. Adding a new company ID to existing problems' `companies` lists provides company-specific problem recommendations without changing the selection architecture.

---

## Performance Expectations

| Operation | Target |
|-----------|--------|
| Company registry load | <10ms (singleton at startup) |
| `company_importance(node_id, company_id)` | <1ms (in-memory tree walk) |
| Readiness score computation | <5ms (in-memory, O(tracks)) |

Company Intelligence MUST use no I/O at runtime beyond the initial startup load.

---

## Invariants

1. Company IDs in `registry.json` are IMMUTABLE once published.
2. `COMPANY_READINESS_WEIGHTS` values per company MUST sum to 1.0.
3. All company IDs in `problem_bank.py::COMPANIES` MUST exist in `registry.json`.
4. The runtime layer NEVER parses Markdown.
5. A company with no entry in `COMPANY_READINESS_WEIGHTS` always falls back to `DEFAULT_READINESS` — this MUST NOT crash.

---

## Anti-patterns

❌ Parsing company Markdown at runtime  
❌ Storing company profiles in MongoDB  
❌ Generating company importance scores via AI  
❌ Hardcoding company names as strings in non-company-intelligence files  
❌ Two files both defining company readiness weights for the same companies  
❌ Using company IDs not registered in `registry.json`  

---

## Future Evolution

- **Company-specific assessment rubrics:** Add a `assessment_rubric` field to the company profile that overrides default rubric weights for companies with unusual interview patterns.
- **Interview trend updates:** Quarterly editorial review of `COMPANY_READINESS_WEIGHTS` based on community-reported interview data. Changes go through the same compile → deploy pipeline.
- **Automated company research:** A future tool scrapes interview reports (Glassdoor, LeetCode Discuss) and proposes weight updates for editorial review. The tool produces DRAFT weights — a human approves before deployment.
- **Company-specific learning paths:** A future feature generates a company-targeted roadmap overlay that reorders nodes by `company_importance` for a given company. Implemented as a new view on the existing roadmap data.
