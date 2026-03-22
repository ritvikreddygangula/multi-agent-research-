"""
Research service for orchestrating multi-agent research.

LangGraphResearchService  — new graph-based orchestrator (Steps 4+)
ResearchService           — legacy sequential pipeline (kept as fallback)
"""
from research.agents import PlannerAgent, ResearchAgent, SynthesizerAgent
import concurrent.futures
import uuid


class ResearchService:
    """Service for coordinating multi-agent research."""
    
    def __init__(self):
        """Initialize research service with agents."""
        self.planner = PlannerAgent()
        self.research = ResearchAgent()
        self.synthesizer = SynthesizerAgent()
    
    def conduct_research(self, topic: str) -> dict:
        """
        Conduct multi-agent research on a topic.
        
        Flow:
        1. Planner agent creates research plan
        2. Research agent performs deep research (uses planner context)
        3. Synthesizer agent creates final output (uses planner + research context)
        
        Args:
            topic: The research topic
            
        Returns:
            Dictionary with final research results
        """
        try:
            # Step 1: Planner creates research plan
            planner_result = self.planner.execute(topic)
            
            # Step 2: Research agent performs deep research (with planner context)
            research_context = {
                'plan': planner_result.get('plan', {})
            }
            research_result = self.research.execute(topic, context=research_context)
            
            # Step 3: Synthesizer creates final output (with all context)
            synthesis_context = {
                'planner': planner_result,
                'research': research_result
            }
            synthesis_result = self.synthesizer.execute(topic, context=synthesis_context)
            
            # Return structured result
            return {
                "topic": topic,
                "overview": synthesis_result.get('synthesis', {}).get('overview', ''),
                "key_concepts": synthesis_result.get('synthesis', {}).get('key_concepts', []),
                "important_findings": synthesis_result.get('synthesis', {}).get('important_findings', []),
                "summary": synthesis_result.get('synthesis', {}).get('summary', ''),
                "agent_results": {
                    "planner": planner_result,
                    "research": research_result,
                    "synthesizer": synthesis_result
                }
            }
        except Exception as e:
            raise Exception(f"Research service error: {str(e)}")


class LangGraphResearchService:
    """
    Graph-based orchestrator using LangGraph StateGraph.
    Replaces the sequential ResearchService with parallel branch execution,
    adversarial critic loop, Pinecone RAG, and confidence scoring.
    """

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
        """
        Run the full research graph synchronously.
        Returns the final_report from the completed state.
        """
        from research.graph.graph_builder import research_graph

        initial_state = self._build_initial_state(topic)
        final_state = research_graph.invoke(initial_state)
        return final_state.get("final_report", {})

    def stream(self, topic: str):
        """
        Run the graph and yield SSE-compatible event dicts as each node completes.
        Yields dicts — caller is responsible for JSON serialisation.
        """
        from research.graph.graph_builder import research_graph

        initial_state = self._build_initial_state(topic)

        for event in research_graph.stream(initial_state, stream_mode="updates"):
            # event is {node_name: state_patch}
            for node_name, patch in event.items():
                node_statuses = patch.get("node_statuses", {})
                graph_events = patch.get("graph_events", [])

                yield {
                    "type": "node_update",
                    "node": node_name,
                    "node_statuses": node_statuses,
                    "graph_events": graph_events,
                }

                # If synthesizer just completed, emit the final result too
                if node_name == "synthesizer" and patch.get("final_report"):
                    yield {
                        "type": "complete",
                        **patch["final_report"],
                    }
