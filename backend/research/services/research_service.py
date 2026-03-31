"""
Research service — LangGraph orchestration entrypoint.

All research runs go through the LangGraph StateGraph defined in research/graph/.
"""
import uuid


def _initial_state(topic: str) -> dict:
    return {
        "topic": topic,
        "run_id": str(uuid.uuid4()),
        "sub_questions": [],
        "key_aspects": [],
        "understanding": "",
        "rag_context": [],
        "branch_results": [],
        "synthesis_draft": "",
        "critic_feedback": [],
        "critic_iteration": 0,
        "max_critic_iterations": 2,
        "final_report": {},
        "graph_events": [],
        "node_statuses": {},
        "errors": [],
    }


class LangGraphResearchService:
    """Orchestrates research through the LangGraph StateGraph."""

    def invoke(self, topic: str) -> dict:
        """Run the full graph synchronously and return the final report."""
        from research.graph.graph_builder import research_graph
        final_state = research_graph.invoke(_initial_state(topic))
        return final_state.get("final_report", {})

    def stream(self, topic: str):
        """
        Stream graph execution as SSE-compatible events.

        Yields:
          - node_update  — emitted after each node completes, carries node name and statuses
          - complete     — emitted once the synthesizer node produces a final_report
        """
        from research.graph.graph_builder import research_graph
        for event in research_graph.stream(_initial_state(topic), stream_mode="updates"):
            for node_name, patch in event.items():
                yield {
                    "type": "node_update",
                    "node": node_name,
                    "node_statuses": patch.get("node_statuses", {}),
                    "graph_events": patch.get("graph_events", []),
                }
                if node_name == "synthesizer" and patch.get("final_report"):
                    yield {"type": "complete", **patch["final_report"]}
