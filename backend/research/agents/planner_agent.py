"""
Planner Agent - Understands the topic and defines research structure.
"""
from .base_agent import BaseAgent
import json


class PlannerAgent(BaseAgent):
    """Agent responsible for planning research structure."""
    
    def execute(self, topic: str, context: dict = None) -> dict:
        """
        Analyze the topic and create a research plan.
        
        Args:
            topic: The research topic
            context: Optional context (not used for planner)
            
        Returns:
            Dictionary with research plan and sub-questions
        """
        system_prompt = """You are a research planning expert. Your role is to analyze research topics and create a structured research plan.

Your output should be:
1. A clear understanding of what needs to be researched
2. Key sub-questions that need to be answered
3. Important aspects to investigate

Be concise and focused. Return your response as a JSON object with the following structure:
{
    "understanding": "Brief explanation of what this research topic entails",
    "sub_questions": ["question 1", "question 2", "question 3"],
    "key_aspects": ["aspect 1", "aspect 2", "aspect 3"]
}

Keep sub_questions to 3-5 items maximum. Keep key_aspects to 3-5 items maximum."""

        user_prompt = f"Create a research plan for the following topic: {topic}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_openai(messages, temperature=0.5)
        
        try:
            # Try to parse JSON response
            plan = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, create a structured response
            plan = {
                "understanding": response[:200],
                "sub_questions": [response],
                "key_aspects": [response]
            }
        
        return {
            "agent": "PlannerAgent",
            "plan": plan,
            "raw_response": response
        }
