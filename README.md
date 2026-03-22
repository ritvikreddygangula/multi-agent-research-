# Multi-Agent Research Platform

A full-stack web application that uses a team of AI agents to research any topic and produce a structured, sourced report. Instead of asking one model a question and getting one answer, this platform breaks the problem down, researches it in parallel, critiques the result, and synthesizes everything into something actually useful.

I built this to go beyond the typical "send a prompt, get a response" pattern and explore what a more realistic AI pipeline looks like when you care about reliability and traceability.

---

## What it does

You type in a topic — say, "the long-term effects of social media on teenage mental health" — and the platform:

1. **Plans** the research by decomposing the topic into specific sub-questions
2. **Retrieves** context from past similar runs using vector memory (Pinecone)
3. **Researches** each sub-question in parallel using web search, Wikipedia, and arXiv
4. **Aggregates** all the branch findings and deduplicates them
5. **Critiques** the synthesis and sends it back for revision if the quality score is too low
6. **Synthesizes** everything into a final report with confidence scores and source citations
7. **Saves** the run to Pinecone so future searches on similar topics can benefit from it

The whole pipeline runs as a live graph — you can watch each agent node light up in real time as it completes.

---

## Architecture

The backend is orchestrated with **LangGraph**, which lets me define the agent pipeline as an explicit state machine with typed state, parallel branches, and conditional retry logic. This is very different from chaining prompts together — every node has a clear contract: it receives the shared state, does one job, and returns only what it changed.

```
START
  └─► Planner
        └─► RAG Retrieval  (Pinecone semantic search over past runs)
              └─► Fan-out  (one parallel branch per sub-question, up to 5)
                    ├─► Branch 0 ─┐
                    ├─► Branch 1 ─┤
                    ├─► Branch 2 ─┼─► Aggregator
                    ├─► Branch 3 ─┤       │
                    └─► Branch 4 ─┘       ▼
                                        Critic ──► (retry if score < 0.72)
                                          │
                                          └─► Synthesizer ──► END
                                                  │
                                            (upsert to Pinecone)
```

### Agent roles

| Agent | Job |
|---|---|
| **Planner** | Breaks the topic into up to 5 focused sub-questions |
| **RAG Retrieval** | Queries Pinecone for semantically similar past research runs |
| **Branch Researchers** | Each branch researches one sub-question using web/Wikipedia/arXiv tools |
| **Aggregator** | Merges all branch findings, deduplicates, computes confidence |
| **Critic** | Scores the aggregated result and flags gaps or low-confidence claims |
| **Synthesizer** | Writes the final structured report and stores it back to Pinecone |

### Key design decisions

- **Parallel fan-out via LangGraph's Send API** — branches run concurrently, not sequentially
- **Partial failure tolerance** — if one branch errors, the rest continue; the aggregator works with what it has
- **Retry loop** — if the critic scores the synthesis below 0.72, it routes back to the aggregator for another pass (max 2 retries)
- **Vector memory** — every completed run is embedded and stored in Pinecone so the RAG node can pull in relevant prior context on future queries
- **SSE streaming** — the Django backend streams `node_update` events over Server-Sent Events as each node completes, so the frontend graph updates in real time

---

## Tech stack

**Backend**
- Python / Django + Django REST Framework
- LangGraph (StateGraph with typed state via TypedDict)
- LangChain tools (web search, Wikipedia, arXiv)
- Pinecone (vector memory, text-embedding-ada-002)
- OpenAI GPT-4o
- JWT authentication (djangorestframework-simplejwt)
- Server-Sent Events for streaming

**Frontend**
- React 18
- React Flow (live agent graph visualization)
- React Router 6
- Fetch API with streaming SSE reader

---

## Project structure

```
multi-agent-research-team/
├── backend/
│   ├── core/                    # Django settings
│   ├── auth_app/                # Signup / login endpoints
│   └── research/
│       ├── graph/
│       │   ├── graph_builder.py # LangGraph StateGraph definition
│       │   ├── nodes.py         # All agent node implementations
│       │   ├── state.py         # Typed shared state (TypedDict)
│       │   ├── tools.py         # Web/Wikipedia/arXiv tool wrappers
│       │   └── pinecone_memory.py # Vector upsert and retrieval
│       ├── services/
│       │   └── research_service.py  # Entrypoint used by views
│       └── views.py             # Thin API views + SSE streaming endpoint
└── frontend/
    └── src/
        ├── components/
        │   └── AgentGraphView.js  # React Flow live graph
        ├── pages/
        │   ├── Home.js            # Research input + live graph preview
        │   └── Results.js         # Final report with findings + sources
        └── services/
            └── researchService.js # SSE stream reader
```

---

## Running it locally

### Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key
- Pinecone account (free tier works)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```
SECRET_KEY=any-random-string
DEBUG=True
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk-...
PINECONE_INDEX_NAME=research-memory
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

Create a `.env` file in `frontend/`:

```
REACT_APP_API_URL=http://localhost:8000
```

```bash
npm start
```

Open `http://localhost:3000`, create an account, and start researching.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/signup/` | Register a new user |
| POST | `/api/auth/login/` | Get JWT token pair |
| POST | `/api/research/` | Run full pipeline, returns final JSON report |
| POST | `/api/research/stream/` | Same pipeline over SSE — streams node updates in real time |

---

## What the results look like

Each research run returns:

- **Executive summary** — high-level overview of the topic
- **Key concepts** — important terms and ideas surfaced during research
- **Important findings** — per-branch findings with individual confidence scores and source links
- **Confidence score** — overall quality score from the critic (0–1)
- **Sources** — all web, Wikipedia, and arXiv sources cited, color-coded by type

On the results page you can also expand a frozen snapshot of the agent graph showing which nodes ran and completed.

---

## Environment variables

| Variable | Where | Purpose |
|---|---|---|
| `SECRET_KEY` | backend | Django secret key |
| `DEBUG` | backend | Enable debug mode |
| `OPENAI_API_KEY` | backend | GPT-4o access |
| `PINECONE_API_KEY` | backend | Pinecone vector store |
| `PINECONE_INDEX_NAME` | backend | Name of your Pinecone index (1536 dims) |
| `REACT_APP_API_URL` | frontend | Backend base URL |
