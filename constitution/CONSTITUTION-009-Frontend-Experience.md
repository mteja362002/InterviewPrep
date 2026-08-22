# CONSTITUTION-009 — Frontend Experience

**Version:** 1.0  
**Status:** Active  
**Scope:** `frontend/src/`  
**Authority:** Chief Software Architect  

---

## Purpose

This constitution governs the architecture, state management, component design, and UX principles of the PrepOS React frontend. It ensures that the frontend is a presentation layer that faithfully renders backend state — without reimplementing business logic, duplicating data models, or making planning decisions independently.

---

## Responsibilities

### Frontend Owns

- All UI rendering and user interaction
- Client-side state management (auth session, UI layout, theme, mentor panel)
- API client layer (`src/services/`)
- React context providers (Auth, Theme, UILayout, AIPanel, Mentor, MissionContextProvider)
- Route protection (auth + onboarding gates)
- Accessibility, performance, and responsive design

### Frontend Does NOT Own

- Business logic (belongs in backend service layer)
- Problem selection (backend problem selector)
- Mission generation (backend mission engine)
- Assessment evaluation (backend assessment engine)
- Readiness scoring (backend mission engine)
- Roadmap unlock logic (backend roadmap engine)
- Any determination of which problems to show or in what order

---

## Scope

This constitution governs:

1. React page architecture (`src/pages/`)
2. Shared component design (`src/components/`)
3. Context provider model (`src/contexts/`)
4. API service layer (`src/services/`)
5. Routing model (`App.js`)
6. UX principles for Mission Control, Coding Arena, Assessment, Knowledge Base, AI Mentor, and Analytics

---

## Architectural Principles

### FE-001 — Backend Drives UI State

The backend determines what the user can do. The frontend renders what the backend says. UI state (which tasks are available, which problems are shown, what the CTA should be) MUST come from the API response — never from frontend computation.

### FE-002 — MissionContextProvider is the Central Context

`MissionContextProvider` is the React context that carries the active mission, today's learning objective, and the mission tasks throughout the app. All pages that need mission data MUST consume it from this provider — not fetch it independently.

### FE-003 — No Business Logic in Pages

React page components MUST NOT contain business logic. They MUST NOT:
- Compute which problem to show
- Determine if an assessment is available
- Score any learner data
- Make planning decisions

Pages render state. Services fetch state. Contexts distribute state.

### FE-004 — API Layer is the Only Communication Channel

All backend communication MUST go through `src/services/`. Pages MUST NOT contain `fetch()` or `axios` calls directly. Services MUST NOT be called from inside component render functions (use hooks or effects).

### FE-005 — Route Protection is Declarative

Protected routes are wrapped in `<ProtectedRoute>` and `<PublicOnlyRoute>` components. Auth and onboarding state come from `AuthContext`. Route protection MUST NOT be reimplemented per-page.

### FE-006 — CTA Comes from Backend

The call-to-action for a mission task (Open Coding Arena / Open Knowledge Base / Start Assessment) MUST come from the `MissionContext.cta` field returned by the backend. The frontend MUST NOT infer the CTA from the topic name, task kind, or any other heuristic.

### FE-007 — Theme is a Global Provider

Dark/light/system theme is managed by `ThemeProvider`. All components MUST use theme tokens — no hardcoded colors. No component may read `localStorage` for theme state independently.

### FE-008 — No Duplicate API Calls

The same API endpoint MUST NOT be called multiple times within one user session to get the same data. React Query or equivalent MUST be used for caching and deduplication. Fetching the daily mission 3 times in 3 seconds is unacceptable.

---

## Design Philosophy

The PrepOS frontend is the learner's daily interface. It must feel like a premium, personalized operating system for interview preparation — not a generic LMS. The experience philosophy:

1. **One screen, one focus:** Each page has a single primary action. The learner always knows what to do.
2. **State visibility:** The learner can always see their progress, streak, and what's next.
3. **Zero-friction navigation:** CTA buttons are always visible and correctly routed.
4. **Adaptive feedback:** The UI reacts to backend state — if today's mission requires revision, the UI emphasizes revision.
5. **AI as a layer:** The AI Mentor is a persistent, accessible panel — not a separate app.

---

## Context Provider Architecture

```
<ThemeProvider>               — dark/light/system theme
  <BrowserRouter>
    <AuthProvider>            — user session, auth state, onboarding status
      <UILayoutProvider>      — sidebar, panel visibility, responsive state
        <AIPanelProvider>     — AI Mentor panel open/closed state
          <MentorProvider>    — AI Mentor conversation state
            <MissionContextProvider>  — active mission, tasks, node context
              <Routes />
            </MissionContextProvider>
          </MentorProvider>
        </AIPanelProvider>
      </UILayoutProvider>
    </AuthProvider>
  </BrowserRouter>
</ThemeProvider>
```

### Provider Responsibilities

| Provider | Owns | Does NOT Own |
|----------|------|-------------|
| `AuthProvider` | JWT session, user profile, onboarding status | Routing, theme |
| `ThemeProvider` | Active theme resolution, CSS variable injection | Any data fetching |
| `UILayoutProvider` | Sidebar state, panel visibility, viewport | Any learner data |
| `AIPanelProvider` | AI Mentor panel visibility state | Mentor messages or conversation |
| `MentorProvider` | Mentor conversation history, active session | Mission state |
| `MissionContextProvider` | Today's mission, tasks, node context, readiness | Problem selection, assessment |

---

## Route Structure

| Route | Page | Auth Required | Onboarding Required |
|-------|------|--------------|-------------------|
| `/login` | Login | ❌ (public only) | ❌ |
| `/register` | Register | ❌ (public only) | ❌ |
| `/forgot-password` | ForgotPassword | ❌ (public only) | ❌ |
| `/reset-password` | ResetPassword | ❌ | ❌ |
| `/onboarding` | MissionInit | ✅ | ❌ |
| `/app/mission-control` | MissionControl | ✅ | ✅ |
| `/app/coding-arena` | CodingArena | ✅ | ✅ |
| `/app/assessment/:missionId` | Assessment | ✅ | ✅ |
| `/app/system-design` | SystemDesign | ✅ | ✅ |
| `/app/knowledge-base` | KnowledgeBase | ✅ | ✅ |
| `/app/knowledge-base/nodes/:nodeId` | DeepTopicPage | ✅ | ✅ |
| `/app/ai-mentor` | AIMentor | ✅ | ✅ |
| `/app/analytics` | CommandAnalytics | ✅ | ✅ |
| `/app/settings` | Settings | ✅ | ✅ |
| `/app/profile` | Profile | ✅ | ✅ |

`AppShell` wraps all `/app/*` routes with the navigation shell (sidebar, header).

---

## Page Responsibilities

### Mission Control (`/app/mission-control`)

**Purpose:** The learner's daily dashboard and primary interaction surface.

**Must show:**
- Today's mission (title, focus area, difficulty, learning objective)
- Task list with completion toggles
- Study streak
- Revision queue (top items due)
- Progress summary
- Recommendation insight ("why today's mission")
- CTA button linked to primary task's `cta.action`

**Must NOT:**
- Compute which tasks to show (backend provides `DailyMission.tasks`)
- Determine if the assessment checkpoint is available (backend provides `assessment_available`)
- Re-order or filter tasks beyond what the backend returns

### Coding Arena (`/app/coding-arena`)

**Purpose:** Present today's representative problem and collect feedback.

**Must show:**
- Problem title, difficulty, LeetCode link
- Estimated time
- Feedback form (confidence 1-10, solved status, time taken, notes)
- "Next Problem" affordance (exclusion-aware via backend)

**Must NOT:**
- Select which problem to show (calls `GET /api/arena/problem`)
- Determine problem difficulty independently
- Allow submission of test results (linking to LeetCode; not running code in PrepOS)

### Assessment (`/app/assessment/:missionId`)

**Purpose:** Walk the learner through the assessment lifecycle (pending → submit → results).

**Must show:**
- Question details from `GET /api/assessment/{id}`
- Submission form (passed_tests, code, explanation, time_taken)
- Results (score, feedback, evidence, recommendation)

**Must NOT:**
- Select assessment problems
- Evaluate submissions
- Compute scores

### Knowledge Base (`/app/knowledge-base`)

**Purpose:** The roadmap tree and node content browser.

**Must show:**
- Full roadmap tree (tracks → modules → topics → nodes)
- Per-node progress, confidence, mastery
- Node content (theory, examples, tips, flashcards — from `GET /api/roadmap/node/{id}/content`)
- "Generate content" affordance (calls backend generation)
- Confidence update UI

**Must NOT:**
- Generate content (calls backend)
- Compute progress rollups (backend returns `build_canonical_progress()` output)

### DeepTopicPage (`/app/knowledge-base/nodes/:nodeId`)

**Purpose:** Full-page view of a single roadmap node with AI-generated content.

**Must:** Call `GET /api/roadmap/node/{id}/content` and render the full schema.

**Must NOT:** Call the LLM directly or format content beyond displaying what the backend returns.

### AI Mentor (`/app/ai-mentor`)

**Purpose:** Multi-turn chat with the AI Mentor.

**Must show:**
- Conversation history
- Message input
- Active node context indicator (if `node_id` context is set)

**Must NOT:**
- Build the mentor context (backend assembles it per turn)
- Access learner state directly

### Analytics (`/app/analytics`)

**Purpose:** Progress visualization across tracks, patterns, and time.

**Must show:**
- Overall + per-track readiness scores
- Company readiness bars
- Mastery heatmap
- Streak grid
- Activity timeline

**Must NOT:**
- Compute readiness scores (backend computes them)
- Derive mastery from raw data

---

## API Service Layer Rules

- All API calls MUST be in `src/services/*.js` files
- Services MUST be plain JS modules (not classes)
- Services MUST return parsed JSON (or throw on error)
- Services MUST NOT contain rendering logic
- Authentication headers/cookies MUST be attached by the service layer — not by individual pages

---

## Component Design Rules

### Shared Components (`src/components/`)

- Shared components MUST be purely presentational
- They receive data via props; they do not fetch
- They emit events via callbacks; they do not navigate
- No business logic inside shared components

### Page Components (`src/pages/`)

- May use hooks to fetch data (via service layer)
- May compute derived display values (e.g., `completionPercent = completed / total * 100`)
- MUST NOT re-implement any backend business rule
- MUST NOT call APIs in render functions (use `useEffect` or React Query)

---

## UX Principles

### UP-001 — Mission-First Home

Every user arriving after login sees `Mission Control` as their first screen. There is no generic dashboard — the mission IS the dashboard.

### UP-002 — Progressive Disclosure

Complex features (AI Mentor full context, detailed assessment rubrics, LI signals) are accessible but not surfaced by default. Primary surfaces show what the learner needs to act on today.

### UP-003 — Sticky CTA

Today's primary CTA (e.g., "Open Coding Arena") MUST be visible at all times on Mission Control without scrolling on standard desktop viewport.

### UP-004 — Real Progress Feedback

Progress bars, completion percentages, and streak counts MUST always reflect the most recent server state. Optimistic updates are acceptable for task toggles but MUST reconcile with server state within 1 request cycle.

### UP-005 — Accessible by Default

All interactive elements MUST have accessible labels. Color MUST NOT be the only indicator of state. Focus management MUST be correct for modals and panels.

---

## State Management Rules

| State Type | Storage |
|-----------|---------|
| User session / auth | `AuthContext` (in-memory) |
| Today's mission | `MissionContextProvider` (in-memory, refreshed per session) |
| Theme preference | `ThemeProvider` (reads from `UserSettings`, syncs with localStorage) |
| AI panel open/closed | `AIPanelProvider` (in-memory) |
| Mentor conversation | `MentorProvider` (in-memory + synced with backend) |
| Roadmap tree data | Local component state or React Query cache |
| Problem feedback form | Local component state (ephemeral) |

Global state MUST NOT include derived data (readiness scores, progress rollups) — these come from the API and are cached by React Query.

---

## Invariants

1. No API calls in React render functions.
2. `MissionContextProvider` is the single source of mission state — no component fetches the mission independently.
3. CTA actions always route to the correct page as defined by `MissionContext.cta.action`.
4. Theme preference is always synced with `UserSettings` — local override is temporary only.
5. Protected routes ALWAYS redirect to `/login` on unauthenticated access.

---

## Anti-patterns

❌ Business logic in React page components  
❌ `fetch()` calls inside JSX or render functions  
❌ Hardcoded problem IDs or node IDs in frontend code  
❌ Deriving the CTA from task title strings  
❌ Re-computing progress rollups in the frontend  
❌ Two components both fetching the same API endpoint without caching  
❌ Storing sensitive data (JWT, API keys) in localStorage  
❌ Making the AI Mentor context-aware on the frontend (context assembly is backend-only)  
❌ Importing backend Python types or schemas into frontend code  

---

## Future Evolution

- **Mobile app:** The REST API surface is the integration point. A React Native app consumes the same API. The context provider model maps to React Native context without architecture changes.
- **Progressive Web App (PWA):** Add service worker + offline manifest. Mission data can be cached for offline reading. Problem feedback submission queues for later sync.
- **Real-time updates:** WebSocket subscription for mission completion events, revision reminders, and streak notifications. `MissionContextProvider` subscribes to a WebSocket channel for live updates.
- **Dark mode system-level detection:** `ThemeProvider` already supports `system` theme. Full system-level detection (prefers-color-scheme media query) is a styling enhancement only.
- **Micro-frontends:** If PrepOS scales to a team of frontend engineers, each major page (Mission Control, Coding Arena, AI Mentor) MAY be extracted to a micro-frontend. The context provider model and API service layer remain the integration boundary.
