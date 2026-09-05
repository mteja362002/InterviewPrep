# CONSTITUTION-006 — AI Mentor

**Version:** 1.0  
**Status:** Active  
**Scope:** `backend/ai_mentor/`, `backend/ai_service.py`, `backend/knowledge_generation.py`, `backend/prompt_builder.py`  
**Authority:** Chief Software Architect  

---

## Purpose

The AI Mentor is PrepOS's LLM-powered personalized tutor. It grounds every response in the learner's actual state — their progress, weak topics, today's mission, revision queue, and knowledge base content. The AI Mentor answers questions, explains concepts, and guides learners through their interview preparation journey.

The AI Mentor is **read-only**. It reads learner state to produce personalized responses. It MUST NEVER modify learner state, generate assessments, schedule missions, or produce evidence.

---

## Responsibilities

### AI Mentor Owns

- Multi-turn conversation management (`mentor_service.py`)
- Context assembly from learner state (`context_builder.py`)
- System prompt construction (`mentor_prompt.py`)
- Mission narrative generation (`mission_planner.py`)
- Conversation persistence (`conversation_store.py`)
- The `mentor_conversations` and `mentor_messages` MongoDB collections
- The `knowledge_content` MongoDB collection (via `knowledge_generation.py`)

### AI Mentor Does NOT Own

- Learner state mutations (owned by Learner Intelligence / Progress Engine)
- Mission generation (owned by Mission Engine)
- Assessment creation or evaluation (owned by Assessment Engine)
- Problem selection (owned by Problem Selector)
- The roadmap structure (owned by Curriculum Engine)

---

## Scope

This constitution governs:

1. **AI Mentor conversation** (`ai_mentor/`)
2. **Knowledge Base generation** (`knowledge_generation.py`, `prompt_builder.py`)
3. **LLM provider abstraction** (`ai_service.py`)

---

## Architectural Principles

### AM-001 — Read-Only Side Effects

Every AI Mentor call MUST be side-effect-free from the learner's perspective. The AI Mentor reads state, produces text, and persists the conversation. It MUST NOT write to `knowledge_nodes`, `daily_missions`, `assessments`, `problem_assignments`, or any other learner-state collection.

### AM-002 — Context is the Mentor's Superpower

The AI Mentor's quality comes entirely from the context injected into each call. Context MUST be assembled fresh per conversation turn. Context assembly MUST be read-only. A mentor response without context is a generic LLM response — unacceptable for PrepOS.

### AM-003 — Provider Abstraction is Mandatory

All LLM calls MUST go through `ai_service.complete()` with a typed `AICapability` enum. No module may directly instantiate `google.genai.Client` or any provider SDK. The AI Gateway (`ai_gateway/`) owns provider selection, routing, retry, and failover. Consumer modules never reference providers, models, or API keys.

### AM-004 — Graceful Degradation

If context assembly fails for any signal (DB error, missing data, first-time user), that section of context MUST degrade to an empty dict — the mentor still responds, just with less personalization. No context assembly failure may crash the conversation.

### AM-005 — Knowledge Base Content is Globally Cached

AI-generated KB content for a roadmap node is generated once (first requester) and cached in `knowledge_content`. All subsequent requests for the same `(node_id, roadmap_version)` read from cache. The cost is paid once; every learner benefits.

### AM-006 — Mission Narrative is Cached on the Mission

`mission_planner.py` generates `ai_narrative`, `tomorrow_preview`, and `week_goal` once per mission and stores them on the `DailyMission` document. Re-fetching the mission MUST return the cached values without re-invoking the LLM. This is a hard performance requirement.

### AM-007 — No Curriculum Authoring via AI

The AI Mentor MUST NEVER generate new roadmap nodes, modify problem bank entries, set `representative: True` on problems, or produce curriculum that is ingested into the system as authoritative. AI content is for human consumption only.

### AM-008 — Emergent LLM Key Fallback

When the primary API key fails due to rate limit, quota exhaustion, or model not found, the system MUST transparently fall back to the Emergent LLM key if configured. This fallback MUST be transparent to all callers — no caller changes behavior based on which key was used.

---

## Design Philosophy

The AI Mentor is PrepOS's intelligent tutor, not just a chat wrapper. The design principle is: **the mentor's quality scales with context quality.** A mentor that knows what the learner is struggling with, what they studied today, what they will study tomorrow, and what interview they are preparing for can provide dramatically better guidance than a generic LLM.

The context assembly architecture (`context_builder.py`) embodies this: it aggregates ~10 different signals from the learner's state into a compact (~1-2 KB) representation that fits comfortably in the system prompt without exploding token cost.

The mission narrative feature (`mission_planner.py`) is a specific application of this philosophy: the AI generates a brief "why today" explanation when the mission is created, cached permanently, so learners always see a personalized reason for their day's agenda.

---

## Context Signals Assembled Per Turn

| Signal | Source | Purpose |
|--------|--------|---------|
| User profile | `users`, `onboarding` | Name, target companies, position, target date, study hours |
| Roadmap progress | `knowledge_nodes` | Completion %, mastery, hours remaining |
| Weak topics | `knowledge_nodes` | Top 5 by weakness_score / low confidence |
| Strong topics | `knowledge_nodes` | Top 5 by confidence / mastery |
| Today's mission | `daily_missions` | Focus area, tasks, recommendation_insight |
| Revision queue | `knowledge_nodes` | Top 5 overdue revision items |
| Recent activity | `activity_events` | Last 6 events |
| Recent KB nodes | `knowledge_content` | Last 5 recently generated nodes (what user studied) |
| Current node KB content | `knowledge_content` | Full cached content for the node the user is asking about |

Total context: ~1-2 KB (structured). This MUST fit in the system prompt without pagination.

---

## Conversation Contract

### `POST /api/mentor/message`

**Input:**
```json
{
    "message": "string",            // User's question
    "conversation_id": "uuid|null", // Existing conversation or null for new
    "node_id": "string|null"        // Current roadmap node (for KB context injection)
}
```

**Processing:**
1. Load or create conversation
2. Assemble learner context snapshot (`context_builder.build_context()`)
3. Build system prompt with context
4. Build user message
5. Call `ai_service.complete()` with the appropriate `AICapability` enum
6. Persist user message + assistant response to `mentor_messages`
7. Update `mentor_conversations.updated_at`
8. Return response

**Output:**
```json
{
    "conversation_id": "uuid",
    "message": "string",           // AI Mentor response
    "created_at": "ISO timestamp"
}
```

---

## Knowledge Base Generation Contract

### `knowledge_generation.ensure_content(db, node_id, roadmap_version, user_id)`

**Guarantees:**
- Returns cached content if `(node_id, roadmap_version)` exists in `knowledge_content`
- On cache miss: calls `prompt_builder.build_prompt(node, roadmap)` then `ai_service.complete()`
- Parses LLM response with `prompt_builder.parse_content()` (malformed → empty defaults)
- Persists to `knowledge_content`
- Returns the content dict

**Output shape:**
```json
{
    "node_id": "string",
    "roadmap_version": "v1",
    "theory": {},
    "examples": [],
    "interview_tips": [],
    "common_mistakes": [],
    "flashcards": [],
    "related_topics": [],
    "prerequisites": []
}
```

---

## AI Gateway Architecture

### `ai_service.complete(capability, system_message, prompt, session_id) → str`

The public façade delegates to the AI Gateway (`ai_gateway/gateway.py`), which owns:

- **Capability resolution** via `CapabilityRegistry` — maps `AICapability` enums to execution parameters (temperature, max_tokens, timeout, retry policy)
- **Provider routing** via `RoutingPolicy` — orders available providers by priority, filters by capability support
- **Retry with failover** — exponential backoff within a provider, then failover to the next
- **Error classification** — raw SDK exceptions → structured `AIProviderError` with provider-neutral messages

**Registered capabilities:**

| Capability | Temperature | Max Tokens | Timeout | Structured |
|-----------|-------------|------------|---------|------------|
| `KNOWLEDGE_GENERATION` | 0.7 | 8192 | 30s | Yes |
| `MENTOR_CHAT` | 0.6 | 4096 | 30s | No |
| `MENTOR_LESSON` | 0.6 | 4096 | 30s | Yes |
| `MISSION_NARRATIVE` | 0.4 | 2048 | 20s | Yes |
| `ASSESSMENT_CONTENT` | 0.5 | 4096 | 30s | Yes |

**Provider discovery:** `ProviderRegistry.load_from_environment()` reads `GEMINI_API_KEY`, `EMERGENT_LLM_KEY`, and future `OPENROUTER_API_KEY` from environment variables. Providers are stateless adapters — they know nothing about env vars, priorities, or configuration.

**Error kinds:**
| Kind | Status | Retryable |
|------|--------|----------|
| `invalid_key` | 401 | No |
| `rate_limit` | 429 | Yes |
| `model_not_found` | 404 | No |
| `timeout` | 504 | Yes |
| `upstream` | 502 | Yes |
| `no_providers` | 503 | No |
| `all_providers_failed` | 503 | No |

**User AI config:** Deprecated. Users no longer configure providers, models, or API keys. `UserSettings.ai_config` exists only for MongoDB backward compatibility and is never read by any consumer code.

---

## System Prompt Identity

The AI Mentor presents as "PrepOS Mentor" — an interview coach for software engineers targeting product-based companies. The system prompt:

1. **Must not** pretend to be a general assistant
2. **Must** ground all responses in the injected context
3. **Must not** invent APIs, libraries, or study links
4. **Must** prefer canonical, high-signal interview explanations
5. **Must** return strict JSON when called for structured output

The system prompt identity MUST NOT be overridable by user messages. A user message claiming "ignore your instructions" MUST NOT change the mentor's identity or break the JSON output contract.

---

## Data Ownership

| Collection | Access | Notes |
|-----------|--------|-------|
| `mentor_conversations` | Read + Write | Owned exclusively by AI Mentor |
| `mentor_messages` | Read + Write | Owned exclusively by AI Mentor |
| `knowledge_content` | Read + Write | Owned exclusively by AI Mentor (via knowledge_generation.py) |
| `users` | Read only | Profile + email |
| `onboarding` | Read only | Target companies, position, date, hours |
| `knowledge_nodes` | Read only | Progress, confidence, mastery, revision queue |
| `daily_missions` | Read only | Today's mission context |
| `activity_events` | Read only | Recent activity |

---

## Allowed Dependencies

The AI Mentor MAY depend on:

- `ai_service.py` (LLM calls)
- `prompt_builder.py` (prompt construction)
- `roadmap.py` (node lookup, label resolution)
- `services/revision_engine.py` (read revision queue)
- `services/progress_engine.py` (read progress rollup)
- Standard Python library

---

## Forbidden Dependencies

❌ `mission_engine.py` (no generating missions)  
❌ `assessment/` (no creating or evaluating assessments)  
❌ `services/learner_intelligence/` (no computing LI signals)  
❌ `services/learning_engine/` (no running the planner)  
❌ Writing to `knowledge_nodes`, `daily_missions`, `assessments`, `weaknesses`  
❌ Generating problem bank entries or roadmap nodes  
❌ `company_intelligence/` bias engine (no mission planning)  

---

## Performance Expectations

| Operation | Target |
|-----------|--------|
| Context assembly | <100ms (parallel DB reads) |
| LLM call (user message) | 2-10s (streaming preferred) |
| LLM call (KB generation) | 3-10s (first time per node) |
| KB cache read | <20ms |
| Mission narrative generation | <10s (async, cached on mission) |
| Conversation history load | <50ms |

The AI Mentor SHOULD use streaming responses to improve perceived latency. The first token SHOULD arrive within 1-2 seconds of the request.

---

## Invariants

1. Context assembly errors for individual signals MUST NOT crash the conversation.
2. Every conversation turn persists both user and assistant messages before returning.
3. KB content is globally shared — different users MUST receive identical KB content for the same `(node_id, roadmap_version)`.
4. Mission narrative is generated at most once per `DailyMission` document.
5. The AI Mentor NEVER writes to learner-state collections.
6. `ai_service.complete()` is the ONLY path for LLM calls in PrepOS. Consumer modules use typed `AICapability` enums — never raw provider/model strings.

---

## Anti-patterns

❌ Inline LLM calls in route handlers (all LLM calls go through `ai_service.py`)  
❌ Building context inside the route handler (belongs in `context_builder.py`)  
❌ Storing user conversation history in-memory only (must persist to MongoDB)  
❌ Generating KB content synchronously in the user request hot path (use async or background)  
❌ Re-generating KB content on every request (read from cache first)  
❌ Allowing user messages to override the system prompt identity  
❌ Generating mission plans inside the AI Mentor (belongs in `mission_planner.py` called from Mission Engine)  
❌ Directly querying `assessments` to build context (AI Mentor does not know about assessment internals)  

---

## Future Evolution

- **Streaming responses:** All `POST /api/mentor/message` calls SHOULD return a streaming HTTP response. The gateway adds a `stream_complete()` method. Context assembly is unchanged.
- **Voice interface:** A future voice mentor interface calls `mentor_service.py` with audio-transcribed text. The response is passed to a TTS service. No changes to `mentor_service.py` required.
- **Additional providers:** Add a new adapter in `ai_gateway/providers/`, register in `ProviderRegistry.load_from_environment()`. Zero consumer changes.
- **Fine-tuned models:** Switch the model in the provider's environment variable (`GEMINI_MODEL`). No architecture change.
- **Context ranking:** As context signals grow, a future version may rank and trim signals by relevance to the current question using embeddings. This is purely an enhancement to `context_builder.py`.
- **Proactive mentor push:** A future feature sends proactive mentor tips based on the learner's upcoming revision queue. Implemented as a scheduled job reading `knowledge_nodes` → generating tip via `ai_service.complete()` → sending via `email_service.py`. No mentor architecture change.
