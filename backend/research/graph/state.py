from typing import TypedDict, List, Optional, Literal, Annotated
import operator


def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer: merge two dicts, b wins on key conflict. Safe for parallel fan-in."""
    return {**a, **b}


class Source(TypedDict):
    title: str
    url: str
    snippet: str
    source_type: Literal["web", "wikipedia", "arxiv"]
    relevance_score: float


class SubQuestionResult(TypedDict):
    question: str
    findings: str
    sources: List[Source]
    confidence: float          # 0.0 – 1.0
    status: Literal["pending", "running", "done", "failed"]
    error: Optional[str]


class CriticFeedback(TypedDict):
    passed: bool
    score: float               # 0.0 – 1.0
    issues: List[str]
    suggestions: List[str]
    iteration: int


class GraphEvent(TypedDict):
    node: str
    status: str                # "started" | "done" | "retry" | "failed"
    ts: float
    meta: Optional[dict]       # extra info (e.g. critic score, branch index)


class ResearchState(TypedDict):
    # ── Input ──────────────────────────────────────────────────────────
    topic: str
    run_id: str

    # ── Planner output ─────────────────────────────────────────────────
    sub_questions: List[str]
    key_aspects: List[str]
    understanding: str

    # ── RAG context fetched from Pinecone before fan-out ───────────────
    rag_context: List[dict]

    # ── Parallel branch results (reducer APPENDS — safe for fan-in) ────
    branch_results: Annotated[List[SubQuestionResult], operator.add]

    # ── Aggregator + critic state ──────────────────────────────────────
    synthesis_draft: str
    critic_feedback: Annotated[List[CriticFeedback], operator.add]
    critic_iteration: int
    max_critic_iterations: int

    # ── Final output ───────────────────────────────────────────────────
    final_report: dict         # overview, key_concepts, findings, summary, sources, confidence_score

    # ── Execution telemetry (reducer APPENDS — streams to frontend) ────
    graph_events: Annotated[List[GraphEvent], operator.add]
    node_statuses: Annotated[dict, _merge_dicts]   # safe parallel writes from branches

    # ── Error tracking (reducer APPENDS — safe for parallel branches) ──
    errors: Annotated[List[str], operator.add]
