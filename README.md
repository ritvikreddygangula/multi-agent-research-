# Multi-Agent Research Platform

A full-stack AI research platform that decomposes any topic into parallel sub-questions, researches each one independently using web search, Wikipedia, and arXiv, critiques the result, and synthesizes everything into a sourced, structured report — all streamed live to the UI.

Built to demonstrate a production-grade multi-agent architecture using LangGraph, not just a single LLM prompt.

---

## What it does

Type in a topic — e.g. *"the long-term effects of social media on teenage mental health"* — and the platform:

1. **Plans** the research by decomposing the topic into focused sub-questions
2. **Retrieves** context from past similar runs using Pinecone vector memory
3. **Researches** each sub-question in parallel using web search, Wikipedia, and arXiv
4. **Aggregates** all branch findings and deduplicates overlapping evidence
5. **Critiques** the synthesis and routes it back for revision if the quality score is too low
6. **Synthesizes** a final report with confidence scores and source citations
7. **Saves** the run to Pinecone so future queries on similar topics benefit from it

Every node in the pipeline streams status updates to the frontend in real time — you can watch the agent graph light up as each step completes.

---

## Architecture

The backend runs as an explicit **LangGraph StateGraph** — a typed state machine where every node has a clear contract: receive shared state, do one job, return only what changed.

```
START
  └─► Planner
        └─► RAG Retrieval      (Pinecone semantic search over past runs)
              └─► Fan-out      (parallel branch per sub-question, up to 5)
                    ├─► Branch 0 ─┐
                    ├─► Branch 1 ─┤
                    ├─► Branch 2 ─┼─► Aggregator
                    ├─► Branch 3 ─┤        │
                    └─► Branch 4 ─┘        ▼
                                         Critic ──► (retry if score < 0.72, max 2×)
                                           │
                                           └─► Synthesizer ──► END
                                                   │
                                             (upsert to Pinecone)
```

### Agent roles

| Agent | Responsibility |
|---|---|
| **Planner** | Decomposes topic into up to 5 focused sub-questions |
| **RAG Retrieval** | Pulls semantically similar prior research from Pinecone |
| **Branch Researchers** | Each branch researches one sub-question independently |
| **Aggregator** | Merges branch findings, deduplicates evidence, computes confidence |
| **Critic** | Scores synthesis quality and flags gaps or weak claims |
| **Synthesizer** | Writes the final structured report and stores it in Pinecone |

### Key design decisions

- **Parallel fan-out** via LangGraph's `Send` API — branches execute concurrently
- **Partial failure tolerance** — a failing branch doesn't block the rest; the aggregator works with what it has
- **Critic retry loop** — if the quality score is below 0.72, the graph routes back through the aggregator (capped at 2 iterations)
- **Vector memory** — every completed run is embedded and stored so future queries on similar topics get prior context for free
- **Real SSE streaming** — the backend streams `node_update` events as each node completes; the frontend graph updates live

---

## Tech stack

**Backend**
- Python 3.11 / Django 4.2 + Django REST Framework
- LangGraph — StateGraph with typed state (TypedDict + operator.add reducers)
- LangChain — tool wrappers for Tavily web search, Wikipedia, arXiv
- Pinecone — vector memory (text-embedding-ada-002, 1536 dims)
- OpenAI GPT-4o
- JWT authentication via `djangorestframework-simplejwt`
- Server-Sent Events for real-time streaming
- PostgreSQL (production) / SQLite (local dev)
- Gunicorn + Whitenoise for production serving

**Frontend**
- React 18
- React Flow — live agent graph visualization
- React Router 6
- Fetch API with SSE stream reader

**Infrastructure**
- Backend: [Render](https://render.com) (free tier web service)
- Frontend: [Render](https://render.com) (free tier static site)
- Database: [Neon](https://neon.tech) (free tier PostgreSQL)

---

## Project structure

```
multi-agent-research-team/
├── backend/
│   ├── core/
│   │   ├── settings.py          # Django config, env vars, security settings
│   │   └── urls.py              # Root URL routing
│   ├── accounts/
│   │   ├── models.py            # Custom User model + UserTokenBudget
│   │   ├── views.py             # Signup / login endpoints
│   │   └── serializers.py       # User schema
│   ├── research/
│   │   ├── graph/
│   │   │   ├── graph_builder.py # LangGraph StateGraph definition
│   │   │   ├── nodes.py         # All 6 node implementations
│   │   │   ├── state.py         # Typed shared state (TypedDict)
│   │   │   ├── tools.py         # Web / Wikipedia / arXiv tool wrappers
│   │   │   └── pinecone_memory.py # Vector upsert and retrieval
│   │   ├── services/
│   │   │   └── research_service.py  # LangGraph orchestration entrypoint
│   │   ├── models.py            # ResearchHistory — persists completed runs
│   │   ├── serializers.py       # History response schema
│   │   └── views.py             # API views + SSE streaming endpoint
│   ├── Procfile                 # gunicorn start command
│   ├── runtime.txt              # Python version pin for Render
│   └── requirements.txt
└── frontend/
    └── src/
        ├── components/
        │   ├── AgentGraphView.js  # React Flow live graph visualization
        │   └── HistorySidebar.js  # Past research runs drawer
        ├── pages/
        │   ├── Home.js            # Research input + live graph
        │   ├── Results.js         # Final report — findings, sources, confidence
        │   ├── History.js         # Research history list
        │   ├── Login.js
        │   └── Signup.js
        ├── services/
        │   ├── authService.js     # API client + safe storage fallback
        │   └── researchService.js # SSE stream reader
        └── context/
            └── AuthContext.js     # Auth state + token management
```

---

## Running locally

### Prerequisites

- Python 3.11
- Node.js 18+
- OpenAI API key
- Pinecone account (free tier works)
- Tavily API key (free tier at [tavily.com](https://tavily.com))

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SECRET_KEY=any-long-random-string
DEBUG=True
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk-...
PINECONE_INDEX_NAME=research-memory
TAVILY_API_KEY=tvly-...
DEFAULT_TOKEN_LIMIT=100000
```

```bash
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:8000
```

```bash
npm start
```

Open `http://localhost:3000`, create an account, and start researching.

---

## API reference

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/signup/` | — | Register a new user |
| `POST` | `/api/auth/login/` | — | Authenticate, returns JWT pair |
| `POST` | `/api/research/` | JWT | Run full pipeline, returns JSON report |
| `POST` | `/api/research/stream/` | JWT | Same pipeline streamed over SSE |
| `GET` | `/api/research/budget/` | JWT | Current token usage and limit |
| `GET` | `/api/research/history/` | JWT | List all past research runs |
| `GET` | `/api/research/history/<id>/` | JWT | Get a specific run |
| `PATCH` | `/api/research/history/<id>/` | JWT | Rename a run |
| `DELETE` | `/api/research/history/<id>/` | JWT | Delete a run |

---

## Environment variables

| Variable | Service | Purpose |
|---|---|---|
| `SECRET_KEY` | backend | Django secret key (required, no default) |
| `DEBUG` | backend | `True` for local dev, `False` in production |
| `DATABASE_URL` | backend | PostgreSQL connection string (falls back to SQLite) |
| `OPENAI_API_KEY` | backend | GPT-4o + embeddings |
| `PINECONE_API_KEY` | backend | Pinecone vector store |
| `PINECONE_INDEX_NAME` | backend | Index name (1536-dim cosine, default: `research-memory`) |
| `TAVILY_API_KEY` | backend | Web search |
| `DEFAULT_TOKEN_LIMIT` | backend | Per-user token budget (default: 100,000) |
| `ALLOWED_HOSTS` | backend | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | backend | Comma-separated frontend origins |
| `REACT_APP_API_URL` | frontend | Backend base URL (baked in at build time) |

---

## Deployment (Render + Neon — free tier)

| Service | Platform | Notes |
|---|---|---|
| Backend | Render Web Service | Root dir: `backend`, build: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput` |
| Frontend | Render Static Site | Root dir: `frontend`, build: `npm install && npm run build`, publish: `build` |
| Database | Neon | Free PostgreSQL — paste connection string as `DATABASE_URL` |
