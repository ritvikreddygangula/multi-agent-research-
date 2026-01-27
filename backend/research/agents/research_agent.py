"""
Research Agent - Performs deep factual and conceptual research.
"""
from .base_agent import BaseAgent
import json


class ResearchAgent(BaseAgent):
    """Agent responsible for performing deep research."""
    
    def execute(self, topic: str, context: dict = None) -> dict:
        """
        Perform deep research on the topic.
        
        Args:
            topic: The research topic
            context: Optional context from planner agent
            
        Returns:
            Dictionary with research findings
        """
        # Use planner context if available
        research_focus = topic
        if context and 'plan' in context:
            plan = context['plan']
            if 'sub_questions' in plan:
                research_focus = f"{topic}\n\nKey questions to address: {', '.join(plan['sub_questions'][:3])}"
        
        system_prompt = """You are a research expert specializing in deep factual and conceptual analysis. Your role is to conduct thorough research on topics and provide well-structured findings.

Your research should cover:
1. Core facts and definitions
2. Important concepts and theories
3. Key findings and insights
4. Relevant examples and applications

Be thorough but concise. Focus on accuracy and clarity. Return your response as a JSON object with the following structure:
{
    "core_facts": ["fact 1", "fact 2", "fact 3"],
    "key_concepts": ["concept 1", "concept 2", "concept 3"],
    "important_findings": ["finding 1", "finding 2", "finding 3"],
    "examples": ["example 1", "example 2"]
}

Keep each array to 3-5 items maximum. Be specific and factual."""

        user_prompt = f"Conduct deep research on: {research_focus}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_openai(messages, temperature=0.6)
        
        try:
            # Try to parse JSON response
            findings = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, create a structured response
            findings = {
                "core_facts": [response[:150]],
                "key_concepts": [response[:150]],
                "important_findings": [response[:150]],
                "examples": [response[:150]]
            }
        
        return {
            "agent": "ResearchAgent",
            "findings": findings,
            "raw_response": response
        }
