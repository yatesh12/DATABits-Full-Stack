# DATABit

**Multi-Tenant SaaS Data Analytics and ETL Platform**

DATABit is a production-grade, cloud-native data analytics platform that enables organizations to ingest, profile, clean, transform, visualize, and export data through an intuitive web interface. Built with modern asynchronous Python and React, it supports multi-tenancy, role-based access control, plan-based billing, and horizontal scalability.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Backend](#backend)
  - [Framework & Runtime](#framework--runtime)
  - [API Layer](#api-layer)
  - [Database Layer](#database-layer)
  - [Authentication & Authorization](#authentication--authorization)
  - [Task Queue & Workers](#task-queue--workers)
  - [Storage Abstraction](#storage-abstraction)
  - [Caching](#caching)
  - [File Upload Pipeline](#file-upload-pipeline)
- [Frontend](#frontend)
  - [Framework & Build](#framework--build)
  - [State Management](#state-management)
  - [Routing](#routing)
  - [UI Component System](#ui-component-system)
  - [Data Visualization](#data-visualization)
- [Security](#security)
  - [Authentication](#authentication)
  - [Authorization](#authorization)
  - [Data Protection](#data-protection)
  - [Network Security](#network-security)
  - [Input Validation](#input-validation)
  - [Secrets Management](#secrets-management)
- [Observability & Monitoring](#observability--monitoring)
  - [Metrics](#metrics)
  - [Logging](#logging)
  - [Error Tracking](#error-tracking)
  - [Health Checks](#health-checks)
  - [Audit Logging](#audit-logging)
- [Scalability & Reliability](#scalability--reliability)
  - [Horizontal Scaling](#horizontal-scaling)
  - [Database](#database)
  - [Caching & Rate Limiting](#caching--rate-limiting)
  - [Async Processing](#async-processing)
  - [Graceful Degradation](#graceful-degradation)
  - [Retry & Resilience](#retry--resilience)
- [Production-Grade Design Decisions](#production-grade-design-decisions)
  - [Why FastAPI](#why-fastapi)
  - [Why RS256 JWT](#why-rs256-jwt)
  - [Why Repository Pattern](#why-repository-pattern)
  - [Why Celery + Redis](#why-celery--redis)
  - [Why Multi-Stage Docker](#why-multi-stage-docker)
  - [Why Tigris/S3 Object Storage](#why-tigriss3-object-storage)
  - [Why Argon2 for Password Hashing](#why-argon2-for-password-hashing)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
  - [Runtime Configuration](#runtime-configuration)
- [Deployment](#deployment)
  - [Docker](#docker)
  - [Render.com](#rendercom)
  - [Procfile (Heroku-compatible)](#procfile-heroku-compatible)
- [Development Setup](#development-setup)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Running Tests](#running-tests)
  - [Linting & Pre-commit](#linting--pre-commit)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Billing & Monetization](#billing--monetization)
- [Internationalization & Compliance](#internationalization--compliance)
- [Contributing](#contributing)
- [License](#license)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                        FRONTEND                           │
│         React 18 + TypeScript + Tailwind + MUI            │
│         TanStack Query 5 | React Router 6                 │
└──────────────────────┬───────────────────────────────────┘
                       │  HTTPS / WSS
                       ▼
┌──────────────────────────────────────────────────────────┐
│                     API GATEWAY                           │
│              FastAPI + Uvicorn + Gunicorn                 │
│         CSRF │ CORS │ Rate Limit │ Usage Limit            │
│         Auth │ RBAC │ Request Observability               │
├──────────────────────────────────────────────────────────┤
│                    API ROUTES (v1)                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │Auth  │ │Dataset│ │ Jobs │ │Billing│ │Upload│ │Work-  │  │
│  │      │ │       │ │      │ │      │ │      │ │flow   │  │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐  │
│  │Ingest│ │Assistant│ │Audit │ │Event │ │Admin │ │Advanced││
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘  │
├──────────────────────────────────────────────────────────┤
│                    SERVICE LAYER                          │
│ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────┐    │
│ │Dataset  │ │Ingestion │ │Export   │ │AI Assistant  │    │
│ │Service  │ │Lifecycle │ │Service  │ │(RAG/Groq)    │    │
│ └─────────┘ └──────────┘ └─────────┘ └─────────────┘    │
├──────────────────────────────────────────────────────────┤
│                   REPOSITORY LAYER                        │
│         SQLAlchemy 2.0 Async ORM + Raw SQL                │
├──────────────────────────────────────────────────────────┤
│                      STORAGE                              │
│  PostgreSQL │ Redis │ Tigris/S3 │ Local Filesystem        │
└──────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend

| Category | Technology |
|---|---|
| **Runtime** | Python 3.11.8 |
| **Web Framework** | FastAPI 0.115 (async), Starlette |
| **ASGI Server** | Uvicorn 0.30 |
| **WSGI Server** | Gunicorn 22.0 (Celery workers) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Migrations** | Alembic + Raw SQL scripts |
| **Validation** | Pydantic v2, pydantic-settings |
| **Auth** | PyJWT (RS256), Passlib, Argon2, bcrypt, Authlib |
| **Task Queue** | Celery + Redis (Upstash) |
| **Caching** | Redis (dedicated instances per concern) |
| **Database** | PostgreSQL 15+ (asyncpg driver, Neon.tech) |
| **Object Storage** | Tigris (S3-compatible) |
| **Vector DB** | Qdrant (RAG embeddings) |
| **AI/ML** | Groq, ONNX Runtime, FastEmbed |
| **Payments** | Stripe, Razorpay |
| **Observability** | Prometheus, Sentry, Structured JSON Logging |
| **Testing** | pytest, pytest-asyncio |

### Frontend

| Category | Technology |
|---|---|
| **Framework** | React 18, Create React App 5 |
| **Language** | TypeScript 4.9 |
| **Routing** | React Router DOM 6 |
| **Server State** | TanStack React Query 5 |
| **UI Library** | MUI 6, Radix UI Primitives |
| **Styling** | Tailwind CSS 3.4, Emotion 11, CVA |
| **Icons** | Lucide React, Heroicons, React Icons |
| **Animation** | Framer Motion 12 |
| **Visualization** | Recharts, Nivo, Plotly.js |
| **Toasts** | Sonner |
| **Error Tracking** | Sentry SDK |
| **Utilities** | Lodash, PapaParse, FileSaver, TUS Client |
| **Testing** | Jest, React Testing Library |

---

## Project Structure

```
DATABit/
├── backend/                        # Python FastAPI backend
│   ├── app.py                      # FastAPI app (lifespan, middleware, exception handlers)
│   ├── main.py                     # Entry point for uvicorn
│   ├── settings.py                 # Pydantic settings re-export
│   ├── requirements.txt            # Production dependencies
│   ├── requirements-dev.txt        # Development dependencies
│   ├── requirements-ml.txt         # ML/embedding dependencies
│   ├── Dockerfile                  # Multi-stage Docker build
│   ├── Procfile                    # Heroku/Render process definitions
│   ├── alembic.ini                 # Alembic configuration
│   ├── runtime.txt                 # Python version (3.11.8)
│   ├── core/                       # Core platform utilities
│   │   ├── config.py               # Pydantic Settings (420+ fields)
│   │   ├── database.py             # Async SQLAlchemy engine, session, base model
│   │   ├── security.py             # JWT encode/decode (RS256), Argon2/PBKDF2 hashing
│   │   ├── auth.py                 # Principal dataclass, bearer/cookie auth, RBAC
│   │   ├── rate_limit.py           # Redis sliding-window rate limiter
│   │   ├── redis_client.py         # Redis connection management
│   │   ├── cache.py                # Shared Redis cache layer
│   │   ├── celery_app.py           # Celery app configuration
│   │   ├── metrics.py              # Prometheus metrics
│   │   ├── logging.py / logging_config.py  # Structured JSON logging
│   │   ├── migrations.py           # Runtime migration orchestration
│   │   ├── usage.py                # Usage tracking & plan limit enforcement
│   │   ├── exceptions.py           # Custom exception classes
│   │   ├── background.py           # Background task helpers
│   │   ├── email_service.py        # SMTP email service
│   │   ├── file_validation.py      # File upload validation
│   │   ├── websocket_manager.py    # WebSocket connection manager
│   │   └── db_health.py            # Database health checks
│   ├── api/
│   │   ├── dependencies.py         # FastAPI dependency injection
│   │   └── v1/                     # API version 1
│   │       ├── router.py           # Central router (registers all modules)
│   │       ├── auth/               # Auth routes, service, schemas
│   │       ├── datasets/           # Dataset CRUD + job management
│   │       ├── billing/            # Stripe & Razorpay billing
│   │       ├── health/             # Health check endpoints
│   │       ├── upload/             # File upload pipeline
│   │       ├── ingestion/          # Cloud ingestion & stream subscriptions
│   │       ├── user/               # User profile & settings
│   │       ├── jobs/               # Job management + SSE
│   │       ├── workflow/           # Workflow recipes, batch processing
│   │       ├── assistant/          # AI assistant (RAG/Groq)
│   │       ├── audit/              # Audit log endpoints
│   │       ├── community/          # Community features
│   │       ├── ecosystem/          # Careers, enterprise, team
│   │       ├── network/            # Network signals, pulse
│   │       ├── events/             # Community events
│   │       ├── support/            # Support center
│   │       └── advanced/           # Model evaluation, data catalog, sampling, validation
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── auth.py                 # User, Tenant, Session, Identity, PasswordReset
│   │   ├── billing.py              # Plan, Subscription, Usage, Transaction, WebhookEvent
│   │   ├── data_platform.py        # Dataset, Version, IngestionJob, SourceConnection
│   │   ├── jobs.py                 # Job, JobRun
│   │   ├── platform.py             # UserSetting, ProjectHistory, AuditEvent
│   │   └── workflow.py             # WorkflowRecipe, WorkflowJob, WorkflowJobLog
│   ├── repositories/               # Data access layer
│   │   ├── base.py                 # Abstract base repository
│   │   ├── user_repository.py
│   │   ├── tenant_repository.py
│   │   ├── dataset_repository.py
│   │   └── billing_repository.py
│   ├── services/                   # Business logic layer
│   │   ├── dataset_service.py
│   │   ├── ingestion_lifecycle.py
│   │   ├── export_service.py
│   │   ├── quality_service.py
│   │   ├── audit_service.py
│   │   └── rag/                    # RAG pipeline for AI assistant
│   ├── storage/                    # Storage abstraction layer
│   │   ├── dataset_store.py        # Local dataset store
│   │   ├── dataset_store_factory.py  # Store selection factory
│   │   ├── tigris_storage.py       # Tigris S3-compatible storage
│   │   ├── object_store.py         # General object store
│   │   ├── stream_store.py         # Stream data store
│   │   └── storage_keys.py         # Key generation utilities
│   ├── workers/                    # Async task definitions
│   │   ├── celery_app.py           # Celery application
│   │   ├── tasks.py                # Main task definitions
│   │   ├── import_tasks.py         # Data import tasks
│   │   ├── data_tasks.py           # Data processing tasks
│   │   ├── db_worker.py            # DB worker loop
│   │   └── cleanup_tasks.py        # Scheduled cleanup tasks
│   ├── migrations/                 # Raw SQL migration scripts
│   ├── alembic/                    # Alembic revision versions
│   ├── tests/                      # Test suite (unit + integration)
│   └── scripts/                    # Utility scripts (PowerShell + Python)
│
├── frontend/                       # React frontend
│   ├── package.json
│   ├── tsconfig.json / tsconfig.typecheck.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env / .env.example
│   ├── public/                     # Static assets
│   └── src/
│       ├── App.tsx                 # Root component (routing, auth, layout)
│       ├── index.js                # Entry point
│       ├── api/                    # API client modules
│       ├── auth/                   # Auth context, login, token management
│       ├── components/             # Shared UI components
│       │   ├── layout/             # Header, Footer
│       │   ├── home/               # Landing page sections
│       │   ├── ui/                 # Reusable UI primitives
│       │   └── ...                 # Feature-specific components
│       ├── v1/                     # Main application workspace
│       │   ├── tool/               # Data preprocessing tool (Main.tsx)
│       │   ├── features/           # Feature modules
│       │   ├── components/         # V1-specific components
│       │   └── billing/            # Billing UI
│       ├── config/                 # Environment & API configuration
│       ├── hooks/                  # Custom React hooks
│       ├── styles/                 # Global styles
│       ├── types/                  # TypeScript type definitions
│       └── utils/                  # Utility functions
│
├── scripts/                        # Root-level automation scripts
├── storage/                        # Local dataset storage mount
├── render.yaml                     # Render.com deployment manifest
├── .pre-commit-config.yaml         # Pre-commit hooks
├── .env.phase1.example             # Phase 1 feature flags
└── .env.phase2.example             # Phase 2 additive configuration
```

---

## Backend

### Framework & Runtime

DATABit runs on **Python 3.11.8** with **FastAPI 0.115** — an async-native web framework built on Starlette. The ASGI server is **Uvicorn** with **Gunicorn** as a process manager for Celery workers.

Key framework characteristics:
- **Async-first**: All I/O-bound operations (database queries, Redis calls, HTTP requests) are non-blocking via `async/await`.
- **Automatic OpenAPI docs**: Swagger UI at `/api/docs`, ReDoc at `/api/redoc`, OpenAPI spec at `/api/openapi.json`.
- **Pydantic v2 validation**: Every request and response is validated through Pydantic models, ensuring type safety and early error detection.
- **Middleware pipeline**: Proxy headers → GZip → CSRF → Request observability → Auth context → Rate limiting → Usage enforcement → CORS.

### API Layer

The API follows a **versioned** structure under `/api/v1/`. Each domain module follows a consistent pattern:

```
api/v1/{domain}/
├── router.py       # FastAPI APIRouter with endpoint definitions
├── controller.py   # Request/response orchestration
├── service.py      # Business logic
├── schemas.py      # Pydantic request/response models
└── dependencies.py # Domain-specific FastAPI dependencies
```

All routes are mounted into a central router at `api/v1/router.py` and included in the app with the `/api` prefix.

**Endpoint categories:**

| Group | Base Path | Description |
|---|---|---|
| Health | `/api/health/*` | System health checks (readiness, liveness, DB, Redis) |
| Auth | `/api/auth/*` | Login, register, refresh, logout, OAuth, magic-link, mobile OTP, password reset |
| Config | `/api/config/*` | Upload configuration, plan limits |
| Datasets | `/api/datasets/*` | Dataset CRUD, jobs, preview, profile |
| Upload | `/api/upload/*` | File upload, import sessions, TUS resumable upload |
| Ingestion | `/api/ingestion/*` | Cloud storage ingestion, stream subscriptions |
| Jobs | `/api/jobs/*` | Job management, SSE real-time updates |
| Billing | `/api/billing/*` | Plans, subscriptions, payments, webhooks (Stripe + Razorpay) |
| User | `/api/user/*` | Profile, settings, preferences |
| Workflow | `/api/workflow/*` | Recipes, batch processing, train/test split |
| Assistant | `/api/assistant/*` | AI assistant chat (RAG over documentation) |
| Audit | `/api/audit/*` | Audit log queries |
| Advanced | `/api/advanced/*` | Model evaluation, data catalog, sampling, validation, reporting |
| Community | `/api/community/*` | Community features |
| Ecosystem | `/api/ecosystem/*` | Careers, enterprise, team management |
| Events | `/api/events/*` | Community event management |
| Network | `/api/network/*` | Network signals, pulse |
| Support | `/api/support/*` | Support center |
| Contact | `/api/contact/*` | Contact forms |
| Architect | `/api/architect/*` | Documentation |

### Database Layer

**PostgreSQL** is the primary database, accessed through **SQLAlchemy 2.0 async ORM** with the **asyncpg** driver.

**Connection Pooling:**
- Pool size: 20 (configurable)
- Max overflow: 20 (configurable)
- Pool timeout: 30s
- Pool recycle: 1800s (prevents connection staleness)
- SSL: Configurable via connection string
- PgBouncer support: Transaction pooling mode

**Schema Management:**
- **Alembic** for version-controlled schema migrations (Python-based, reversible)
- **Raw SQL scripts** for complex migrations (indexes, stored procedures, data migrations)
- **Runtime migrations** for non-schema data updates
- **ORM consistency checks** on startup validate that the database schema matches model definitions
- **Critical table checks** ensure core tables exist before the app accepts traffic

**Repository Pattern:**
A dedicated data access layer (`repositories/`) abstracts SQLAlchemy queries behind domain-specific interfaces. This provides:
- Clear separation between business logic and data access
- Easier unit testing (repositories can be mocked)
- Consistent query patterns across the codebase
- Centralized optimization points

**Key tables:**
- **Auth**: `tenants`, `auth_users`, `tenant_memberships`, `auth_identities`, `auth_user_sessions`, `password_reset_tokens`
- **Billing**: `plans`, `plan_limits`, `tenant_subscriptions`, `tenant_usage`, `billing_payment_transactions`, `usage_events`, `billing_webhook_events`
- **Data**: `datasets`, `dataset_versions`, `ingestion_jobs`, `ingestion_attempts`, `source_connections`, `stream_subscriptions`, `dataset_profiles`, `dataset_quality_rules`
- **Jobs**: `jobs`, `job_runs`
- **Audit**: `auth_audit_events`, `auth_project_history`
- **Workflow**: `workflow_recipes`, `workflow_jobs`

### Authentication & Authorization

**Multi-factor authentication strategy:**

| Method | Implementation |
|---|---|
| Email/Password | Argon2 hashed, PBKDF2-SHA256 fallback |
| OAuth 2.0 | Google and GitHub via Authlib |
| Magic Link | Time-limited (15 min) one-time tokens |
| Mobile OTP | Twilio or MSG91 (configurable) |
| Session Tokens | Refresh token rotation with 14-day expiry |

**JWT Authentication:**
- **Algorithm**: RS256 (asymmetric RSA-2048)
- **Access token**: Short-lived (default 10 minutes)
- **Refresh token**: 14-day expiry with rotation (refresh families prevent token reuse)
- **Cookie delivery**: `databits_at` HTTP-only cookie + `Authorization: Bearer` header support
- **Token claims**: `sub` (user_id), `email`, `role`, `tenant_id`, `jti` (unique token ID), issuer, audience
- **Key management**: PEM-encoded private/public keys via environment variables or file paths

**Role-Based Access Control (RBAC):**
- Three roles: `admin`, `analyst`, `viewer`
- Roles enforced at the API layer via dependency injection
- Granular permission checks on datasets, projects, and administrative actions

**Multi-Tenant Isolation:**
- Every resource is scoped to a `tenant_id`
- All queries enforce tenant isolation at the database level
- Cross-tenant access is denied by default
- Tenant context is extracted from JWT and propagated through middleware

### Task Queue & Workers

**Celery** with **Redis** as both broker and result backend handles asynchronous processing.

**Worker topology:**
| Service | Command | Queue | Purpose |
|---|---|---|---|
| Web | Uvicorn (4 workers) | N/A | API request handling |
| Worker | Celery worker (2 concurrency) | `free_jobs` | Dataset import, processing |
| Scheduler | Celery beat | N/A | Scheduled cleanup, maintenance |
| DB Worker | In-process asyncio loop | N/A | Stale job cleanup, dataset maintenance |

**Task categories:**
- Data import (local files, cloud storage, database connections, streams)
- Data processing (profiling, transformation, quality checks)
- Export (Parquet, CSV, database writes)
- Cleanup (stale jobs, expired artifacts, audit log purging)
- Email notifications (welcome emails, password reset, billing alerts)

**Inline mode**: For small files (<50MB), the system uses FastAPI's `BackgroundTask` directly, bypassing Celery entirely. This eliminates broker dependency for common operations while maintaining reliability for larger workloads.

### Storage Abstraction

DATABit uses a **strategy pattern** for dataset storage, allowing transparent switching between backends:

| Backend | Type | Use Case |
|---|---|---|
| Tigris (S3-compatible) | Object Storage | Production primary (configurable bucket) |
| Local Filesystem | Disk | Development, single-server deployments |
| Supabase Storage | Object Storage | Legacy (deprecated) |

The `dataset_store_factory.py` selects the appropriate store based on configuration. All stores implement a common interface: `save`, `load`, `delete`, `exists`, `list`.

Additionally, a separate **Object Store** handles non-dataset artifacts (exported files, temporary processing results) with configurable TTL-based cleanup.

### Caching

**Redis** provides a multi-layered caching strategy:

| Cache | TTL | Purpose |
|---|---|---|
| Dataset Preview | 60s | Preview rows for dataset explorer |
| Dataset Summary | 90s | Statistical summaries |
| Dataset Correlation | 90s | Correlation matrices |
| Dataset Visualization | 180s | Chart data |
| Quality Reports | 300s | Data quality snapshots |
| Histograms | 600s | Column distribution data |

**Cache invalidation** is event-driven: mutations to datasets (upload, transform, clean) invalidate related cache entries automatically.

### File Upload Pipeline

The upload pipeline supports multiple strategies for different file sizes:

| File Size | Strategy | Mechanism |
|---|---|---|
| <6MB | Direct inline | Synchronous parse + store |
| <50MB | BackgroundTask | In-process async upload |
| <Plan limit | Celery task | Distributed processing |
| Any size | TUS resumable | Chunked upload (tus-js-client) |

Upload limits are enforced per plan:
- **Free**: 10MB
- **Essential**: 250MB
- **Professional**: 1.5GB
- **Enterprise**: Negotiable (5GB hard cap)

---

## Frontend

### Framework & Build

The frontend is a **React 18** single-page application bootstrapped with **Create React App 5** and written in **TypeScript 4.9**.

Build configuration:
- **TypeScript**: Two tsconfig files — a standard CRA config for development and a strict config (`tsconfig.typecheck.json`) for CI type-checking
- **PostCSS**: Tailwind CSS 3.4 + Autoprefixer for utility-first CSS
- **Emotion 11**: CSS-in-JS for MUI component customization
- **ESLint**: Standard CRA `react-app` preset with `react-app/jest`

### State Management

| Concern | Solution | Rationale |
|---|---|---|
| Server state | TanStack React Query 5 | Automatic caching, background refetching, optimistic updates, request deduplication |
| Auth state | React Context (`localAuth.tsx`) | Simple, synchronous auth checks for UI rendering |
| UI state | Local component state, React Context | No global state manager needed; domains are well-encapsulated |

### Routing

```
Route                  Component            Auth Required
─────────────────────────────────────────────────────────
/                       HomePage            No
/login                  LoginForm           No
/reset-password         ResetPasswordPage   No
/auth/callback          AuthCallbackPage    No
/desktop-auth/success   DesktopAuthSuccess  No
/app/editor             DataPreprocessingApp  Yes
/agentic-mode           AgenticMode         Yes
/profile                ProfilePage         Yes
/account                AccountPage         Yes
/checkout               CheckoutPage        No
/billing                BillingPage         No
/billing/success        BillingSuccess      No
/pricing                Pricing             No
/community/*            Community pages     No
/ecosystem/*            Ecosystem pages     No
/network/*              Network pages       No
/architect/*            Documentation pages No
/support                SupportCenter       No
/status                 SystemStatusPage    No
/privacy                LegalPage           No
/terms                  LegalPage           No
/cookies                LegalPage           No
```

### UI Component System

The UI is built on a hybrid of **Material UI 6** (complex data tables, form controls, dialogs) and **Radix UI Primitives** (accessible, unstyled base components for custom UI).

**Component hierarchy:**
- Primitives: Radix UI (accordion, checkbox, dropdown, label, progress, scroll-area, select, separator, tabs, tooltip)
- Compound components: MUI + custom compositions
- Page-level components: Feature-specific assemblies
- Layout: Common header/footer, auth-aware navigation

**Design tokens** are managed through Tailwind classes with `class-variance-authority` (CVA) for component variant management and `clsx`/`tailwind-merge` for class composition.

### Data Visualization

| Library | Use Case |
|---|---|
| Recharts | Standard charts (line, bar, area, pie, scatter) |
| Nivo | Heatmaps, advanced bar/line/scatter, responsive SVGs |
| Plotly.js | Interactive, publication-quality charts |
| d3-array | Statistical computations for chart data |

---

## Security

### Authentication

| Measure | Implementation |
|---|---|
| Password Hashing | Argon2 (primary), PBKDF2-SHA256 (fallback), automatic hash upgrade on login |
| JWT Signing | RS256 asymmetric (RSA-2048 key pair) — private key never leaves the server |
| Token Lifetime | Access: 10 min, Refresh: 14 days with rotation family |
| OAuth 2.0 | State parameter with PKCE, HTTPS-only redirect URIs |
| Magic Link | SHA256-hashed tokens, 15-min expiry, single-use |
| Mobile OTP | Rate-limited (3/hour), max 3 verification attempts |
| Session Management | Refresh family rotation prevents stolen token reuse |
| CSRF | Double-submit cookie pattern: `databits_csrf` cookie must match `x-csrf-token` header |

### Authorization

| Measure | Implementation |
|---|---|
| RBAC | 3 roles (admin, analyst, viewer), enforced via FastAPI dependency injection |
| Multi-Tenant Isolation | All queries scoped to `tenant_id`, enforced at repository layer |
| Resource Ownership | Datasets, jobs, and projects checked against owning tenant |
| Admin Escalation | Admin-only endpoints for billing, user management, and system configuration |

### Data Protection

| Measure | Implementation |
|---|---|
| In-Transit Encryption | All traffic over HTTPS (TLS 1.2+ enforced at load balancer) |
| Database Encryption | PostgreSQL SSL/TLS connections |
| PII Detection | Automated PII scanning (emails, SSNs, phone numbers) |
| Anonymization | Masking, hashing, and tokenization of sensitive fields |
| Data Governance | Differential privacy support for aggregate queries |
| Source Credentials | AES-256 encrypted at rest via `SOURCE_CREDENTIALS_SECRET` |
| Audit Trail | Immutable `auth_audit_events` table, 90-day retention |

### Network Security

| Measure | Implementation |
|---|---|
| CORS | Strict origin allowlist + Vercel preview domain regex |
| Request Size Limit | 64MB default (413 if exceeded) |
| Rate Limiting | Redis sliding window per-endpoint limits |
| Outbound Control | Blocked private IPs (production), blocked ports (22, 25, 5432, 6379), DNS rebinding protection |
| Proxy Headers | Trusted proxy IP configuration for correct client IP |
| GZip Compression | Min 1000 bytes, prevents compression-based attacks |

### Input Validation

- **Pydantic v2**: All request bodies, query parameters, and path parameters are validated at the framework level
- **Dataset ID sanitization**: Regex-based whitelist prevents path traversal and injection
- **File upload validation**: MIME type checking, magic byte verification, size enforcement per plan
- **SQL injection**: Prevented by SQLAlchemy parameterized queries

### Secrets Management

- All secrets loaded via environment variables — never hardcoded
- `.env` files are gitignored
- JWT keys can be injected as PEM strings or file paths
- Encryption keys (`SOURCE_CREDENTIALS_SECRET`) used for sensitive configuration at rest
- Sentry DSN configured via environment variable

---

## Observability & Monitoring

### Metrics

Prometheus metrics are exposed at the `/api/metrics` endpoint:

| Metric | Type | Labels |
|---|---|---|
| `databits_http_requests_total` | Counter | `method`, `path`, `status_code` |
| `databits_http_request_duration_seconds` | Histogram | `method`, `path` |
| `databits_http_errors_total` | Counter | `method`, `path`, `status_code` |

### Logging

Structured JSON logging with the following loggers:

| Logger | Purpose |
|---|---|
| `app.request` | Per-request logging (method, path, status, duration_ms, request_id, correlation_id) |
| `app.errors` | Error details with full stack traces |
| `core.database` | Database connection pool events |
| `startup` | Startup sequence progress (10-step bootstrap) |
| `shutdown` | Shutdown sequence events |

Every request receives:
- `x-request-id`: Unique request identifier
- `x-correlation-id`: End-to-end trace identifier (propagated from frontend)

### Error Tracking

**Sentry** is configured for both backend and frontend:

| Component | SDK | Sample Rate |
|---|---|---|
| Backend | `sentry-sdk[fastapi]` | 0.1 (10%) |
| Frontend | `@sentry/react` | Configurable via env |

Sentry is initialized during app startup with FastAPI integration for automatic error context.

### Health Checks

| Endpoint | Check | Frequency |
|---|---|---|
| `GET /api/health/ready` | DB connectivity, Redis, storage backend | Every 30s (Docker) |
| `GET /api/health` | App status, environment, timestamp | On demand |

Docker `HEALTHCHECK` uses `curl localhost:8000/api/health` with 30s interval, 5s timeout, 3 retries, and 10s start period.

### Audit Logging

All user actions that modify state are recorded in the `auth_audit_events` table:

```
tenant_id | user_id | event_type | event_data (JSONB) | ip_address | user_agent | created_at
```

Audit logs are immutable (append-only) and retained for 90 days (configurable). The audit trail supports compliance requirements (GDPR, SOC 2, HIPAA).

---

## Scalability & Reliability

### Horizontal Scaling

**Stateless API servers**: The FastAPI application is stateless (session state stored in Redis, not in-memory). Multiple Uvicorn workers or multiple server instances can run behind a load balancer.

**Database connection pooling**: Configurable pool size (default 20) with overflow support for traffic spikes. PgBouncer transaction pooling mode is supported for high-connection environments.

**Vertical slice architecture**: Each Celery worker type (import, processing, cleanup) can be scaled independently based on queue depth.

### Database

| Strategy | Implementation |
|---|---|
| Connection Pooling | SQLAlchemy pool (20 + 20 overflow), PgBouncer compatible |
| Query Optimization | Strategic indexes (8+ migration files), `EXPLAIN ANALYZE` validated |
| Read/Write Splitting | Possible via SQLAlchemy bind configuration |
| Migration Safety | Alembic versioned + startup schema consistency checks |
| Health Checks | Periodic DB connectivity validation |

### Caching & Rate Limiting

**Redis resilience:**
- Three dedicated Redis connections (token, rate limit, queue) — failure in one does not affect others
- Configurable fallback behavior per concern:
  - Token Redis fallback: `REDIS_ALLOW_FALLBACK_TOKEN` (default: allow)
  - Rate limit Redis fallback: `REDIS_ALLOW_FALLBACK_RATE_LIMIT` (default: allow)
  - Queue Redis fallback: `REDIS_ALLOW_FALLBACK_QUEUE` (default: allow)
- Automatic Upstash SSL detection (`rediss://` scheme enforced for Upstash hosts)
- Connection retries with exponential backoff

**Rate limiting tiers:**
| Resource | Limit |
|---|---|
| Authenticated requests | 120/min (multiplied by plan tier) |
| Anonymous requests | 40/min |
| Login attempts | 20/min |
| Registration | 10/min |
| File upload | 3/60s |

Plan tier multipliers: Free (1x), Essential (2x), Professional (5x), Enterprise (10x)

### Async Processing

| Strategy | Description |
|---|---|
| Celery | Distributed task queue for long-running operations (import, processing, export) |
| BackgroundTask | In-process async for small files (<50MB) — no broker dependency |
| SSE (Server-Sent Events) | Real-time job progress updates to the frontend |
| WebSocket Manager | Real-time agent communication and status updates |
| Cleanup Tasks | Scheduled Celery beat tasks for retention policies |

### Graceful Degradation

| Failure Scenario | Behavior |
|---|---|
| Redis unavailable | Rate limiting and caching bypassed; token validation falls back to cached keys |
| Celery broker unreachable | Inline mode activates for small files; upload jobs queued when broker recovers |
| Database connection failure | Health check fails; load balancer routes away from unhealthy instance |
| Storage backend unavailable | Uploads rejected with clear error; existing datasets remain readable |
| S3/Tigris down | Local storage fallback for critical operations (configurable) |

### Retry & Resilience

- **Tenacity** library for retry logic with exponential backoff on transient failures
- **Celery task retries** with configurable max retries and delay
- **Job state machine** tracks every execution attempt with failure reason
- **Startup recovery** detects and recovers incomplete ingestion jobs from prior lifecycle stages
- **Stale job cleanup** automatically cancels jobs older than 24 hours on startup

---

## Production-Grade Design Decisions

### Why FastAPI

- **Async-native**: Leverages Python async for high-concurrency I/O without the GIL penalty of threading
- **Automatic OpenAPI**: Eliminates documentation drift — API docs are always current
- **Pydantic v2**: Blazing-fast validation (Rust-based core), precise error messages, IDE autocompletion
- **Dependency injection**: Clean separation of concerns, easy testing with overrideable dependencies
- **Performance**: On par with Node.js and Go for typical API workloads

### Why RS256 JWT

- **Asymmetric signing**: Private key never leaves the server — public key can be distributed freely
- **No shared secret**: Avoids the risk of secret leakage from client-side code or third-party services
- **Key rotation**: Possible without invalidating all tokens (introduce new `kid`)
- **Industry standard**: Compatible with all JWT libraries and API gateways

### Why Repository Pattern

- **Testability**: Business logic can be tested with mocked repositories — no database needed
- **Query optimization**: Complex queries are centralized, not scattered across services
- **Consistency**: All data access follows the same patterns (pagination, filtering, error handling)
- **Migration path**: Swapping ORM or database requires changing only the repository layer

### Why Celery + Redis

- **Proven reliability**: Celery has been the standard Python task queue for over a decade
- **Distributed by design**: Workers can run on separate machines, scaled independently
- **Flexible broker**: Redis is fast, simple, and already in the stack for caching/rate limiting
- **Inline fallback**: Small tasks bypass the broker entirely, keeping latency low
- **Monitoring**: Flower-compatible, Prometheus metrics, built-in retry and rate limiting

### Why Multi-Stage Docker

- **Small image size**: Only runtime dependencies are included in the final stage
- **Security**: Non-root user (`databit`) in the runtime stage, reduced attack surface
- **Layer caching**: Dependency installation is cached — only rebuilds on `requirements.txt` changes
- **Production readiness**: HEALTHCHECK, proper signal handling, configurable workers

### Why Tigris/S3 Object Storage

- **S3-compatible**: Avoids provider lock-in — can switch between AWS S3, Tigris, MinIO, or any S3-compatible store
- **Scalability**: Object storage handles petabytes without application changes
- **Cost-effective**: Pay only for storage used; no provisioning needed
- **Durability**: 99.999999999% durability with automatic replication

### Why Argon2 for Password Hashing

- **Winner of the Password Hashing Competition**: Designated successor to bcrypt/scrypt
- **Memory-hard**: Resistant to GPU and ASIC-based brute force attacks
- **Configurable**: Memory cost, time cost, and parallelism parameters tunable for future hardware
- **Automatic upgrade**: Users' password hashes are transparently upgraded on next login

---

## Configuration

### Environment Variables

The application is configured entirely through environment variables. Below are the key configuration groups:

**Core:**
```
ENV=development|production
APP_NAME=DATABit
FRONTEND_URL=http://localhost:3000
API_BASE_URL=http://127.0.0.1:8000
```

**Database:**
```
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=20
ENABLE_PGBOUNCER=false
```

**Redis:**
```
REDIS_URL=rediss://default:pass@host.upstash.io:6379
REDIS_TOKEN_DB=0
REDIS_RATE_LIMIT_DB=0
REDIS_CELERY_DB=0
```

**JWT:**
```
JWT_PRIVATE_KEY_PEM="-----BEGIN PRIVATE KEY-----..."
JWT_PUBLIC_KEY_PEM="-----BEGIN PUBLIC KEY-----..."
ACCESS_TOKEN_EXPIRE_SECONDS=600
REFRESH_TOKEN_EXPIRE_SECONDS=1209600
```

**Billing (Stripe):**
```
STRIPE_SECRET_KEY=sk_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_CURRENCY=usd
```

**Billing (Razorpay):**
```
RAZORPAY_KEY_ID=rzp_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

**Storage:**
```
OBJECT_STORAGE_BACKEND=local|s3
TIGRIS_ENDPOINT_URL=https://fly.storage.tigris.dev
TIGRIS_BUCKET_NAME=databits
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

**Frontend (REACT_APP_*):**
```
REACT_APP_API_BASE_URL=https://api.databit.com
REACT_APP_API_PREFIX=/api
REACT_APP_SENTRY_DSN=...
NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_...
```

See `.env.phase1.example` and `.env.phase2.example` for complete variable lists with defaults.

### Runtime Configuration

Phase-based feature flags enable staged rollout of new capabilities:

| Phase 1 | Phase 2 |
|---|---|
| `ENABLE_CELERY_TASKS=false` | `ENABLE_SUPABASE_DATASET_STORE=false` |
| `ENFORCE_FILE_SIZE_LIMIT=false` | `ENABLE_SHARED_REDIS_CACHE=false` |
| `ENABLE_STORAGE_TIMEOUT=false` | `ENABLE_PGBOUNCER=false` |
| | `REACT_APP_ENABLE_FRONTEND_VIRTUALIZATION=true` |

---

## Deployment

### Docker

```bash
# Build the image
docker build -t databit-backend ./backend

# Run with environment variables
docker run -p 8000:8000 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  -e JWT_PRIVATE_KEY_PEM="..." \
  -e JWT_PUBLIC_KEY_PEM="..." \
  databit-backend
```

The Dockerfile uses a **three-stage build**:
1. **base**: Python 3.11-slim, system dependencies (curl for healthcheck), non-root user creation
2. **deps**: Python dependency installation with `--no-cache-dir`
3. **runtime**: Source copy, permission hardening, HEALTHCHECK, non-root execution

### Render.com

A complete `render.yaml` manifest defines three services:

| Service | Type | Instances | Command |
|---|---|---|---|
| `databits-backend` | Web | 1 | `uvicorn main:app --workers 4` |
| `databits-worker` | Worker | 1 | `celery worker --concurrency 2 -Q free_jobs` |
| `databits-scheduler` | Worker | 1 | `celery beat` |

All services share a 20GB persistent disk mounted at `/var/data/databits` for dataset storage.

### Procfile (Heroku-compatible)

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4
worker: celery -A core.celery_app worker --loglevel=info --concurrency=2
```

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For testing/linting

# Set up environment
copy .env.example .env  # Edit with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload --port 8000
```

The API is now available at `http://localhost:8000/api/docs`.

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
copy .env.example .env.local  # Edit with your configuration

# Start the development server
npm start
```

The app is now available at `http://localhost:3000`.

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

### Linting & Pre-commit

```bash
# Backend linting
cd backend
ruff check .

# Frontend linting
cd frontend
npm run lint

# Type checking
npm run type-check

# Pre-commit hooks (layer enforcement)
pre-commit install
pre-commit run --all-files
```

---

## API Documentation

When the backend is running:

| URL | Description |
|---|---|
| `/api/docs` | Swagger UI (interactive) |
| `/api/redoc` | ReDoc (reference) |
| `/api/openapi.json` | OpenAPI schema (JSON) |

### Standard Response Format

All API responses follow a consistent envelope:

```json
{
  "success": true,
  "message": "Operation completed",
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "success": false,
  "message": "Human-readable error message",
  "code": "ERROR_CODE",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  },
  "data": null
}
```

Standard error codes:
| Code | HTTP Status | Description |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `UNAUTHORIZED` | 401 | Missing or invalid credentials |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `USAGE_LIMIT_EXCEEDED` | 403 | Plan limit exceeded |
| `CSRF_VALIDATION_FAILED` | 403 | CSRF token mismatch |
| `REQUEST_ENTITY_TOO_LARGE` | 413 | Payload exceeds limit |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected error |

---

## Database Schema

Detailed schema documentation for all tables is available in the migration files:

- `backend/migrations/data_platform_foundation_v2.sql` — Core tables
- `backend/migrations/ingestion_state_machine_v4.sql` — Ingestion lifecycle
- `backend/migrations/upload_jobs_migration.sql` — Upload job tables
- `backend/migrations/add_missing_tables_v3.sql` — Additional tables
- `backend/migrations/add_performance_indexes.sql` — Query optimization indexes
- `backend/migrations/job_processing_optimization.sql` — Job processing indexes

Alembic migration versions are in `backend/alembic/versions/`.

---

## Billing & Monetization

### Payment Providers

| Provider | Region | Integration |
|---|---|---|
| Stripe | Global | Subscriptions, payment links, webhooks |
| Razorpay | India | Subscriptions, one-time payments, webhooks |

### Plan Tiers

| Plan | Upload Limit | Rate Limit Multiplier | Features |
|---|---|---|---|
| Free | 10MB | 1x | Core features, community support |
| Essential | 250MB | 2x | Increased limits, email support |
| Professional | 1.5GB | 5x | Advanced features, priority support |
| Enterprise | Custom | 10x | Custom limits, dedicated support, SSO |

### Usage Tracking

Each API call consumes from the tenant's plan allowance. Usage is tracked with per-resource granularity:
- API calls (monthly reset)
- Storage (byte-days)
- Compute (vCPU-minutes)
- Concurrent jobs

Limits are enforced at the middleware layer before request processing.

---

## Internationalization & Compliance

### Supported Regions

- **Global**: Stripe payments, English UI, multiple currencies
- **India**: Razorpay payments, INR support, mobile OTP via MSG91

### Data Protection & Privacy

| Regulation | Feature |
|---|---|
| GDPR | Right to deletion, data export, audit logs, consent management |
| CCPA | Opt-out mechanisms, disclosure of data collection |
| HIPAA | PHI detection, access controls, audit trails (configurable) |
| SOC 2 | Audit logging, access controls, change management |

### Privacy Features

- PII detection and masking
- Data anonymization and tokenization
- Differential privacy for aggregate queries
- Configurable data retention policies
- Automated data purging (90-day audit logs, 24-hour export cleanup)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run the pre-commit hooks (`pre-commit run --all-files`)
4. Ensure all tests pass
5. Submit a pull request

### Coding Standards

- **Python**: Follow PEP 8, use type hints, prefer async/await, maintain repository/service separation
- **TypeScript**: Use strict type checking, prefer interfaces over types, follow existing patterns
- **UI**: Follow the established component structure, use Tailwind for styling, Radix for primitives
- **Security**: Never hardcode secrets, validate all inputs, respect tenant isolation

### Commit Messages

Follow conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`.

---

## License

Private - All rights reserved.

For licensing inquiries, contact the DATABit team.
