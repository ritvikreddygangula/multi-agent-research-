"""
LangGraph StateGraph assembly.

Topology:
    START
      └─► planner
            └─► rag_retrieval          (query Pinecone for prior similar runs)
                  └─► fan_out          (Send API — one Send per sub-question)
                        ├─► branch_0 ─┐
                        ├─► branch_1 ─┤
                        ├─► branch_2 ─┼─► aggregator ◄──────────────┐
                        ├─► branch_3 ─┤       │                      │
                        └─► branch_4 ─┘       ▼                 (retry if
                                            critic            score < 0.72
                                              │               & iter < 2)
                                              └──► synthesizer ──► END
                                                       │
                                                  (upsert to Pinecone)
"""

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from .state import ResearchState
from .nodes import (
    planner_node,
    rag_retrieval_node,
    branch_research_node,
    aggregator_node,
    critic_node,
    synthesizer_node,
)

MAX_BRANCHES = 5


# ── Fan-out ───────────────────────────────────────────────────────────────────

def fan_out_branches(state: ResearchState):
    """One Send() per sub-question — runs branches in parallel."""
    n = min(len(state.get("sub_questions", [])), MAX_BRANCHES)
    return [Send(f"branch_{i}", state) for i in range(n)]


# ── Critic routing ────────────────────────────────────────────────────────────

def route_after_critic(state: ResearchState) -> str:
    feedbacks = state.get("critic_feedback", [])
    if not feedbacks or feedbacks[-1].get("passed", True):
        return "synthesizer"
    return "aggregator"


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_research_graph():
    builder = StateGraph(ResearchState)

    builder.add_node("planner", planner_node)
    builder.add_node("rag_retrieval", rag_retrieval_node)

    for i in range(MAX_BRANCHES):
        builder.add_node(f"branch_{i}", branch_research_node(i))

    builder.add_node("aggregator", aggregator_node)
    builder.add_node("critic", critic_node)
    builder.add_node("synthesizer", synthesizer_node)

    # START → planner → rag_retrieval → fan_out → branches
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "rag_retrieval")
    builder.add_conditional_edges(
        "rag_retrieval",
        fan_out_branches,
        [f"branch_{i}" for i in range(MAX_BRANCHES)],
    )

    # branches → aggregator → critic → (route) → synthesizer → END
    for i in range(MAX_BRANCHES):
        builder.add_edge(f"branch_{i}", "aggregator")

    builder.add_edge("aggregator", "critic")
    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {"synthesizer": "synthesizer", "aggregator": "aggregator"},
    )
    builder.add_edge("synthesizer", END)

    return builder.compile()


research_graph = build_research_graph()
