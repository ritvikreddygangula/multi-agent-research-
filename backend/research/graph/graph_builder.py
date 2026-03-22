"""
LangGraph StateGraph assembly.

Topology:
    START
      └─► planner
            └─► fan_out  (Send API — one Send per sub-question)
                  ├─► branch_0 ─┐
                  ├─► branch_1 ─┤
                  ├─► branch_2 ─┼─► aggregator ◄─────────────────┐
                  ├─► branch_3 ─┤       │                         │
                  └─► branch_4 ─┘       ▼                    (retry if
                                      critic                  score < 0.72
                                        │                    & iter < 2)
                                        └──── synthesizer ─► END
"""

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from .state import ResearchState
from .nodes import (
    planner_node,
    branch_research_node,
    aggregator_node,
    critic_node,
    synthesizer_node,
)

MAX_BRANCHES = 5   # max parallel sub-questions


# ── Fan-out edge function ─────────────────────────────────────────────────────

def fan_out_branches(state: ResearchState):
    """
    Called after planner. Returns one Send() per sub-question so LangGraph
    runs them as independent parallel branches.
    Branches that exceed sub_questions length are skipped by the node guard.
    """
    n = min(len(state.get("sub_questions", [])), MAX_BRANCHES)
    return [Send(f"branch_{i}", state) for i in range(n)]


# ── Critic routing (real retry loop) ─────────────────────────────────────────

def route_after_critic(state: ResearchState) -> str:
    """
    If the latest critic feedback passed → synthesizer.
    If it failed AND we haven't hit the iteration cap → aggregator (retry).
    The cap is enforced inside critic_node itself (passed=True when cap reached),
    so this function just reads the flag.
    """
    feedbacks = state.get("critic_feedback", [])
    if not feedbacks:
        return "synthesizer"

    latest = feedbacks[-1]
    if latest.get("passed", True):
        return "synthesizer"
    return "aggregator"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_research_graph():
    builder = StateGraph(ResearchState)

    # Register nodes
    builder.add_node("planner", planner_node)

    for i in range(MAX_BRANCHES):
        builder.add_node(f"branch_{i}", branch_research_node(i))

    builder.add_node("aggregator", aggregator_node)
    builder.add_node("critic", critic_node)
    builder.add_node("synthesizer", synthesizer_node)

    # Edges: START → planner
    builder.add_edge(START, "planner")

    # Conditional fan-out: planner → [branch_0 .. branch_N] via Send()
    builder.add_conditional_edges(
        "planner",
        fan_out_branches,
        [f"branch_{i}" for i in range(MAX_BRANCHES)],
    )

    # Fan-in: every branch → aggregator
    for i in range(MAX_BRANCHES):
        builder.add_edge(f"branch_{i}", "aggregator")

    # aggregator → critic → (route) → synthesizer
    builder.add_edge("aggregator", "critic")
    builder.add_conditional_edges(
        "critic",
        route_after_critic,
        {"synthesizer": "synthesizer", "aggregator": "aggregator"},
    )

    # synthesizer → END
    builder.add_edge("synthesizer", END)

    return builder.compile()


# Module-level compiled graph — import this everywhere
research_graph = build_research_graph()
