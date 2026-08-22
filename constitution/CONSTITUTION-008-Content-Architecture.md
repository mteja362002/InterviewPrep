# CONSTITUTION-008 — Content Architecture

**Version:** 1.0  
**Status:** Active  
**Scope:** `backend/knowledge_generation.py`, `backend/prompt_builder.py`, `backend/ai_service.py`, `backend/problem_bank.py` (problems as content), `backend/data/roadmap_v1.json` (node descriptions as content)  
**Authority:** Chief Software Architect  

---

## Purpose

Content Architecture governs how PrepOS produces, stores, versions, and serves learning content. This includes AI-generated Knowledge Base articles, flashcards, interview tips, coding examples, problem bank entries, and revision content. It defines the canonical shape of all learning content and the rules for its lifecycle.

---

## Responsibilities

### Content Architecture Owns

- AI-generated Knowledge Base content for roadmap nodes (`knowledge_content` collection)
- The global KB content cache strategy (first-user-pays model)
- The prompt construction for content generation (`prompt_builder.py`)
- The structured content schema (theory, examples, tips, flashcards, related_topics, prerequisites)
- The `knowledge_content` MongoDB collection

### Content Architecture Does NOT Own

- Problem selection (owned by Curriculum Engine)
- Roadmap structure (owned by Curriculum Engine)
- Conversation content (owned by AI Mentor)
- Assessment questions (owned by Assessment Engine)

---

## Scope

This constitution governs:

1. The KB content generation lifecycle
2. The KB content schema
3. The prompt engineering standards
4. The content caching strategy
5. The problem metadata as content (in `problem_bank.py`)
6. The roadmap node descriptive content (in `roadmap_v1.json`)

---

## Architectural Principles

### CA-001 — Global Cache, Not Per-User

KB content is generated once for `(node_id, roadmap_version)` and cached in `knowledge_content`. All learners see the same content for the same node. Per-user content customization is a future concern. This is a deliberate cost-control and quality-control decision.

### CA-002 — First-Requester Pays

The first user to request content for a node triggers generation. All subsequent users read from cache. This means early users bear the latency cost; this is an acceptable trade-off for the global benefit.

### CA-003 — Strict JSON from LLM

All content generation calls MUST request strict JSON from the LLM (no markdown fences, no prose outside JSON). The `prompt_builder.py` MUST include this instruction explicitly. `parse_content()` handles malformed responses by falling back to sensible empty defaults — it MUST NEVER raise.

### CA-004 — Content Does Not Drive Logic

AI-generated content is for human consumption only. It MUST NOT be parsed to derive learner state, mastery scores, or planning inputs. Content is a presentation layer. Logic is in the service layer.

### CA-005 — Problem Metadata is Editorial, Not Generated

Problem bank entries (`PROBLEMS` in `problem_bank.py`) are manually curated. No AI MUST generate or modify problem metadata (title, difficulty, pattern, `representative` flag, companies, etc.). AI may generate problem explanations for the UI — this is presentation, not metadata.

### CA-006 — Content Versioning is by Roadmap Version

Content is keyed by `(node_id, roadmap_version)`. When a new roadmap version is published, content for new or changed nodes MUST be regenerated. Content for unchanged nodes (same `node_id`, new `roadmap_version`) MAY be migrated or regenerated.

### CA-007 — Regeneration is Opt-In

A user with admin or editor role MAY trigger regeneration of KB content for a specific node via `POST /api/roadmap/node/{id}/content/regenerate`. This clears the cache and re-generates on the next request. Standard users MUST NOT be able to trigger regeneration.

---

## Design Philosophy

PrepOS's Knowledge Base is the "textbook" that supplements coding practice. A learner who is about to practice two-pointer problems benefits enormously from reading a high-quality explanation of the pattern, seeing canonical examples, understanding common mistakes, and reviewing relevant flashcards — all in one place, personalized to the interview context.

The decision to generate this content with an LLM (rather than writing it manually) reflects:

1. **Scale:** There are ~200 roadmap nodes. Manually writing high-quality content for each would require prohibitive editorial effort.
2. **Freshness:** LLM-generated content can be refreshed as models improve.
3. **Consistency:** Every node gets the same content structure (theory → examples → tips → mistakes → flashcards → related → prerequisites).
4. **Global cache:** The cost is amortized across all users for a given deployment.

The trade-off: LLM-generated content can be wrong. This is mitigated by:
- Using PrepOS-specific system prompt identity ("never invent APIs or libraries")
- Structured JSON output that prevents hallucinated formatting
- Human review at scale by the first users who see the content
- An explicit regeneration mechanism for updates

---

## KB Content Schema

The canonical shape of a `knowledge_content` document:

```json
{
    "id": "uuid",
    "node_id": "string",
    "roadmap_version": "v1",
    "provider": "gemini",
    "model_name": "gemini-flash-latest",
    "theory": {
        "title": "string",
        "explanation": "string",
        "key_concepts": ["string"],
        "time_complexity": "string",
        "space_complexity": "string"
    },
    "examples": [
        {
            "title": "string",
            "description": "string",
            "code": "string",
            "language": "python",
            "explanation": "string"
        }
    ],
    "interview_tips": ["string"],
    "common_mistakes": [
        {
            "mistake": "string",
            "correction": "string"
        }
    ],
    "flashcards": [
        {
            "question": "string",
            "answer": "string"
        }
    ],
    "related_topics": [
        {
            "node_id": "string",
            "label": "string",
            "relationship": "prerequisite|related|advanced"
        }
    ],
    "prerequisites": [
        {
            "node_id": "string",
            "label": "string"
        }
    ],
    "generated_by": "user_id",
    "generated_at": "ISO timestamp",
    "updated_at": "ISO timestamp"
}
```

### Malformed Response Handling

If LLM response cannot be parsed as valid JSON, or if individual sections are missing:
- `theory` defaults to `{}`
- `examples` defaults to `[]`
- `interview_tips` defaults to `[]`
- `common_mistakes` defaults to `[]`
- `flashcards` defaults to `[]`
- `related_topics` defaults to `[]`
- `prerequisites` defaults to `[]`

A document with all-default sections IS stored to prevent re-generation storms. The content may be manually triggered for regeneration.

---

## Prompt Engineering Standards

### System Message

```
You are PrepOS Mentor — an interview coach for software engineers targeting 
product-based companies (Google, Microsoft, Uber, Atlassian, Adobe, LinkedIn, 
Stripe, PhonePe, Flipkart, Goldman Sachs, PayPal, Salesforce, Oracle, Zoho). 
You produce concise, high-signal interview content. Never invent APIs, 
libraries or study links. Prefer canonical explanations over trivia. 
Return STRICT JSON — no markdown code fences, no prose outside JSON.
```

This system message MUST be used verbatim for all KB generation calls. It MUST NOT be modified without an editorial review.

### User Prompt Context Injected

| Field | Source |
|-------|--------|
| Node label | `node["label"]` |
| Track | `node["track"]` |
| Module | `node["module"]` |
| Category | `node["category"]` |
| Difficulty | `node["difficulty"]` |
| Tags | `node["tags"]` |
| Description | `node["description"]` |
| Interview frequency | `node["interview_frequency"]` |
| Related context | Prerequisite and sibling node IDs + labels |

### Quality Rules

Prompts MUST NOT ask the LLM to:
- Provide LeetCode-specific solution hints (avoid copyright issues)
- Generate "study links" to external resources
- Rate the difficulty of its own output
- Produce content longer than the structured JSON schema allows

---

## Roadmap Node as Content

Each roadmap node in `roadmap_v1.json` carries editorial content:

| Field | Type | Purpose |
|-------|------|---------|
| `description` | str | Brief node description for UI tooltips and context |
| `learning_objectives` | list[str] | What the learner will be able to do after this node |
| `interview_frequency` | int (1-5) | How often this topic appears in interviews (editorial) |
| `tags` | list[str] | Related topic keywords for search |

This content is **editorial** — authored by humans, never generated. It is used as context for KB generation prompts and as display content in the Knowledge Base UI.

---

## Problem Bank as Content

Each problem in `problem_bank.py` carries display content:

| Field | Purpose |
|-------|---------|
| `title` | Display title |
| `leetcode_url` | Link to problem (external, never scraped) |
| `estimated_minutes` | Time estimate for the UI |
| `tags` | Related topics for display |
| `source_lists` | Attribution (Blind75, NeetCode150, etc.) |

Problem content MUST NEVER be scraped or imported from LeetCode. PrepOS links to LeetCode — it does not host problem text.

---

## Data Ownership

| Collection | Access | Notes |
|-----------|--------|-------|
| `knowledge_content` | Read + Write | Owned by Content Architecture (via `knowledge_generation.py`) |

---

## Allowed Dependencies

Content Architecture modules MAY depend on:

- `ai_service.py`
- `roadmap.py` (node metadata for prompts)
- Standard Python library

---

## Forbidden Dependencies

❌ `mission_engine.py`  
❌ `assessment/`  
❌ `services/learner_intelligence/`  
❌ Writing to `knowledge_nodes`, `daily_missions`, or `assessments`  
❌ Scraping external URLs for content  

---

## Performance Expectations

| Operation | Target |
|-----------|--------|
| Cache read (hit) | <20ms |
| Cache miss (generation) | 3-10s |
| Cache clear + regeneration | Same as miss |

Content generation SHOULD be non-blocking from the user's perspective. The API SHOULD return a loading state and poll for completion, or use a streaming response for generation.

---

## Invariants

1. `knowledge_content` documents are keyed by `(node_id, roadmap_version)` — unique index.
2. A document is never deleted except via explicit `clear_cache()` before regeneration.
3. `generated_by` is always set to the user_id of the first requester.
4. `parse_content()` NEVER raises — malformed responses produce empty-default documents.
5. AI-generated content MUST NOT influence learner state, mastery, or planning.

---

## Anti-patterns

❌ Generating KB content per-user (content is global)  
❌ Regenerating on every request (cache must be checked first)  
❌ Parsing AI-generated content to make planning decisions  
❌ Storing full problem text (title + description + solution) in `knowledge_content`  
❌ Allowing LLM to suggest which problems a learner should study  
❌ Using markdown fences in LLM output (strict JSON only)  

---

## Future Evolution

- **Content versioning:** Add a `content_version` field to `knowledge_content`. When the prompt template changes significantly, bump the version and regenerate all content with the new template.
- **Editorial review workflow:** Add a `review_status` field (`draft | approved | flagged`). A PrepOS editor reviews LLM-generated content before it is shown to learners. Default: `approved` (current behavior, no review required).
- **User-contributed notes:** Add `user_notes` to `knowledge_content` as a per-user overlay (separate sub-document keyed by `user_id`). The global canonical content is unchanged.
- **Multi-language support:** Add a `language` field to `knowledge_content`. Generate content in the user's preferred language. The cache key becomes `(node_id, roadmap_version, language)`.
- **Content quality feedback:** Allow learners to flag content as incorrect or outdated. This triggers a review queue, not automatic regeneration.
