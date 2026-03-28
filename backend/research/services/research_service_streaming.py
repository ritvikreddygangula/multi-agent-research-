"""
Streaming research service that yields progress updates.
"""
from research.agents import PlannerAgent, ResearchAgent, SynthesizerAgent
import json
import time
import threading


class StreamingResearchService:
    """Service for coordinating multi-agent research with streaming updates."""
    
    def __init__(self):
        """Initialize research service with agents."""
        self.planner = PlannerAgent()
        self.research = ResearchAgent()
        self.synthesizer = SynthesizerAgent()
    
    def _execute_with_progress(self, agent_func, topic, context, progress_start, progress_end, agent_name, messages):
        """
        Execute an agent function while yielding progress updates.
        
        Args:
            agent_func: The agent function to execute
            topic: Research topic
            context: Context for the agent
            progress_start: Starting progress percentage
            progress_end: Ending progress percentage
            agent_name: Name of the agent
            messages: List of progress messages to show
            
        Yields:
            Progress updates during execution
        """
        import time
        
        # Calculate number of progress steps
        num_steps = len(messages)
        progress_range = progress_end - progress_start
        progress_per_step = progress_range / num_steps if num_steps > 0 else 0
        
        # Start agent execution in a thread
        result_container = {'result': None, 'error': None, 'done': False}
        
        def execute_agent():
            try:
                if context:
                    result_container['result'] = agent_func(topic, context=context)
                else:
                    result_container['result'] = agent_func(topic)
            except Exception as e:
                result_container['error'] = e
            finally:
                result_container['done'] = True
        
        # Start execution thread
        thread = threading.Thread(target=execute_agent)
        thread.start()
        
        # Yield progress updates while agent is working
        current_progress = progress_start
        for i, message in enumerate(messages):
            # Wait a bit before next update (simulate work)
            time.sleep(0.8)
            
            current_progress = min(progress_start + (i + 1) * progress_per_step, progress_end - 1)
            
            yield {
                "type": "progress",
                "agent": agent_name,
                "status": "working",
                "message": message,
                "progress": int(current_progress)
            }
        
        # Wait for agent to complete
        thread.join(timeout=120)  # 2 minute timeout
        
        if result_container['error']:
            raise result_container['error']
        
        return result_container['result']
    
    def conduct_research_streaming(self, topic: str):
        """
        Conduct multi-agent research on a topic with streaming updates.
        
        Yields progress updates as each agent completes.
        
        Args:
            topic: The research topic
            
        Yields:
            Dictionary with progress updates and partial results
        """
        try:
            # Step 1: Planner creates research plan (0-30%)
            yield {
                "type": "progress",
                "agent": "planner",
                "status": "working",
                "message": "Initializing planner agent...",
                "progress": 5
            }
            time.sleep(0.5)
            
            yield {
                "type": "progress",
                "agent": "planner",
                "status": "working",
                "message": "Analyzing topic structure...",
                "progress": 10
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "planner",
                "status": "working",
                "message": "Identifying key research areas...",
                "progress": 15
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "planner",
                "status": "working",
                "message": "Creating research plan and sub-questions...",
                "progress": 20
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "planner",
                "status": "working",
                "message": "Finalizing research strategy...",
                "progress": 25
            }
            
            # Execute planner
            planner_result = self.planner.execute(topic)
            
            yield {
                "type": "progress",
                "agent": "planner",
                "status": "completed",
                "message": "Research plan created successfully",
                "progress": 30,
                "data": {
                    "plan": planner_result.get('plan', {})
                }
            }
            time.sleep(0.5)
            
            # Step 2: Research agent performs deep research (30-65%)
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Initializing research agent...",
                "progress": 32
            }
            time.sleep(0.5)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Reviewing research plan...",
                "progress": 35
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Gathering factual information...",
                "progress": 40
            }
            time.sleep(1.0)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Analyzing key concepts...",
                "progress": 45
            }
            time.sleep(1.0)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Collecting detailed findings...",
                "progress": 50
            }
            time.sleep(1.0)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Validating research data...",
                "progress": 55
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "working",
                "message": "Organizing research findings...",
                "progress": 60
            }
            
            research_context = {
                'plan': planner_result.get('plan', {})
            }
            research_result = self.research.execute(topic, context=research_context)
            
            yield {
                "type": "progress",
                "agent": "research",
                "status": "completed",
                "message": "Research findings gathered",
                "progress": 65,
                "data": {
                    "findings": research_result.get('findings', {})
                }
            }
            time.sleep(0.5)
            
            # Step 3: Synthesizer creates final output (65-95%)
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "working",
                "message": "Initializing synthesizer agent...",
                "progress": 67
            }
            time.sleep(0.5)
            
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "working",
                "message": "Reviewing all research data...",
                "progress": 70
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "working",
                "message": "Synthesizing key insights...",
                "progress": 75
            }
            time.sleep(1.0)
            
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "working",
                "message": "Structuring final report...",
                "progress": 80
            }
            time.sleep(1.0)
            
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "working",
                "message": "Compiling overview and summary...",
                "progress": 85
            }
            time.sleep(0.8)
            
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "working",
                "message": "Finalizing research report...",
                "progress": 90
            }
            
            synthesis_context = {
                'planner': planner_result,
                'research': research_result
            }
            synthesis_result = self.synthesizer.execute(topic, context=synthesis_context)
            
            yield {
                "type": "progress",
                "agent": "synthesizer",
                "status": "completed",
                "message": "Synthesis completed",
                "progress": 95,
                "data": {
                    "overview": synthesis_result.get('synthesis', {}).get('overview', '')[:200] if synthesis_result.get('synthesis', {}).get('overview') else ''
                }
            }
            time.sleep(0.5)
            
            # Final result
            yield {
                "type": "progress",
                "agent": "system",
                "status": "working",
                "message": "Preparing final results...",
                "progress": 98
            }
            time.sleep(0.3)
            
            tokens_used = (
                self.planner.tokens_used
                + self.research.tokens_used
                + self.synthesizer.tokens_used
            )

            final_result = {
                "type": "complete",
                "topic": topic,
                "overview": synthesis_result.get('synthesis', {}).get('overview', ''),
                "key_concepts": synthesis_result.get('synthesis', {}).get('key_concepts', []),
                "important_findings": synthesis_result.get('synthesis', {}).get('important_findings', []),
                "summary": synthesis_result.get('synthesis', {}).get('summary', ''),
                "progress": 100,
                "tokens_used": tokens_used,
            }

            yield final_result
            
        except Exception as e:
            yield {
                "type": "error",
                "message": f"Research failed: {str(e)}",
                "error": str(e)
            }
