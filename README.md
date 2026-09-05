<p align="center">
  <strong>PrepOS</strong> — AI Interview Operating System
</p>

<p align="center">
  <em>An AI-powered, adaptive interview preparation platform for product-based company interviews.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-19.0-61DAFB?logo=react&logoColor=white" alt="React 19" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-06B6D4?logo=tailwindcss&logoColor=white" alt="TailwindCSS" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/License-Private-red" alt="License" />
</p>

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Core Engines & Services](#core-engines--services)
- [Frontend Architecture](#frontend-architecture)
- [Design System](#design-system)
- [Testing](#testing)
- [Engineering Constitution](#engineering-constitution)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**PrepOS** is a premium, multi-user SaaS platform designed to be an **AI-powered Interview Operating System**. It provides a structured, adaptive, and personalized interview preparation experience targeting product-based companies (Google, Amazon, Microsoft, Adobe, Atlassian, Stripe, Uber, Flipkart, and more).

The platform operates on a **daily mission** model — each day, the system generates a tailored study plan based on the learner's current knowledge state, target companies, interview timeline, and historical performance. An AI Mentor provides contextual guidance, while the Assessment Engine measures progress through deterministic evaluation.

The design philosophy is inspired by **Linear, Vercel, and Cursor** — a premium dark-first command center for elite engineers.

---

## Key Features

### Adaptive Learning System
- **Daily Mission Engine** — One personalized mission per day, deterministically generated based on learner state, pacing, company weights, and spaced-repetition schedules
- **Learning Engine** — Multi-signal ranking, candidate generation, eligibility filtering, composition planning, and ROI-based prioritization
- **Spaced Repetition** — 5-stage revision scheduling (1d → 3d → 7d → 14d → 30d) integrated into mission planning
- **Knowledge Graph** — Hierarchical roadmap (Track → Module → Topic → Subtopic → Learning Node) with ~2.8MB versioned curriculum data

### AI-Powered Features
- **AI Mentor** — Context-grounded conversational assistant with full learner state awareness (progress, missions, company targets, knowledge gaps)
- **AI Knowledge Base** — On-demand AI-generated theory, examples, interview tips, flashcards, and common mistakes for every roadmap node (globally cached, first-requester-pays)
- **AI Gateway** — Provider-agnostic abstraction layer using OpenRouter first with Gemini fallback, supporting multiple model families through gateway configuration

### Assessment & Intelligence
- **Assessment Engine** — Deterministic evaluation with rubric-based scoring, immutable evidence trail, difficulty calibration, and feedback generation
- **Learner Intelligence** — 10 deterministic signals (confidence, coding proficiency, consistency, difficulty calibration, mastery trends, velocity, readiness, retention, revision health, weakness detection) that nudge mission planning
- **Company Intelligence** — Compile-time company profiles with weighted readiness scoring per target company

### Coding Practice
- **Coding Arena** — Adaptive problem selection from a curated LeetCode-mapped problem bank (600+ problems across 25+ patterns)
- **Problem Feedback Loop** — Confidence ratings, solve status, time tracking, and weakness detection that feed back into the learning engine
- **Pattern-Based Progression** — Problems organized by algorithmic patterns with prerequisite chains

### User Experience
- **7-Step Onboarding Wizard** — Target companies, experience level, daily study hours, self-assessment, interview date, animated mission initialization
- **Mission Control Dashboard** — Bento-grid layout with Today's Mission, Interview Readiness, Study Streak, Upcoming Revisions, Knowledge Progress, Recent Activity
- **Command Palette** — Global Cmd+K search and quick actions
- **AI Assistant Panel** — Docked collapsible panel with context-aware mentoring
- **Dark/Light/System Theme** — Full theme support with premium glassmorphism design
- **Email Notifications** — Verification emails, password reset flows via SMTP

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  React 19 · TailwindCSS · shadcn/ui · Framer Motion        │
│  React Router 7 · TanStack Query · Axios · Recharts        │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (JSON)
                           │ JWT httpOnly cookies
┌──────────────────────────▼──────────────────────────────────┐
│                     FASTAPI BACKEND                         │
│                                                             │
│  ┌──────────┐  ┌───────────┐  ┌───────────┐  ┌──────────┐  │
│  │  Auth    │  │  Mission  │  │  Roadmap  │  │   AI     │  │
│  │  Routes  │  │  Routes   │  │  Routes   │  │  Mentor  │  │
│  └────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬─────┘  │
│       │              │              │              │        │
│  ┌────▼──────────────▼──────────────▼──────────────▼─────┐  │
│  │              SERVICE LAYER                            │  │
│  │                                                       │  │
│  │  Mission Engine · Learning Engine · Assessment Engine  │  │
│  │  Progress Engine · Revision Engine · Streak Engine     │  │
│  │  Learner Intelligence · Company Intelligence           │  │
│  │  Problem Selection · AI Gateway · Email Service        │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │              DATA LAYER                               │  │
│  │  MongoDB (Motor async) · Roadmap JSON · Problem Bank  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Flow (Unidirectional)

```
Routes → Services → Data
  │         │
  │         ├── Learning Engine → Roadmap + Problem Bank (static)
  │         ├── Mission Engine → Learning Engine + Composition
  │         ├── Assessment Engine → Evidence (immutable)
  │         ├── Learner Intelligence → Knowledge Nodes (read-only signals)
  │         ├── AI Mentor → Context Builder → All read-only data
  │         └── Company Intelligence → Compiled registry (read-only)
  │
  └── Never: Route → Route, Service ↔ Service (circular)
```

---

## Tech Stack

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| React | 19.0 | UI framework (CRA + CRACO) |
| React Router | 7.15 | Client-side routing |
| TailwindCSS | 3.4 | Utility-first CSS framework |
| shadcn/ui | — | Radix-based component library |
| Framer Motion | 11.18 | Animations and transitions |
| TanStack Query | 5.56 | Server state management |
| Axios | 1.18 | HTTP client |
| Recharts | 3.6 | Data visualization / charts |
| Lucide React | 0.516 | Icon library |
| Zod | 3.24 | Schema validation |
| React Hook Form | 7.56 | Form management |
| Sonner | 2.0 | Toast notifications |
| date-fns / dayjs | — | Date utilities |
| cmdk | 1.1 | Command palette |
| react-markdown | 10.1 | Markdown rendering |

### Backend

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.110.1 | Async web framework |
| Motor | 3.3.1 | Async MongoDB driver |
| PyMongo | 4.6.3 | MongoDB driver (sync fallback) |
| Pydantic | 2.6+ | Data validation & schemas |
| PyJWT | 2.10+ | JSON Web Token handling |
| bcrypt | 4.1.3 | Password hashing |
| python-dotenv | 1.0+ | Environment config |
| certifi | — | TLS certificate verification |
| Pandas | 2.2+ | Data processing |
| NumPy | 1.26+ | Numerical computing |
| Typer | 0.9+ | CLI tooling |
| PyYAML | 6.0+ | YAML parsing |
| pytest | 8.0+ | Test framework |
| pytest-xdist | 3.6+ | Parallel test execution |
| Black | 24.1+ | Code formatting |
| isort | 5.13+ | Import sorting |
| Flake8 | 7.0+ | Linting |
| mypy | 1.8+ | Static type checking |

### Infrastructure

| Technology | Purpose |
|---|---|
| MongoDB Atlas | Cloud database (TLS via `mongodb+srv://`) |
| SMTP (Gmail) | Transactional email delivery |
| Gemini API | Default AI provider (via AI Gateway) |

---

## Project Structure

```
InterviewPrep/
├── backend/                          # FastAPI backend application
│   ├── server.py                     # Application entrypoint, CORS, startup hooks
│   ├── models.py                     # Pydantic schemas (Auth, Onboarding, Missions, etc.)
│   ├── auth_utils.py                 # JWT + bcrypt auth utilities
│   ├── email_service.py              # SMTP email service (verification, password reset)
│   ├── mission_engine.py             # V2 adaptive mission builder
│   ├── roadmap.py                    # Roadmap engine (topic hierarchy, node lookup)
│   ├── problem_bank.py               # Curated problem catalog (600+ LeetCode problems)
│   ├── ai_service.py                 # AI service façade
│   ├── knowledge_generation.py       # AI-generated content caching
│   ├── prompt_builder.py             # AI prompt construction
│   │
│   ├── routes_auth.py                # /api/auth/* endpoints
│   ├── routes_user.py                # /api/profile, /api/settings endpoints
│   ├── routes_missions.py            # /api/missions/* + dashboard + coding arena
│   ├── routes_roadmap.py             # /api/roadmap/* + knowledge graph
│   ├── routes_companies.py           # /api/companies/* endpoints
│   ├── routes_leetcode_catalog.py    # /api/leetcode-catalog/* endpoints
│   ├── routes_mission_assessment.py  # /api/missions/*/assessment endpoints
│   │
│   ├── ai_gateway/                   # Provider-agnostic AI abstraction
│   │   ├── gateway.py                # Core gateway logic
│   │   ├── models.py                 # AIRequest, AIResponse, AICapability
│   │   ├── routing.py                # Provider routing logic
│   │   └── providers/               # Provider implementations
│   │       ├── base.py               # Abstract base provider
│   │       └── gemini.py             # Google Gemini provider
│   │
│   ├── ai_mentor/                    # AI Mentor subsystem
│   │   ├── mentor_routes.py          # /api/mentor/* endpoints
│   │   ├── mentor_service.py         # Conversation orchestration
│   │   ├── mentor_prompt.py          # System prompt builder
│   │   ├── context_builder.py        # Learner context aggregation
│   │   ├── conversation_store.py     # Conversation persistence
│   │   ├── mission_planner.py        # AI narrative generation
│   │   └── models.py                 # Mentor-specific schemas
│   │
│   ├── assessment/                   # Assessment Engine
│   │   ├── assessment_engine.py      # Core assessment logic
│   │   ├── assessment_generator.py   # Question generation
│   │   ├── evaluation_engine.py      # Deterministic evaluation
│   │   ├── evidence.py               # Immutable evidence records
│   │   ├── feedback_engine.py        # Feedback generation
│   │   ├── rubrics.py                # Scoring rubrics
│   │   ├── schemas.py                # Assessment schemas
│   │   └── prompts/                  # Assessment prompt templates
│   │
│   ├── company_intelligence/         # Company Intelligence Engine
│   │   ├── compiler.py               # Compile-time profile builder
│   │   ├── scoring.py                # Readiness scoring
│   │   ├── bias_engine.py            # Bias detection
│   │   ├── explainability.py         # Score explanations
│   │   ├── loader.py                 # Data loading
│   │   ├── registry.json             # Company registry
│   │   └── schema_validator.py       # Schema validation
│   │
│   ├── leetcode_catalog/             # LeetCode problem catalog
│   │   ├── repository.py             # Problem queries
│   │   ├── importer.py               # Data import tools
│   │   └── data/                     # Catalog data files
│   │
│   ├── services/                     # Core service layer
│   │   ├── learning_engine/          # Learning Engine (21 modules)
│   │   │   ├── planner.py            # Daily node selection
│   │   │   ├── ranking.py            # Multi-signal node scoring
│   │   │   ├── candidates.py         # Candidate generation
│   │   │   ├── eligibility.py        # Prerequisite enforcement
│   │   │   ├── composition.py        # Mission task-mix planning
│   │   │   ├── context.py            # Learner context assembly
│   │   │   ├── stage_engine.py       # Learning stage management
│   │   │   ├── subject_progression.py# Cross-subject progression
│   │   │   ├── adaptive_weights.py   # Dynamic weight tuning
│   │   │   ├── company_context.py    # Company-aware planning
│   │   │   ├── priority_engine.py    # Priority scoring
│   │   │   ├── cold_start.py         # New user bootstrapping
│   │   │   ├── companion.py          # Companion task selection
│   │   │   ├── foresight.py          # Future topic prediction
│   │   │   ├── insight.py            # Recommendation explainability
│   │   │   ├── pacing.py             # Interview timeline pacing
│   │   │   ├── revision.py           # Revision integration
│   │   │   ├── roi.py                # Learning ROI calculation
│   │   │   ├── unlock.py             # Node unlock logic
│   │   │   └── builder.py            # Node builder utilities
│   │   │
│   │   ├── learner_intelligence/     # Learner Intelligence (23 modules)
│   │   │   ├── engine.py             # Signal aggregation
│   │   │   ├── coding.py             # Coding proficiency signal
│   │   │   ├── confidence.py         # Confidence signal
│   │   │   ├── consistency.py        # Study consistency signal
│   │   │   ├── difficulty.py         # Difficulty calibration
│   │   │   ├── mastery_trend.py      # Mastery trend analysis
│   │   │   ├── velocity.py           # Learning velocity
│   │   │   ├── readiness.py          # Interview readiness
│   │   │   ├── retention.py          # Knowledge retention
│   │   │   ├── revision_health.py    # Revision schedule health
│   │   │   ├── weakness.py           # Weakness detection
│   │   │   ├── trend_analysis.py     # Trend analysis
│   │   │   ├── explainability.py     # Signal explanations
│   │   │   ├── metrics.py            # LI metrics
│   │   │   ├── snapshot.py           # State snapshots
│   │   │   ├── learner_state.py      # Learner state model
│   │   │   ├── learner_update.py     # State update logic
│   │   │   ├── evidence_integration.py # Assessment evidence integration
│   │   │   ├── planner_adapter.py    # LI → Planner bridge
│   │   │   ├── context.py            # LI context assembly
│   │   │   └── evidence_api.py       # REST endpoints
│   │   │
│   │   ├── problem_selection/        # Problem selection service
│   │   │   └── selector.py           # Adaptive problem picker
│   │   │
│   │   ├── curriculum/               # Curriculum sync service
│   │   │   └── activity_metadata.py  # Activity metadata
│   │   │
│   │   ├── roadmap_progress/         # Roadmap progress tracking
│   │   ├── progress_engine.py        # Canonical progress computation
│   │   ├── progress_repository.py    # Progress data access
│   │   ├── revision_engine.py        # Spaced repetition engine
│   │   ├── streak_engine.py          # Study streak tracking
│   │   └── mission_context.py        # Mission context builder
│   │
│   ├── data/                         # Static data files
│   │   └── roadmap_v1.json           # Master roadmap (~2.8MB, versioned)
│   │
│   ├── tests/                        # Backend test suite (39 test files)
│   ├── scripts/                      # Utility scripts
│   ├── requirements.txt              # Python dependencies
│   ├── pytest.ini                    # Test configuration (xdist parallel)
│   └── .env                          # Environment variables (not committed)
│
├── frontend/                         # React frontend application
│   ├── package.json                  # Dependencies and scripts
│   ├── tailwind.config.js            # Tailwind + design token config
│   ├── craco.config.js               # CRA overrides (path aliases)
│   ├── postcss.config.js             # PostCSS configuration
│   │
│   └── src/
│       ├── App.js                    # Root component + routing
│       ├── index.js                  # Application entrypoint
│       ├── index.css                 # Global styles + CSS variables
│       ├── App.css                   # App-level styles
│       │
│       ├── pages/                    # Page components
│       │   ├── auth/                 # Login, Register, ForgotPassword, ResetPassword
│       │   ├── onboarding/           # MissionInit (7-step wizard)
│       │   ├── dashboard/            # MissionControl (main dashboard)
│       │   ├── coding/               # CodingArena
│       │   ├── knowledge/            # KnowledgeBase, DeepTopicPage
│       │   ├── ai-mentor/            # AIMentor chat interface
│       │   ├── assessment/           # Assessment checkpoint
│       │   ├── system-design/        # SystemDesign practice
│       │   ├── analytics/            # CommandAnalytics dashboard
│       │   ├── settings/             # Settings page
│       │   ├── profile/              # User profile
│       │   └── notifications/        # NotificationsPage
│       │
│       ├── components/               # Reusable components
│       │   ├── ui/                   # shadcn/ui primitives (46 components)
│       │   ├── layout/               # AppShell, Sidebar, Topbar, CommandPalette,
│       │   │                         # AIAssistantPanel, MobileNav, AuthLayout
│       │   ├── dashboard/            # Dashboard widgets
│       │   ├── mission/              # Mission-specific components
│       │   ├── knowledge/            # Knowledge base components
│       │   ├── mentor/               # Mentor chat components
│       │   ├── progress/             # Progress visualization
│       │   └── common/               # Shared utilities
│       │
│       ├── contexts/                 # React context providers
│       │   ├── AuthContext.jsx        # Authentication state
│       │   ├── ThemeContext.jsx        # Dark/light/system theme
│       │   ├── AIPanelContext.jsx      # AI panel state
│       │   ├── MentorContext.jsx       # Mentor chat state
│       │   ├── MissionContextProvider.jsx # Mission data
│       │   ├── UILayoutContext.jsx     # Layout state
│       │   └── CommandPaletteContext.jsx # Cmd+K state
│       │
│       ├── services/                 # API service layer
│       │   ├── api.js                # Axios instance configuration
│       │   ├── auth.service.js       # Auth API calls
│       │   └── mission.service.js    # Mission API calls
│       │
│       ├── hooks/                    # Custom React hooks
│       │   ├── useAIContent.js       # AI content fetching
│       │   ├── useMentor.js          # Mentor interactions
│       │   ├── useProgressTree.js    # Progress tree data
│       │   ├── useRecentlyViewed.js  # Recently viewed tracking
│       │   └── use-toast.js          # Toast hook
│       │
│       ├── queries/                  # TanStack Query definitions
│       ├── config/                   # App configuration
│       ├── constants/                # Shared constants
│       ├── lib/                      # Utility functions
│       └── utils/                    # Helper utilities
│
├── constitution/                     # Engineering Constitution (12 docs)
│   ├── CONSTITUTION-001-System-Architecture.md
│   ├── CONSTITUTION-002-Curriculum-Engine.md
│   ├── CONSTITUTION-003-Mission-Engine.md
│   ├── CONSTITUTION-004-Learner-Intelligence.md
│   ├── CONSTITUTION-005-Assessment-Engine.md
│   ├── CONSTITUTION-006-AI-Mentor.md
│   ├── CONSTITUTION-007-Company-Intelligence.md
│   ├── CONSTITUTION-008-Content-Architecture.md
│   ├── CONSTITUTION-009-Frontend-Experience.md
│   ├── CONSTITUTION-010-Development-Rules.md
│   ├── CONSTITUTION-011-Data-Contracts.md
│   └── CONSTITUTION-012-Testing-and-Quality.md
│
├── docs/                             # Documentation
│   ├── architecture/                 # Architecture docs
│   │   ├── system-overview.md
│   │   ├── backend-architecture.md
│   │   └── frontend-architecture.md
│   ├── adr/                          # Architecture Decision Records
│   ├── assessment-engine/            # Assessment engine docs
│   ├── curriculum/                   # Curriculum documentation
│   ├── database/                     # Database schema docs
│   ├── deployment/                   # Deployment guides
│   ├── frontend/                     # Frontend documentation
│   ├── learning-engine/              # Learning engine docs
│   └── research/                     # Research notes
│
├── memory/                           # Project memory
│   └── PRD.md                        # Product Requirements Document
│
├── test_reports/                     # Test result history
├── tests/                            # Root-level test config
├── design_guidelines.json            # UI/UX design system spec
├── auth_testing.md                   # Auth testing playbook
└── .gitignore                        # Git ignore rules
```

---

## Getting Started

### Prerequisites

- **Python** 3.10+
- **Node.js** 18+ and **Yarn** 1.22+
- **MongoDB** (local instance or MongoDB Atlas connection string)
- **Gemini API Key** (for AI features)

### Backend Setup

```bash
# 1. Navigate to the backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables (see Environment Variables section)
cp .env.example .env   # or create .env manually

# 5. Start the development server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Health check: `GET http://localhost:8000/api/health`

### Frontend Setup

```bash
# 1. Navigate to the frontend directory
cd frontend

# 2. Install dependencies
yarn install

# 3. Start the development server
yarn start
```

The frontend will be available at `http://localhost:3000`.

### Environment Variables

Create a `backend/.env` file with the following variables:

```env
# ─── Database ───
MONGO_URL=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>?retryWrites=true&w=majority
DB_NAME=prepos_db

# ─── Authentication ───
JWT_SECRET=<your-256-bit-hex-secret>
ADMIN_EMAIL=admin@prepos.io
ADMIN_PASSWORD=Admin@123

# ─── CORS ───
CORS_ORIGINS=http://localhost:3000
FRONTEND_URL=http://localhost:3000

# ─── AI Provider ───
GEMINI_API_KEY=<your-gemini-api-key>
EMERGENT_LLM_KEY=<your-llm-key>
EMERGENT_LLM_MODEL=gemini-2.5-flash

# ─── Email (SMTP) ───
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=<your-email>
EMAIL_PASSWORD=<your-app-password>
EMAIL_FROM_ADDRESS=PrepOS <noreply@yourdomain.com>
```

> **Note:** On first startup, the backend automatically seeds an admin user using `ADMIN_EMAIL` and `ADMIN_PASSWORD`, creates MongoDB indexes, and runs roadmap data migrations.

---

## API Reference

All endpoints are prefixed with `/api`. Authentication uses JWT tokens stored in httpOnly cookies.

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user (email, password, name) |
| `POST` | `/api/auth/login` | Login and receive JWT cookies |
| `POST` | `/api/auth/logout` | Clear auth cookies |
| `GET` | `/api/auth/me` | Get current authenticated user |
| `POST` | `/api/auth/refresh` | Refresh expired access token |
| `POST` | `/api/auth/forgot-password` | Send password reset email |
| `POST` | `/api/auth/reset-password` | Reset password with token |
| `POST` | `/api/auth/resend-verification` | Resend email verification |
| `GET` | `/api/auth/verify-email` | Verify email address |

### User (`/api`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/onboarding` | Get onboarding state |
| `POST` | `/api/onboarding` | Submit onboarding data |
| `PATCH` | `/api/onboarding` | Update onboarding preferences |
| `GET` | `/api/profile` | Get user profile |
| `PATCH` | `/api/profile` | Update profile (name, avatar, bio, headline) |
| `GET` | `/api/settings` | Get user settings |
| `PATCH` | `/api/settings` | Update settings (theme, AI config, notifications) |

### Missions (`/api/missions`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/missions/today` | Get or generate today's mission |
| `POST` | `/api/missions/{id}/tasks/{tid}/toggle` | Toggle task completion |
| `POST` | `/api/missions/{id}/complete` | Complete a mission |
| `POST` | `/api/missions/{id}/skip` | Skip a mission |
| `GET` | `/api/missions/history` | Get mission history |

### Dashboard (`/api`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard` | Full dashboard data (mission, readiness, streak, etc.) |
| `GET` | `/api/readiness` | Interview readiness score |
| `GET` | `/api/streak` | Current study streak |
| `GET` | `/api/streak/grid` | Streak calendar heatmap data |
| `GET` | `/api/activity` | Recent activity feed |
| `GET` | `/api/notifications` | User notifications |

### Roadmap & Knowledge (`/api/roadmap`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/roadmap/tree` | Full roadmap tree with progress |
| `GET` | `/api/roadmap/nodes/{id}` | Node details + AI content |
| `GET` | `/api/roadmap/nodes/{id}/content` | AI-generated knowledge content |
| `POST` | `/api/roadmap/nodes/{id}/content/regenerate` | Regenerate AI content |
| `PATCH` | `/api/roadmap/nodes/{id}/notes` | Update personal notes |
| `PATCH` | `/api/roadmap/nodes/{id}/confidence` | Update confidence rating |
| `PATCH` | `/api/roadmap/nodes/{id}/status` | Update completion status |
| `POST` | `/api/roadmap/nodes/{id}/attempt` | Record a practice attempt |

### Coding Arena (`/api`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/coding-arena/problems` | Get assigned problems |
| `POST` | `/api/coding-arena/practice-more` | Request additional problems |
| `POST` | `/api/problems/{id}/feedback` | Submit problem feedback |

### AI Mentor (`/api/mentor`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/mentor/conversations` | List conversations |
| `POST` | `/api/mentor/conversations` | Create new conversation |
| `GET` | `/api/mentor/conversations/{id}` | Get conversation messages |
| `POST` | `/api/mentor/conversations/{id}/messages` | Send message to mentor |
| `DELETE` | `/api/mentor/conversations/{id}` | Delete conversation |

### Assessment (`/api/assessment`)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/assessment/start` | Start an assessment session |
| `POST` | `/api/assessment/submit` | Submit assessment answers |
| `GET` | `/api/assessment/history` | Get assessment history |

### Companies (`/api/companies`)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/companies` | List supported companies |
| `GET` | `/api/companies/{id}` | Company profile + readiness |

---

## Core Engines & Services

### Mission Engine (`mission_engine.py`)
The adaptive mission builder. Generates one daily mission per user with:
- **Feedback-driven adaptation** — Tomorrow's mission adjusts based on today's confidence, hint usage, and time performance
- **Prerequisite insertion** — Detects weaknesses and inserts root-cause revision tasks
- **Company weighting** — Missions prioritize topics based on target company interview weights
- **Deterministic composition** — Same inputs always produce the same mission (seeded randomness)

### Learning Engine (`services/learning_engine/`)
A 21-module system responsible for deciding **what to learn next**:
- **Planner** — Selects today's learning node from scored candidates
- **Ranking** — Multi-signal scoring (ROI, weakness, company importance, pacing urgency, continuity)
- **Composition** — Plans the task mix (study/practice/revision ratios)
- **Eligibility** — Enforces prerequisite chains before unlocking nodes
- **Pacing** — Calibrates study velocity against the interview target date
- **Cold Start** — Bootstraps new users with appropriate starting nodes

### Assessment Engine (`assessment/`)
Deterministic evaluation system:
- **Evidence is immutable** — Once created, assessment evidence can never be modified
- **Engine exposes, never applies** — Produces evidence; other engines consume it
- **Rubric-based scoring** — Consistent, explainable evaluation criteria
- **Difficulty calibration** — Adapts question difficulty based on learner level

### Learner Intelligence (`services/learner_intelligence/`)
10 deterministic signals that provide **bounded nudges** (never hard vetoes) to the planner:
1. Confidence · 2. Coding Proficiency · 3. Consistency · 4. Difficulty Calibration · 5. Mastery Trends · 6. Velocity · 7. Readiness · 8. Retention · 9. Revision Health · 10. Weakness Detection

### AI Gateway (`ai_gateway/`)
Provider-agnostic AI abstraction:
- Singleton gateway with lazy initialization
- Pluggable provider architecture (OpenRouter preferred, Gemini fallback)
- Structured request/response models (`AIRequest`, `AIResponse`, `AICapability`)
- Routing logic for provider selection

### AI Mentor (`ai_mentor/`)
Context-grounded conversational AI:
- **Read-only** — Never modifies learner state
- **Full context awareness** — Sees current mission, progress, company targets, knowledge gaps
- **Provider-agnostic** — Works through the AI Gateway
- **Globally cached knowledge base** — First-requester-pays for content generation

---

## Frontend Architecture

### Routing

```
/                     → RootRedirect (→ /login or /app/mission-control)
/login                → Login (public only)
/register             → Register (public only)
/forgot-password      → ForgotPassword (public only)
/reset-password       → ResetPassword
/onboarding           → MissionInit (auth required, no onboarding check)
/app/*                → AppShell (auth + onboarding required)
  ├── mission-control → MissionControl (main dashboard)
  ├── coding-arena    → CodingArena
  ├── system-design   → SystemDesign
  ├── knowledge-base  → KnowledgeBase
  ├── knowledge-base/nodes/:nodeId → DeepTopicPage
  ├── ai-mentor       → AIMentor
  ├── assessment/:missionId → Assessment
  ├── analytics       → CommandAnalytics
  ├── notifications   → NotificationsPage
  ├── settings        → Settings
  └── profile         → Profile
```

### Context Providers

The app wraps these providers (outer → inner):
```
ThemeProvider → BrowserRouter → AuthProvider → UILayoutProvider
  → AIPanelProvider → MentorProvider → MissionContextProvider
```

### Component Architecture
- **UI primitives**: 46 shadcn/ui components (Radix-based)
- **Layout**: AppShell with Sidebar, Topbar, MobileNav, CommandPalette, AIAssistantPanel
- **State management**: React Context + TanStack Query for server state
- **Forms**: React Hook Form + Zod validation
- **Notifications**: Sonner toast library

---

## Design System

The UI follows a **premium dark-first** design language (Linear/Vercel/Cursor inspired):

| Token | Value | Purpose |
|---|---|---|
| Background | `#0B0F19` | Near-black primary background |
| Surface | `#131825` | Elevated surface cards |
| Surface Glass | `rgba(19, 24, 37, 0.6)` | Glassmorphism panels |
| Primary | `#6366F1` | Cool Indigo accent (CTAs) |
| Secondary | `#3B82F6` | Blue secondary accent |
| Text Primary | `#F8FAFC` | High-contrast text |
| Text Secondary | `#94A3B8` | Muted/secondary text |
| Border | `rgba(255,255,255,0.08)` | Subtle 1px borders |

### Typography
- **Headings**: Outfit (tracking-tight for >32px)
- **Body**: Manrope
- **Code/Labels**: JetBrains Mono (uppercase, wide spacing for overlines)

### Visual Effects
- Dark glassmorphism: `backdrop-blur-xl bg-[#131825]/60 border border-white/10`
- Tracing beam borders on high-conversion cards
- Staggered entrance animations for lists
- Micro-animations on all hover states
- Glow animation keyframe (subtle indigo pulsing box shadow)

Full design specification: [`design_guidelines.json`](design_guidelines.json)

---

## Testing

### Backend Tests

The backend has a comprehensive test suite with **39 test files** covering:

- Unit tests for all core engines (Mission, Learning, Assessment, LI)
- Integration tests for API routes
- Regression tests for known bugs
- Phase-specific feature tests (Phase 2–4, iterations 1–12)

```bash
# Run all tests (parallel, 2 workers)
cd backend
pytest

# Run a specific test file
pytest tests/test_missions.py

# Run tests serially (for debugging)
pytest -n 0

# Run with verbose output
pytest -v
```

Test configuration uses `pytest-xdist` with 2 workers and `loadscope` distribution to prevent cross-test race conditions.

### Frontend Tests

```bash
cd frontend
yarn test
```

---

## Engineering Constitution

The project is governed by **12 constitutional documents** that define immutable architectural principles. These are **architectural law**, not implementation guides.

| Constitution | Subsystem | Core Principle |
|---|---|---|
| 001 — System Architecture | Entire System | Unidirectional dependency, single source of truth |
| 002 — Curriculum Engine | Problem Bank, Roadmap | Static at runtime, editorial curation |
| 003 — Mission Engine | Mission builder | One mission/day, deterministic, composition-driven |
| 004 — Learner Intelligence | LI signals | 10 deterministic signals, bounded nudge, no ML |
| 005 — Assessment Engine | Assessment | Immutable evidence, deterministic evaluation |
| 006 — AI Mentor | Mentor, KB | Read-only, context-grounded, provider-agnostic |
| 007 — Company Intelligence | Company profiles | Compile-time only, deterministic scoring |
| 008 — Content Architecture | Knowledge gen | Global cache, first-requester-pays, strict JSON |
| 009 — Frontend Experience | Frontend | Backend drives UI state, no business logic in pages |
| 010 — Development Rules | All code | Sprint workflow, PR checklist, naming conventions |
| 011 — Data Contracts | MongoDB + DTOs | Canonical schemas, additive evolution, UTC timestamps |
| 012 — Testing & Quality | All tests | Hermetic tests, no production DB, regression policy |

### Key Invariants
1. Problem IDs (`lc-N`) are **immutable** — never change
2. Roadmap node IDs are **immutable** — permanent once published
3. `MissionContext` is the **single curriculum interface**
4. Arena and Assessment problems are **always disjoint**
5. Assessment evidence is **frozen** — never modified after creation
6. The planner is **deterministic** — same inputs → same output
7. Business logic belongs in the **service layer** — not in routes or React pages

Full constitution: [`constitution/`](constitution/)

---

## Contributing

### Development Workflow

1. Read the relevant [constitution documents](constitution/) before making changes
2. Branch from `main` using the naming convention: `feat/`, `fix/`, `refactor/`, `test/`
3. Follow existing code patterns and file organization
4. Ensure all tests pass (`pytest` for backend, `yarn test` for frontend)
5. Format Python code with `black` and `isort`
6. Lint Python code with `flake8` and `mypy`

### Forbidden Patterns
- ❌ Business logic in route handlers or React pages
- ❌ Problem metadata stored in MongoDB (it's static in `problem_bank.py`)
- ❌ Assessment Engine writing to `knowledge_nodes`
- ❌ Circular imports between service modules
- ❌ `console.log` in committed JavaScript
- ❌ `print()` in committed Python service code
- ❌ Tests that hit the production database
- ❌ `transition: all` in CSS (use specific properties)
- ❌ LLM calls in the mission generation blocking path

### Architecture Review
Any constitutional change requires:
1. PR title starting with `[ARCH REVIEW]`
2. Chief Software Architect approval
3. Constitution PR merged **before** implementation PR

---

## Default Credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@prepos.io` | `Admin@123` |

> These are auto-seeded on first startup. Change them via `ADMIN_EMAIL` and `ADMIN_PASSWORD` environment variables.

---

## License

This is a private, proprietary project. All rights reserved.
