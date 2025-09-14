"""Deimos/Martian routing service for optimized LLM selection."""

from typing import Dict, Any, Optional, List
import openai
import os

# Try to import the new router service
try:
    from .deimos_router import get_router_service, DeimosRouterService
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    print("Warning: DeimosRouterService not available, using basic routing")

class DeimosService:
    """Service for routing LLM tasks using Deimos/Martian.
    
    This service routes different task types to appropriate LLM models
    based on complexity and requirements to optimize costs.
    """
    
    def __init__(self):
        """Initialize Deimos router with task mappings."""
        # Try to use the advanced router if available
        self.router_service = get_router_service() if ROUTER_AVAILABLE else None
        
        # Define task to model mappings (fallback)
        self.task_model_map = {
            "parse_bug_report": {
                "low": "command-r",
                "medium": "command-r",
                "high": "command-r-plus"
            },
            "generate_code_fix": {
                "low": "command-r",
                "medium": "command-r-plus",
                "high": "command-r-plus"
            },
            "summarize_pr": {
                "low": "command-r",
                "medium": "command-r",
                "high": "command-r"
            }
        }
    
    def route_task(self, task_type: str, complexity: str = "medium") -> str:
        """Route task to appropriate model.
        
        Args:
            task_type: Type of task (parse_bug_report, generate_code_fix, etc.)
            complexity: Task complexity (low, medium, high)
            
        Returns:
            Selected model name
        """
        # Use advanced router if available
        if self.router_service:
            return self.router_service.get_model_for_task(task_type, complexity)
        
        # Fallback to basic routing
        if task_type in self.task_model_map:
            model_map = self.task_model_map[task_type]
            return model_map.get(complexity, model_map["medium"])
        
        # Default routing for unknown tasks
        if task_type == "parse_bug_report":
            return "command-r"
        elif task_type == "generate_code_fix":
            return "command-r-plus"
        elif task_type == "summarize_pr":
            return "command-r"
        else:
            # Default to medium model
            return "command-r"
    
    def route_pr_edit_request(self, messages: List[Dict[str, str]], task: str = "pr_edit") -> Any:
        """Route PR editing request through Deimos Router.
        
        Args:
            messages: Conversation messages in OpenAI format
            task: Task type for routing
            
        Returns:
            Model response
        """
        if self.router_service:
            print(f"🚀 Routing PR edit task '{task}' through Deimos Router")
            return self.router_service.route_request(
                task_type=task,
                messages=messages,
                temperature=0.1,  # Low temperature for precise code edits
                max_tokens=8000   # Allow for longer responses
            )
        else:
            # Fallback to direct OpenAI call
            print(f"📍 Using fallback OpenAI for PR edit task '{task}'")
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1"
            )
            return client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=8000
            )
    
    def get_model_for_conversation_length(self, message_count: int) -> str:
        """Select model based on conversation length.
        
        Args:
            message_count: Number of messages in conversation
            
        Returns:
            Appropriate model name
        """
        if message_count < 10:
            return "command-r"  # Light model for short conversations
        elif message_count < 30:
            return "command-r"  # Medium model
        else:
            return "command-r-plus"  # Heavy model for long conversations
