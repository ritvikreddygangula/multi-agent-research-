"""
Synthesizer Agent - Produces clean, concise, well-aligned final answer.
"""
from .base_agent import BaseAgent
import json


class SynthesizerAgent(BaseAgent):
    """Agent responsible for synthesizing final research output."""
    
    def execute(self, topic: str, context: dict = None) -> dict:
        """
        Synthesize all research into a final structured answer.
        
        Args:
            topic: The research topic
            context: Context from planner and research agents
            
        Returns:
            Dictionary with final synthesized research
        """
        # Build context summary
        context_summary = f"Research Topic: {topic}\n\n"
        
        if context:
            if 'planner' in context:
                planner_data = context['planner']
                if 'plan' in planner_data:
                    plan = planner_data['plan']
                    context_summary += f"Research Plan:\n"
                    if 'understanding' in plan:
                        context_summary += f"- Understanding: {plan['understanding']}\n"
                    if 'sub_questions' in plan:
                        context_summary += f"- Key Questions: {', '.join(plan['sub_questions'])}\n"
                    context_summary += "\n"
            
            if 'research' in context:
                research_data = context['research']
                if 'findings' in research_data:
                    findings = research_data['findings']
                    context_summary += f"Research Findings:\n"
                    if 'core_facts' in findings:
                        context_summary += f"- Core Facts: {', '.join(findings['core_facts'][:3])}\n"
                    if 'important_findings' in findings:
                        context_summary += f"- Key Findings: {', '.join(findings['important_findings'][:3])}\n"
        
        system_prompt = """You are a research synthesis expert. Your role is to take research findings from multiple sources and create a clean, concise, well-structured final answer.

Create a comprehensive but readable synthesis that includes:
1. Overview - Brief summary of the topic
2. Key Concepts - Important concepts explained clearly
3. Important Findings - Most significant discoveries/insights
4. Summary - Concise conclusion

Be crisp, structured, and readable. Avoid verbosity. Focus on clarity and insight. Return your response as a JSON object with the following structure:
{
    "overview": "Brief 2-3 sentence overview",
    "key_concepts": ["concept 1 with brief explanation", "concept 2 with brief explanation", "concept 3 with brief explanation"],
    "important_findings": ["finding 1", "finding 2", "finding 3"],
    "summary": "2-3 sentence summary"
}

Keep key_concepts and important_findings to 3-5 items each. Be concise but informative."""

        user_prompt = f"Synthesize the following research into a final structured answer:\n\n{context_summary}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = self._call_openai(messages, temperature=0.5)
        
        try:
            # Try to parse JSON response
            synthesis = json.loads(response)
        except json.JSONDecodeError:
            # If not JSON, create a structured response
            synthesis = {
                "overview": response[:200],
                "key_concepts": [response[:150]],
                "important_findings": [response[:150]],
                "summary": response[:200]
            }
        
        return {
            "agent": "SynthesizerAgent",
            "synthesis": synthesis,
            "raw_response": response
        }
