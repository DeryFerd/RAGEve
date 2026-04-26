<!-- PROJECT BADGES -->
<div align="center">

![RAGEve](docs/assets/banner.png)

**Local-first RAG platform — Fast, private, no cloud required.**

[![License](https://img.shields.io/badge/License-Apache--2.0-blue?labelColor=d4eaf7)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-green?logo=python&logoColor=white)](pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal?logo=fastapi&logoColor=white)](backend/main.py)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js&logoColor=white)](frontend)
[![Ollama](https://img.shields.io/badge/Ollama-Local-purple?logo=ollama&logoColor=white)](https://ollama.com)

<a href="#-get-started">Get Started</a> ·
<a href="#-configurations">Configuration</a> ·
<a href="#-launch-service-from-source-for-development">Develop</a> ·
<a href="#-community">Community</a> ·
<a href="#-contributing">Contributing</a>

</div>

---

<details open>
<summary><b>📕 Table of Contents</b></summary>

- 💡 [What is RAGEve?](#-what-is-rageve)
- 🎮 [Demo](#-demo)
- 🔥 [Latest Updates](#-latest-updates)
- 🌟 [Key Features](#-key-features)
- 🔎 [System Architecture](#-system-architecture)
- 🎬 [Get Started](#-get-started)
  - 📝 [Prerequisites](#-prerequisites)
  - 🚀 [Quick Start](#-quick-start)
  - 🔧 [Configuration](#-configuration)
- 🔨 [Launch Service from Source for Development](#-launch-service-from-source-for-development)
  - [Backend only (technical users)](#-backend-only)
- 📜 [Roadmap](#-roadmap)
- 📊 [Benchmark](#-benchmark)
- 🏄 [Community](#-community)
- 🙌 [Contributing](#-contributing)

</details>

---

## 💡 What is RAGEve?

[RAGEve](https://github.com/bazzi24/RAGEve) is a **local-first RAG (Retrieval-Augmented Generation) platform** built for developers and teams who want the power of RAG workflows without depending on external cloud services.

It combines **Ollama** for local LLM inference and embeddings, **Qdrant** as a high-performance vector database, and **FastAPI + Next.js** for a full-featured web interface. Everything runs on your own machine — no API keys, no data leaves your network.

**Backend Architecture**:
- **FastAPI** for high-performance async APIs
- **Peewee ORM** with a 27-table RAGFlow schema for persistent storage
- **MySQL** (or SQLite for single-node) via Peewee + connection pooling (900 connections)
- **SQLAlchemy** (temporary) for legacy chat history storage during migration
- **Qdrant** for vector search with hybrid retrieval (dense + sparse)
- **Ollama** for embeddings and LLM inference

RAGEve is designed for two audiences:

| User | Experience |
|---|---|
| **Non-technical users** | `git clone && ./scripts/run.sh` — everything starts automatically |
| **Developers** | `./scripts/backend.sh` or manual `uvicorn` / `npm run dev` for full control |

---

## 🎮 Demo
<div align="center">
  <img src="docs/assets/demo.gif" alt="RAGEve" />
</div>

Start RAGEve locally and open [http://localhost:3000](http://localhost:3000):

```bash
git clone https://github.com/bazzi24/RAGEve.git
cd RAGEve
./scripts/run.sh
```

> **Tip:** On first run, `install.sh` automatically installs `uv`, Ollama, pulls the required models (~8 GB), and starts Docker services. This takes about 5–10 minutes once, then subsequent starts are instant.

---

## 🔥 Latest Updates

- **2026-04-27** Peewee migration complete — 27-table RAGFlow schema, new `/dialogs` and `/knowledgebases` APIs, transitional support for legacy routes
- **2026-04-22** Enhanced PDF parsing — column detection, structured table extraction, hierarchical chunking, reading order optimization
- **2026-04-03** Evaluation matrix (16-cell benchmark) + Qdrant hybrid search fix
- **2026-04-01** 9 production fixes: structured 500 handler, health checks, rate limiter proxy safety, request timeouts, streaming 404 fix, file upload limits, paginated datasets API
- **2026-04-01** Chat history with MySQL/SQLite, session panel, per-agent conversations
- **2026-03-28** Background HF dataset ingest with live progress tracking
- **2026-03-26** Real-time streaming upload with per-batch progress stages
- **2026-03-26** Cross-encoder reranking (sentence-transformers)
- **2026-03-25** E2E test suite, conversation persistence


---

## 🌟 Key Features

### 🔍 **Deep Document Understanding**

- Ingest PDFs, Word docs, Excel, CSV, images, and more
- **Enhanced PDF parsing**: column detection, structured table extraction (markdown), heading hierarchy, reading order optimization
- Adaptive chunking with quality scoring per profile (clean text, OCR noisy, table-heavy, code)
- Intelligent text column selection for multi-column datasets
- Hierarchical chunking preserves section context for better semantic search

### 🧠 **Grounded Answers with Citations**

- Exact chunk references from source documents
- Quality scores exposed to the LLM via enriched context
- Session history-aware chat with up to 6 prior turns in context

### ⚡ **Multiple Retrieval Strategies**

- Dense vector search via Ollama embeddings
- Sparse keyword search
- Hybrid fusion combining both with configurable weights
- Cross-encoder reranking for improved precision

### 🤖 **Flexible LLM Support**

- Any Ollama model as the chat backend
- Any Ollama embedding model
- Configurable temperature, top-k, top-p, and context window size per dialog (agent)

### 📦 **HuggingFace Integration**

- Browse, preview, and search HuggingFace datasets directly from the UI
- Download datasets to local storage
- Background ingest with real-time progress
- Multi-config and multi-split support

### 🗄️ **Persistent Conversations**

- Sessions stored in MySQL via Peewee ORM (or SQLite for single-node)
- Full conversation history per dialog (agent)
- Thumbs up/down feedback on individual messages
- Conversation context automatically injected into subsequent turns

### 🔧 **Production-Ready Backend**

- Request ID tracing and structured error responses
- CORS and API key authentication
- Circuit breaker and retry logic for Ollama calls
- Dependency health checks (`/health` pings Ollama and Qdrant)

### 🐳 **Developer-Friendly**

- `scripts/run.sh` — everything in one command
- `scripts/backend.sh` — backend only for technical users
- Docker Compose for infrastructure (Qdrant + MySQL)
- Full E2E and stress test suites

---

## 🔎 System Architecture

RAGEve follows a modern full-stack architecture with a local-first design:

```
┌─────────────────────────────────────────────────────────────┐
│                     Next.js Frontend (port 3000)           │
│  - Chat interface                                          │
│  - Knowledge base management                               │
│  - HuggingFace integration                                 │
│  - Dialog (agent) configuration                            │
└────────────────────────────┬──────────────────────────────┘
                             │ HTTPS/HTTP
┌────────────────────────────▼──────────────────────────────┐
│              FastAPI Backend (port 8000)                  │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Routes (API routers)                               │   │
│  │ • /dialogs         — Dialog (agent) CRUD          │   │  ← NEW (Peewee)
│  │ • /knowledgebases  — KB, document, file, task     │   │  ← NEW (Peewee)
│  │ • /conversations   — Conversation + streaming     │   │  ← NEW (Peewee)
│  │ • /chat            — Stateless RAG chat           │   │
│  │ • /datasets        — Legacy (deprecated)          │   │
│  │ • /agents          — Legacy (deprecated)          │   │
│  │ • /chat_history    — Legacy (SQLAlchemy)          │   │
│  └────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Services (Store pattern)                           │   │
│  │ • DialogStore          — Dialog CRUD              │   │
│  │ • KnowledgeBaseStore   — KB, Document, File, Task│   │
│  │ • ConversationStore    — Conversation + messages  │   │
│  │ • TenantUserStore      — Multi-tenancy           │   │
│  │ • LLMStore             — LLM factory management  │   │
│  │ • EvaluationStore      — RAG evaluation          │   │
│  │ • ConnectorStore       — External connectors     │   │
│  │ • CanvasStore          — Agent workflows         │   │
│  │ • SystemStore          — System settings         │   │
│  └────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────┐   │
│  │ Persistence Layer                                  │   │
│  │ • Peewee ORM (27-table RAGFlow schema)           │   │  ← PRIMARY
│  │   Tables: User, Tenant, Knowledgebase, Document, │   │
│  │   File, Task, Dialog, Conversation, LLM, etc.    │   │
│  │ • SQLAlchemy (legacy chat history)               │   │  ← TEMPORARY
│  │   Tables: chat_sessions, chat_messages           │   │
│  └────────────────────────────────────────────────────┘   │
│  ┌────────────────────────────────────────────────────┐   │
│  │ RAG Pipeline (rag/retrieval/rag_pipeline.py)     │   │
│  │ 1. Embed query (dense + sparse)                  │   │
│  │ 2. Qdrant hybrid search with RRF                 │   │
│  │ 3. Optional cross-encoder reranking               │   │
│  │ 4. Build context → Ollama chat                   │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────┬──────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
┌─────────▼──────┐  ┌────────▼────────┐  ┌────▼─────────────┐
│    Qdrant      │  │     MySQL       │  │    Ollama        │
│  (vector DB)   │  │  (Peewee ORM)   │  │  (LLM + embed)   │
│  Port 6333     │  │  27-table schema │  │  Local daemon    │
└────────────────┘  └─────────────────┘  └──────────────────┘
```

### Database Architecture

**Peewee ORM (Primary)** — 27-table RAGFlow schema stored in MySQL:
- **User & Tenancy**: `User`, `Tenant`, `UserTenant`
- **Knowledge Base**: `Knowledgebase`, `Document`, `File`, `File2Document`, `Task`
- **Dialogs**: `Dialog`, `Conversation`
- **LLM Management**: `LLMFactories`, `LLM`, `TenantLLM`
- **Connectors**: `Connector`, `Connector2Kb`, `SyncLogs`
- **Canvas**: `UserCanvas`, `CanvasTemplate`
- **Evaluation**: `EvaluationDataset`, `EvaluationCase`, `EvaluationRun`, `EvaluationResult`
- **System**: `SystemSettings`, `APIToken`, `API4Conversation`, `MCP`, `Search`, `PipelineOperationLog`

**SQLAlchemy (Legacy, Temporary)** — During the migration from SQLAlchemy to Peewee, chat history continues to use the old schema (`chat_sessions`, `chat_messages`, `chat_feedback`) in a separate database. This will be unified with the Peewee `Conversation` table in a future update.

---

## 📊 Database Schema Details

### 27-Table RAGFlow Schema (Peewee ORM)

RAGEve uses a production-ready schema inherited from the RAGFlow project, providing comprehensive data model for knowledge management, conversations, evaluation, and system configuration.

**User & Multi-Tenancy**
- `User` — Application users with authentication
- `Tenant` — Multi-tenant isolation (each tenant has separate KBs, settings)
- `UserTenant` — Many-to-many relationship with role-based access

**Knowledge Management**
- `Knowledgebase` — Container for documents (replaces "datasets")
- `Document` — Parsed document metadata and processing status
- `File` — Uploaded file tracking
- `File2Document` — Link between files and documents
- `Task` — Background ingestion tasks with progress tracking

**Dialogs & Conversations** (replaces legacy "agents")
- `Dialog` — Agent configuration (LLM, prompt, KB associations, retrieval settings)
- `Conversation` — Chat sessions with messages stored as JSON array

**LLM & Embedding Management**
- `LLMFactories` — Provider configurations (Ollama, OpenAI, etc.)
- `LLM` — Available models per factory
- `TenantLLM` — Tenant-specific model selections and API keys

**Data Connectors**
- `Connector` — External data source configurations
- `Connector2Kb` — Connector-to-knowledgebase mappings
- `SyncLogs` — Sync history and error tracking

**Agent Workflows**
- `UserCanvas` — Custom agent workflows (DSL-based)
- `CanvasTemplate` — Reusable workflow templates

**RAG Evaluation**
- `EvaluationDataset` — Test questions and reference answers
- `EvaluationCase` — Individual evaluation examples
- `EvaluationRun` — Execution of evaluation against a dialog
- `EvaluationResult` — Per-case metrics (NDCG, MRR, faithfulness, relevance)

**System Configuration**
- `SystemSettings` — Global key-value settings
- `APIToken` — API token authentication (when enabled)
- `API4Conversation` — Audit log for API-based conversations
- `MCP` — Model Context Protocol server configurations
- `Search` — Saved search configurations
- `PipelineOperationLog` — Detailed ingestion pipeline logs

---

## 🎬 Get Started

### 📝 Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Docker** | >= 24.0.0 | [Install Docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | >= v2.26.1 | Usually bundled with Docker Desktop |
| **macOS / Linux / WSL2** | — | Windows native not supported; use WSL2 |
| **Disk** | >= 50 GB | For models (~8 GB) and data |
| **RAM** | >= 16 GB | Recommended; CPU fallback is slower |

> **Windows:** Enable WSL2 and run all commands from inside the WSL shell. Do not run scripts from PowerShell or CMD.

### 🚀 Quick Start

**One command for everything — auto-installs if needed:**

```bash
git clone https://github.com/bazzi24/RAGEve.git
cd RAGEve
./scripts/run.sh
```

The first run will:
1. Install `uv` (Python package manager)
2. Install Ollama and pull models (`nomic-embed-text` + `llama3.2`)
3. Start Docker containers (Qdrant + MySQL)
4. Start the FastAPI backend and Next.js frontend

Open **[http://localhost:3000](http://localhost:3000)** when you see:

```
[*] Starting FastAPI backend...
[*] Starting Next.js frontend...
[✓] RAGEve is running!

  Frontend  http://localhost:3000
  Backend   http://localhost:8000
  API docs  http://localhost:8000/docs
```

Press **Ctrl+C** to stop all services cleanly.

### 🔧 Configuration

RAGEve uses environment variables for configuration. Copy the example and customize:

```bash
# From the project root:
cp docker/.env.example .env  # Recommended for Docker deployments
# OR
cp .env.example .env        # If .env.example exists (legacy location)
```

**Core Database Settings**

| Variable | Default | Description |
|---|---|---|
| `MYSQL_HOST` | `localhost` | MySQL server hostname (Peewee ORM — primary) |
| `MYSQL_PORT` | `3306` | MySQL server port |
| `MYSQL_USER` | `root` | MySQL username |
| `MYSQL_PASSWORD` | _(empty)_ | MySQL password |
| `MYSQL_DBNAME` | `rag_flow` | MySQL database name (27-table schema) |
| `DB_URL` | _(SQLite)_ | **Legacy:** SQLAlchemy DSN for chat history (e.g., `mysql+aiomysql://...` or `sqlite:///data/chat.db`) |

**Service URLs**

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `QDRANT_API_KEY` | _(none)_ | Qdrant API key when auth is enabled |

**Application Settings**

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:3001,http://localhost:3002` | Allowed CORS origins (comma-separated, no spaces) |
| `TRUSTED_PROXY_COUNT` | `1` | Number of reverse proxies for X-Forwarded-For (0 to disable) |
| `API_KEY` | _(none)_ | When set, enables `X-API-Key` authentication on all endpoints |
| `RATE_LIMIT_PER_MINUTE` | `120` | Rate limit per IP (only active when `API_KEY` is set) |
| `HF_TOKEN` | _(none)_ | HuggingFace token for private datasets |

**Storage & Processing**

| Variable | Default | Description |
|---|---|---|
| `DATA_ROOT` | `data` | Base directory for uploads, chunks, vectors, logs |
| `UPLOAD_DIR_NAME` | `uploads` | Subdirectory for uploaded files |
| `CHUNK_DIR_NAME` | `chunks` | Subdirectory for extracted text chunks |
| `VECTOR_DIR_NAME` | `vector` | Subdirectory for vector index data |

**Advanced PDF Parsing**

| Variable | Default | Description |
|---|---|---|
| `ENABLE_COLUMN_DETECTION` | `true` | Enable multi-column layout detection |
| `ENABLE_STRUCTURED_TABLES` | `true` | Extract tables as markdown |
| `ENABLE_HIERARCHICAL_CHUNKING` | `true` | Preserve section hierarchy in chunks |
| `ENABLE_READING_ORDER_OPTIMIZATION` | `true` | Fix reading order for multi-column docs |
| `OCR_ENGINE` | `paddle` | OCR engine: `paddle` or `tesseract` |
| `OCR_THRESHOLD_CHARS` | `50` | Minimum chars to consider PDF not scanned |

**Upload Limits**

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_BYTES` | `524288000` (500 MB) | Maximum file size |
| `MAX_DATASET_BYTES` | `107374182400` (100 GB) | Maximum total dataset size |

#### Scripts

| Script | Description |
|---|---|
| `./scripts/run.sh` | Everything in one command — auto-installs on first run |
| `./scripts/install.sh` | One-time setup only (called automatically by `run.sh`) |
| `./scripts/backend.sh` | Backend only — for developers who run the frontend manually |

---

## 🔨 Launch Service from Source for Development

For developers who want full control over startup and debugging.

### 📋 Full Stack

```bash
# 1. Start infrastructure
docker compose -f docker/docker-compose.yml up -d qdrant mysql

# 2. Start Ollama (keep running in a terminal)
ollama serve

# 3. Pull required models (first time only)
ollama pull nomic-embed-text
ollama pull llama3.2:latest

# 4. Install Python dependencies
uv sync

# 5. Install frontend dependencies
cd frontend && npm install && cd ..

# 6. Start FastAPI backend (port 8000)
#    Do NOT use --reload — it crashes in-flight uploads
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 7. Start Next.js frontend (port 3000) — in another terminal
cd frontend && npm run dev
```

Open:
- Frontend: [http://localhost:3000](http://localhost:3000)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Qdrant Dashboard: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 🔧 Backend Only

For developers who run the frontend manually (e.g. in an IDE with hot reload):

```bash
./scripts/backend.sh
```

Starts: Docker (Qdrant + MySQL) → Ollama → FastAPI. No frontend.

### 🧪 Run Tests

**Store Unit Tests** (100+ tests across 9 store services):

```bash
uv run python test/test_stores.py
```

Tests: TenantUserStore (14), KnowledgeBaseStore (21), DialogStore (6), ConversationStore (9), LLMStore (12), ConnectorStore (11), CanvasStore (10), EvaluationStore (12), SystemStore (15).

**API Integration Tests** (34+ tests):

```bash
# Run all API tests
uv run python -m pytest test/api/

# Or run individual test files
uv run python test/api/test_dialogs.py
uv run python test/api/test_conversations.py
uv run python test/api/test_knowledgebases.py
uv run python test/api/test_chat.py
uv run python test/api/test_ingestion.py
```

API tests use a SQLite database (`./test_api.db`) and bypass authentication via FastAPI dependency overrides.

**Full End-to-End Test** (requires running Qdrant + Ollama):

```bash
uv run python -m pytest test/integration/test_rag.py
```

**Legacy Tests** (pre-migration):

```bash
uv run python test/_test_e2e.py
uv run python test/_test_stress.py --test all --stream --keep-files
```

---

## 🔌 API Reference

### Base URL

All API endpoints are relative to `http://localhost:8000` (or your configured backend URL).

### Authentication & Security

- **API Key**: When `API_KEY` is set in `.env`, all endpoints require the header `X-API-Key: <your-key>`
- **Request ID**: Every response includes `X-Request-ID` header for tracing
- **CORS**: Configure allowed origins via `CORS_ORIGINS` (comma-separated)
- **Rate Limiting**: Active only when `API_KEY` is set (default: 120 req/min per IP)

### Health Check

```
GET /health
```

Verifies connectivity to Ollama and Qdrant. Returns:
```json
{
  "status": "ok" | "degraded",
  "ollama": "ok" | "unreachable",
  "qdrant": "ok" | "unreachable"
}
```

### New Routes (Peewee-based)

These are the primary endpoints after the Peewee migration:

#### Dialogs (Agents)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/dialogs/` | Create a new dialog (agent configuration) |
| `GET` | `/dialogs/` | List dialogs (filter by `tenant_id`) |
| `GET` | `/dialogs/{dialog_id}` | Get dialog details |
| `PUT` | `/dialogs/{dialog_id}` | Update dialog |
| `DELETE` | `/dialogs/{dialog_id}` | Delete dialog |

#### Knowledge Bases (Datasets)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/knowledgebases/` | Create knowledge base |
| `GET` | `/knowledgebases/` | List knowledge bases |
| `GET` | `/knowledgebases/{kb_id}` | Get knowledge base details |
| `PUT` | `/knowledgebases/{kb_id}` | Update knowledge base |
| `DELETE` | `/knowledgebases/{kb_id}` | Delete KB and Qdrant collection |
| `POST` | `/knowledgebases/{kb_id}/upload` | Upload files for ingestion |
| `GET` | `/knowledgebases/documents` | List documents (filter by `kb_id`) |
| `GET` | `/knowledgebases/documents/{doc_id}` | Document details + progress |
| `GET` | `/knowledgebases/tasks/{task_id}` | Ingestion task progress |
| `GET` | `/knowledgebases/documents/{doc_id}/tasks` | All tasks for a document |

#### Conversations (Persistent Chat)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/conversations/` | Create conversation |
| `GET` | `/conversations/` | List conversations (filter by `dialog_id`, `user_id`) |
| `GET` | `/conversations/{id}` | Get conversation with full message history |
| `POST` | `/conversations/{id}/messages` | Append message to conversation |
| `GET` | `/conversations/{id}/context` | Get last N turns formatted for LLM |
| `POST` | `/conversations/{id}/chat/stream` | **Streaming** RAG chat with persistence |

#### Stateless Chat (RAG without persistence)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat/{dialog_id}` | Non-streaming RAG chat |
| `POST` | `/chat/{dialog_id}/stream` | **Streaming** RAG chat (NDJSON) |

### Legacy Routes (Deprecated)

These routes remain for backward compatibility but will be removed in a future version:

| Route | Purpose | Migration Target |
|-------|---------|------------------|
| `/agents/*` | Agent CRUD (JSON file-based) | Use `/dialogs` (Peewee-backed) |
| `/datasets/*` | Dataset/file operations | Use `/knowledgebases` |
| `/chat_history/*` | Chat history (SQLAlchemy) | Use `/conversations` |
| `/files/*` | File management | Use `/knowledgebases/{kb_id}/upload` |

### Streaming Format (NDJSON)

Streaming endpoints return newline-delimited JSON objects:

```
{"event": "chunk", "content": "Hello"}
{"event": "chunk", "content": " world"}
{"event": "end", "sources": [...], "use_hybrid": true, "elapsed_s": 1.23}
```

On error:
```
{"event": "error", "error": "Error message", "message_id": "..."}
```

### Error Responses

Standard error format:
```json
{
  "error": "Human-readable message",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 📊 Benchmark

RAGEve's retrieval pipeline is benchmarked on **100 SQuAD questions** across every combination of embedding model, LLM, and search strategy. All metrics are computed automatically by an LLM-as-judge — no manual scoring. I run local with NVIDIA 1650, if you use stronger GPU, i think benchmark will better. If you clone this project and run with stronger GPU, give me feedback.

### Methodology

| Dimension | Options |
|---|---|
| **Embedding models** | nomic-embed-text (768d), qwen3-embedding (4096d) |
| **LLM** | llama3.2, SmolLM2-1.7B |
| **Search strategies** | Dense · Hybrid · Hybrid+Rerank · Dense+Rerank |
| **Dataset** | SQuAD v1.1 (100 questions) |
| **Retrieval top-k** | 5 |

**Metrics:** NDCG@K, MRR, Recall@K (retrieval) · Faithfulness, Answer Relevance (LLM-as-judge)

### Results — nomic-embed-text (768d) + llama3.2

| Mode | NDCG@K | MRR | Recall@K | Answer Relevance |
|---|---:|---:|---:|---:|
| **Dense** | 0.30 | 0.30 | 0.30 | **0.54** |
| **Hybrid** | 0.23 | 0.23 | 0.30 | 0.36 |
| **Hybrid+Rerank** | 0.24 | 0.25 | 0.30 | 0.29 |
| **Dense+Rerank** | **0.40** | **0.40** | **0.40** | 0.35 |

### Results — qwen3-embedding (4096d) + llama3.2

| Mode | NDCG@K | MRR | Recall@K | Answer Relevance |
|---|---:|---:|---:|---:|
| **Dense** | **0.50** | **0.50** | **0.50** | 0.44 |
| **Hybrid** | 0.30 | 0.37 | **0.50** | **0.70** |
| **Hybrid+Rerank** | 0.41 | 0.50 | **0.50** | 0.53 |
| **Dense+Rerank** | **0.50** | **0.50** | **0.50** | 0.64 |

> Higher is better for all metrics. Bold = best in column.

### Key Findings

- **qwen3-embedding (4096d) dramatically outperforms nomic-embed-text (768d)** — Dense retrieval alone gives qwen3 a **0.50 NDCG** vs nomic's 0.30, a **67% relative improvement**
- **Dense+Rerank** is the safest strategy — best retrieval quality on both models with consistent Answer Relevance
- **Hybrid search shines on qwen3** — Answer Relevance jumps to **0.70** (vs 0.44 Dense), because keyword matching supplements semantic search for factoid questions
- **Cross-encoder reranking** lifts NDCG/MRR on both models — the reranker refines ranking beyond raw similarity scores

### Performance Breakdown

<div align="center">
  <img src="docs/assets/benchmark_chart.png" alt="RAGEve Benchmark Results — nomic vs qwen3 on SQuAD v1.1" width="860" />
</div>

### Run Your Own Benchmark

```bash
# Full 16-cell matrix, 100 SQuAD questions
uv run python test/benchmark/evaluation/matrix.py --samples 100

# One embed model, all modes
uv run python test/benchmark/evaluation/matrix.py --samples 100 --embed qwen3 --llm llama3.2

# Quick smoke test
uv run python test/benchmark/evaluation/matrix.py --samples 10 --embed nomic --llm llama3.2

# Filter to specific search modes
uv run python test/benchmark/evaluation/matrix.py --samples 100 --mode rerank hybrid
```

Results are saved to `data/benchmarks/matrix-<timestamp>.json` with full per-sample answers and judge scores.

---

## 📜 Roadmap


- [x] RAGFlow-style deep document parsing (layout awareness, table extraction, hierarchical chunking, reading order)
- [x] PDF preview with highlighted citations
- [ ] API rate limiting per-user
- [ ] Multi-user / session isolation
- [ ] Webhook support for external integrations

---

## 🏄 Community

- 🐛 [Bug Reports](https://github.com/bazzi24/RAGEve/issues) — report issues with clear reproduction steps
- 💡 [Feature Requests](https://github.com/bazzi24/RAGEve/issues) — open a discussion or issue
- 🤝 [Contributing](https://github.com/bazzi24/RAGEve/blob/main/CONTRIBUTING.md) — see below

---

## 🙌 Contributing

RAGEve grows through open-source collaboration. Contributions of all kinds are welcome — bug fixes, features, docs, tests, and feedback.

**Before contributing:**

1. Fork the repository and create a feature branch from `main`
2. Make your changes — all code must pass `bash -n scripts/*.sh` (shell scripts) and `cd frontend && npx tsc --noEmit` (TypeScript)
3. Run the E2E test suite: `uv run python test/_test_e2e.py`
4. Submit a pull request with a clear description of what changed and why

**Development setup:**

```bash
git clone https://github.com/bazzi24/RAGEve.git
cd RAGEve
cp .env.example .env    # optional: fill in HF_TOKEN, API_KEY, etc.
./scripts/install.sh  # one-time setup
./scripts/backend.sh  # backend only for iterative development
```


---

<p align="center">
Built with ❤️ for local-first AI — RAGEve
</p>
