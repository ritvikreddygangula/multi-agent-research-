"""
Research service layer.

LangGraphResearchService  — graph-based orchestrator (Steps 4+)
ResearchService           — legacy sequential pipeline (kept as fallback)
"""
import uuid
from research.agents import PlannerAgent, ResearchAgent, SynthesizerAgent


class ResearchService:
    """Legacy sequential pipeline — kept as fallback."""

    def __init__(self):
        self.planner = PlannerAgent()
        self.research = ResearchAgent()
        self.synthesizer = SynthesizerAgent()

    def conduct_research(self, topic: str) -> dict:
        try:
            planner_result = self.planner.execute(topic)
            research_result = self.research.execute(topic, context={"plan": planner_result.get("plan", {})})
            synthesis_result = self.synthesizer.execute(topic, context={"planner": planner_result, "research": research_result})
            return {
                "topic": topic,
                "overview": synthesis_result.get("synthesis", {}).get("overview", ""),
                "key_concepts": synthesis_result.get("synthesis", {}).get("key_concepts", []),
                "important_findings": synthesis_result.get("synthesis", {}).get("important_findings", []),
                "summary": synthesis_result.get("synthesis", {}).get("summary", ""),
            }
        except Exception as e:
            raise Exception(f"Research service error: {e}")


class LangGraphResearchService:
    """Graph-based orchestrator using LangGraph StateGraph."""

    def _build_initial_state(self, topic: str) -> dict:
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

    def invoke(self, topic: str) -> dict:
        from research.graph.graph_builder import research_graph
        final_state = research_graph.invoke(self._build_initial_state(topic))
        return final_state.get("final_report", {})

    def stream(self, topic: str):
        from research.graph.graph_builder import research_graph
        for event in research_graph.stream(self._build_initial_state(topic), stream_mode="updates"):
            for node_name, patch in event.items():
                yield {
                    "type": "node_update",
                    "node": node_name,
                    "node_statuses": patch.get("node_statuses", {}),
                    "graph_events": patch.get("graph_events", []),
                }
                if node_name == "synthesizer" and patch.get("final_report"):
                    yield {"type": "complete", **patch["final_report"]}
