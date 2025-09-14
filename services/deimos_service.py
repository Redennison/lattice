"""Deimos/Martian routing service for optimized LLM selection."""

from typing import Dict, Any, Optional

class DeimosService:
    """Service for routing LLM tasks using Deimos/Martian.
    
    This service routes different task types to appropriate LLM models
    based on complexity and requirements to optimize costs.
    """
    
    def __init__(self):
        """Initialize Deimos router with task mappings."""
        # Define task to model mappings
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
        # Get model based on task type and complexity
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
