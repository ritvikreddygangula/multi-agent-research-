"""
Base agent class for all research agents.
"""
from abc import ABC, abstractmethod
from openai import OpenAI
from django.conf import settings
import httpx


class BaseAgent(ABC):
    """Base class for all research agents."""
    
    def __init__(self):
        """Initialize the agent with OpenAI client."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        # Initialize OpenAI client for version 1.3.0
        # Workaround for httpx compatibility issue with proxies parameter
        # Create httpx client without proxies to avoid TypeError
        try:
            # Try to create httpx client without proxies parameter
            http_client = httpx.Client(timeout=60.0)
            self.client = OpenAI(api_key=api_key, http_client=http_client)
        except (TypeError, Exception) as e:
            # Fallback: use environment variable approach
            import os
            original_key = os.environ.get('OPENAI_API_KEY')
            os.environ['OPENAI_API_KEY'] = api_key
            try:
                # Create http client without proxies
                http_client = httpx.Client(timeout=60.0)
                self.client = OpenAI(http_client=http_client)
            finally:
                if original_key:
                    os.environ['OPENAI_API_KEY'] = original_key
                elif 'OPENAI_API_KEY' in os.environ:
                    del os.environ['OPENAI_API_KEY']
    
    @abstractmethod
    def execute(self, topic: str, context: dict = None) -> dict:
        """
        Execute the agent's task.
        
        Args:
            topic: The research topic
            context: Optional context from other agents
            
        Returns:
            Dictionary with agent's results
        """
        pass
    
    def _call_openai(self, messages: list, model: str = "gpt-4", temperature: float = 0.7) -> str:
        """
        Make a call to OpenAI API.
        
        Args:
            messages: List of message dictionaries
            model: Model to use (default: gpt-4)
            temperature: Temperature setting (default: 0.7)
            
        Returns:
            Response content from OpenAI
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
