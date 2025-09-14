"""Deimos Router configuration for optimal LLM selection."""

import os
from typing import Dict, Any, Optional
import openai

# Import deimos_router components (assuming it's installed)
try:
    from deimos_router import Router, register_router, chat
    from deimos_router.rules import TaskRule, MessageLengthRule, ConversationContextRule, CodeRule
    DEIMOS_AVAILABLE = True
except ImportError:
    DEIMOS_AVAILABLE = False
    print("Warning: deimos_router package not installed. Using fallback routing.")

class DeimosRouterService:
    """Service for intelligent LLM routing using Deimos Router."""
    
    def __init__(self):
        """Initialize Deimos Router with rules for different task types."""
        self.router_registered = False
        self.router_name = "lattice_router"
        
        if DEIMOS_AVAILABLE:
            self._setup_router()
        
        # Fallback model mappings if Deimos isn't available
        self.fallback_models = {
            "parse_bug_report": "command-r-plus",
            "locate_change_target": "gpt-4o",
            "generate_patch": "gpt-4o", 
            "pr_description": "gpt-4o-mini",
            "code_analysis": "gpt-4o",
            "simple_task": "gpt-4o-mini"
        }
    
    def _setup_router(self):
        """Set up the Deimos Router with rules."""
        try:
            # Task-based routing rule for explicit task types
            task_rule = TaskRule(
                name="lattice_task_router",
                triggers={
                    # PR editing tasks - use more powerful models
                    "locate_change_target": "openai/gpt-4o",
                    "generate_patch": "openai/gpt-4o",
                    "code_fix": "openai/gpt-4o",
                    "pr_edit": "openai/gpt-4o",
                    
                    # Ticket creation tasks - use Cohere models
                    "parse_bug_report": "cohere/command-r-plus",
                    "ticket_creation": "cohere/command-r-plus",
                    "bug_analysis": "cohere/command-r-plus",
                    
                    # General tasks
                    "pr_description": "openai/gpt-4o-mini",
                    "summarize": "openai/gpt-4o-mini",
                    "simple": "openai/gpt-4o-mini"
                }
            )
            
            # Code detection rule - route code-related content to GPT-4
            code_rule = CodeRule(
                name="code_detector",
                code="openai/gpt-4o",  # Use GPT-4 for code
                not_code="openai/gpt-4o-mini"  # Use smaller model for non-code
            )
            
            # Message length rule for optimizing based on input size
            length_rule = MessageLengthRule(
                name="length_router",
                short_threshold=500,
                long_threshold=3000,
                short_model="openai/gpt-4o-mini",  # Short messages
                medium_model="openai/gpt-4o",      # Medium messages
                long_model="openai/gpt-4o"         # Long messages (code context)
            )
            
            # Context depth rule for conversation history
            context_rule = ConversationContextRule(
                name="context_router",
                new_threshold=2,
                deep_threshold=5,
                new_model="openai/gpt-4o-mini",     # New conversations
                developing_model="openai/gpt-4o",    # Developing conversations
                deep_model="openai/gpt-4o"          # Deep conversations
            )
            
            # Create the main router with all rules
            # Rules are evaluated in order, so put task rule first for explicit routing
            router = Router(
                name=self.router_name,
                rules=[
                    task_rule,      # First: Check for explicit task
                    code_rule,      # Second: Detect if it's code
                    length_rule,    # Third: Route by message length
                    context_rule    # Fourth: Route by conversation depth
                ],
                default="openai/gpt-4o-mini"  # Fallback model
            )
            
            # Register the router
            register_router(router)
            self.router_registered = True
            print(f"✅ Deimos Router '{self.router_name}' registered successfully")
            
        except Exception as e:
            print(f"⚠️ Failed to setup Deimos Router: {e}")
            self.router_registered = False
    
    def route_request(self, task_type: str, messages: list, **kwargs) -> Dict[str, Any]:
        """Route a request through Deimos Router.
        
        Args:
            task_type: Type of task (e.g., 'locate_change_target', 'generate_patch')
            messages: List of messages in OpenAI format
            **kwargs: Additional parameters for the request
            
        Returns:
            Response from the routed model
        """
        if not DEIMOS_AVAILABLE or not self.router_registered:
            # Fallback to direct model selection
            model = self.fallback_models.get(task_type, "gpt-4o-mini")
            print(f"📍 Using fallback model for {task_type}: {model}")
            return self._fallback_request(model, messages, **kwargs)
        
        try:
            # Use Deimos Router for intelligent routing
            print(f"🚀 Routing {task_type} through Deimos Router")
            
            response = chat.completions.create(
                model=f"deimos/{self.router_name}",
                messages=messages,
                task=task_type,  # Pass task type for TaskRule
                explain=True,    # Get routing explanation
                **kwargs
            )
            
            # Log routing decision
            if hasattr(response, '_deimos_metadata'):
                metadata = response._deimos_metadata
                print(f"✨ Deimos routed to: {metadata.get('selected_model')}")
                if 'explain' in metadata:
                    for entry in metadata['explain']:
                        print(f"   Rule: {entry['rule_name']} → {entry['decision']}")
            
            return response
            
        except Exception as e:
            print(f"⚠️ Deimos routing failed: {e}, using fallback")
            model = self.fallback_models.get(task_type, "gpt-4o-mini")
            return self._fallback_request(model, messages, **kwargs)
    
    def _fallback_request(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """Fallback to direct OpenAI/Cohere API call.
        
        Args:
            model: Model name to use
            messages: List of messages
            **kwargs: Additional parameters
            
        Returns:
            API response
        """
        # Map model names to API providers
        if model.startswith("command"):
            # Use Cohere (would need cohere client setup)
            return {"model": model, "choices": [{"message": {"content": "Cohere fallback"}}]}
        else:
            # Use OpenAI
            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url="https://api.openai.com/v1"
            )
            return client.chat.completions.create(
                model=model.replace("openai/", ""),
                messages=messages,
                **kwargs
            )
    
    def get_model_for_task(self, task_type: str, complexity: str = "medium") -> str:
        """Get recommended model for a task type.
        
        Args:
            task_type: Type of task
            complexity: Task complexity (low, medium, high)
            
        Returns:
            Recommended model name
        """
        # PR editing tasks should use GPT-4
        if task_type in ["locate_change_target", "generate_patch", "code_fix", "pr_edit"]:
            return "openai/gpt-4o"
        
        # Ticket creation should use Cohere
        if task_type in ["parse_bug_report", "ticket_creation", "bug_analysis"]:
            return "cohere/command-r-plus"
        
        # Simple tasks can use smaller models
        if task_type in ["summarize", "pr_description"]:
            return "openai/gpt-4o-mini"
        
        # Default based on complexity
        if complexity == "high":
            return "openai/gpt-4o"
        elif complexity == "low":
            return "openai/gpt-4o-mini"
        else:
            return "openai/gpt-4o"
    
    def explain_routing(self, task_type: str, message_length: int = 0) -> str:
        """Explain how a task would be routed.
        
        Args:
            task_type: Type of task
            message_length: Length of message in characters
            
        Returns:
            Explanation of routing decision
        """
        explanations = []
        
        # Task-based routing
        if task_type in ["locate_change_target", "generate_patch", "pr_edit"]:
            explanations.append(f"✅ Task '{task_type}' → GPT-4 (PR editing requires precision)")
        elif task_type in ["parse_bug_report", "ticket_creation"]:
            explanations.append(f"✅ Task '{task_type}' → Cohere Command-R+ (optimized for ticket creation)")
        
        # Length-based routing
        if message_length > 0:
            if message_length < 500:
                explanations.append(f"📏 Short message ({message_length} chars) → GPT-4o-mini")
            elif message_length < 3000:
                explanations.append(f"📏 Medium message ({message_length} chars) → GPT-4")
            else:
                explanations.append(f"📏 Long message ({message_length} chars) → GPT-4")
        
        return "\n".join(explanations) if explanations else "🤖 Using default routing"


# Singleton instance
_router_service = None

def get_router_service() -> DeimosRouterService:
    """Get or create the singleton DeimosRouterService instance."""
    global _router_service
    if _router_service is None:
        _router_service = DeimosRouterService()
    return _router_service
