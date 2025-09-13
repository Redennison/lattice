"""
Deimos Router Service - Cost-effective LLM routing for Lattice
Follows the official Deimos Router documentation patterns
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from deimos_router import Router, register_router, chat, clear_routers
from deimos_router.rules import TaskRule, CodeRule, MessageLengthRule

@dataclass
class RoutingResponse:
    """Response from Deimos routing"""
    selected_model: str
    response: str
    routing_metadata: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = None

# Router name constant
LATTICE_ROUTER_NAME = "lattice-router"

def setup_lattice_router():
    """Set up and register the Lattice router with intelligent routing rules"""
    
    # Clear any existing routers
    clear_routers()
    
    # Rule 1: Task-based routing with diverse model selection
    task_rule = TaskRule(
        name="task-router",
        triggers={
            'ticket_analysis': 'anthropic/claude-3-5-sonnet-latest',
            'coding': 'anthropic/claude-3-5-sonnet-latest',
            'debugging': 'openai/gpt-4o',
            'architecture': 'anthropic/claude-3-opus-latest',
            'summarization': 'anthropic/claude-3-haiku',
            'classification': 'google/gemini-1.5-flash',
            'extraction': 'mistral/mistral-small-latest',
            'translation': 'google/gemini-1.5-flash',
            'simple_query': 'openai/gpt-4o-mini',
            'formatting': 'meta-llama/llama-3.1-8b-instruct',
            'basic_qa': 'mistral/mistral-tiny',
            'complex_analysis': 'openai/o1-preview',
            'math': 'openai/o1-mini',
            'creative': 'anthropic/claude-3-5-sonnet-latest',
        }
    )
    
    # Rule 2: Code detection with chained task routing for code
    code_task_rule = TaskRule(
        name="code-type-router",
        triggers={
            'python': 'anthropic/claude-3-5-sonnet-latest',
            'javascript': 'openai/gpt-4o',
            'rust': 'anthropic/claude-3-5-sonnet-latest',
            'sql': 'openai/gpt-4o',
            'react': 'openai/gpt-4o',
            'backend': 'anthropic/claude-3-5-sonnet-latest',
            'devops': 'openai/gpt-4o',
            'default': 'anthropic/claude-3-5-sonnet-latest'
        }
    )
    
    code_rule = CodeRule(
        name="code-detector",
        code=code_task_rule,  # Chain to code-specific task routing
        not_code=task_rule    # Fall back to general task routing if no code
    )
    
    length_rule = MessageLengthRule(
        name="complexity-router",
        short_threshold=300,
        long_threshold=1500,
        short_model='mistral/mistral-tiny',
        medium_model='anthropic/claude-3-haiku',
        long_model='anthropic/claude-3-5-sonnet-latest'
    )
    
    cost_priority_rule = TaskRule(
        name="cost-priority-router",
        triggers={
            'ultra_low_cost': 'meta-llama/llama-3.1-8b-instruct',
            'low_cost': 'mistral/mistral-small-latest',
            'balanced': 'anthropic/claude-3-haiku',
            'high_quality': 'anthropic/claude-3-5-sonnet-latest',
            'max_quality': 'openai/o1-preview'
        }
    )
    
    lattice_router = Router(
        name=LATTICE_ROUTER_NAME,
        rules=[
            code_rule,           
            cost_priority_rule, 
            task_rule,          
            length_rule         
        ],
        default="anthropic/claude-3-haiku"  
    )
    
    register_router(lattice_router)
    
    return lattice_router

# Initialize router on module import
_router = setup_lattice_router()

async def route_request(
    prompt: str,
    task: str = "ticket_analysis",
    context: Optional[str] = None,
    max_tokens: Optional[int] = 2500,
    temperature: Optional[float] = 0.2,
    explain: bool = False
) -> RoutingResponse:
    """
    Route a request using the Lattice Deimos Router
    
    Args:
        prompt: The prompt to send to the LLM
        task: Task type for routing (ticket_analysis, coding, summarization, etc.)
        context: Additional context for the request
        max_tokens: Maximum tokens for the response
        temperature: Temperature for the LLM
        explain: Whether to include routing explanation
        
    Returns:
        RoutingResponse with the LLM response and metadata
    """
    
    # Build the full prompt
    full_prompt = prompt
    if context:
        full_prompt = f"Context: {context}\n\nTask: {prompt}"
    
    # Prepare the messages
    messages = [
        {"role": "user", "content": full_prompt}
    ]
    
    # Build request parameters using documented format
    request_params = {
        "model": f"deimos/{LATTICE_ROUTER_NAME}",  # Use deimos/ prefix as documented
        "messages": messages,
        "task": task,  # Custom parameter for TaskRule
        "explain": explain,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        # Make the request using Deimos Router chat API
        response = chat.completions.create(**request_params)
        
        # Extract routing metadata if available
        routing_metadata = {}
        estimated_cost = None
        selected_model = response.model if hasattr(response, 'model') else "unknown"
        
        # Check for Deimos metadata
        if hasattr(response, '_deimos_metadata'):
            routing_metadata = response._deimos_metadata
            selected_model = routing_metadata.get('selected_model', selected_model)
            estimated_cost = routing_metadata.get('cost_estimate')
        
        # Extract response content
        response_content = ""
        if hasattr(response, 'choices') and response.choices:
            response_content = response.choices[0].message.content
        
        return RoutingResponse(
            selected_model=selected_model,
            response=response_content,
            routing_metadata=routing_metadata,
            estimated_cost=estimated_cost
        )
        
    except Exception as e:
        # Fallback to direct model call if routing fails
        fallback_response = chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            max_tokens=max_tokens or 2000,
            temperature=temperature or 0.3
        )
        
        response_content = ""
        if hasattr(fallback_response, 'choices') and fallback_response.choices:
            response_content = fallback_response.choices[0].message.content
        
        return RoutingResponse(
            selected_model="openai/gpt-4o-mini",
            response=response_content,
            routing_metadata={"error": str(e), "fallback": True}
        )
