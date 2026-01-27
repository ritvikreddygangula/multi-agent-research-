"""
Research service for orchestrating multi-agent research.
"""
from research.agents import PlannerAgent, ResearchAgent, SynthesizerAgent
import concurrent.futures


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
