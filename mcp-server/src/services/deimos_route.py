"""
Deimos Router Service - Cost-effective LLM routing for Lattice
Uses the official Deimos Router library for intelligent model selection
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import json

from deimos_router import Router, register_router, chat, clear_routers
from deimos_router.rules import TaskRule, CodeRule, MessageLengthRule

@dataclass
class RoutingResponse:
    """Response from Deimos routing"""
    selected_model: str
    response: str
    routing_metadata: Optional[Dict[str, Any]] = None
    estimated_cost: Optional[float] = None

class LatticeDeimosRouter:
    """Lattice-specific Deimos Router configuration"""
    
    def __init__(self):
        self._router_registered = False
        self._setup_router()
    
    def _setup_router(self):
        """Set up the Lattice router with intelligent routing rules"""
        
        # Clear any existing routers
        clear_routers()
        
        # Rule 1: Task-based routing with diverse model selection
        # Using different providers for cost optimization
        task_rule = TaskRule(
            name="task-router",
            rules={
                # Critical tasks - use best models regardless of cost
                'ticket_analysis': 'anthropic/claude-3-5-sonnet-latest',  # Best for structured analysis
                'coding': 'anthropic/claude-3-5-sonnet-latest',          # Excellent at code generation
                'debugging': 'openai/gpt-4o',                            # Strong debugging capabilities
                'architecture': 'anthropic/claude-3-opus-latest',        # Best for system design
                
                # Medium complexity tasks - balance cost and quality
                'summarization': 'anthropic/claude-3-haiku',             # Fast, cheap, good summaries
                'classification': 'google/gemini-1.5-flash',             # Very fast classification
                'extraction': 'mistral/mistral-small-latest',            # Good for data extraction
                'translation': 'google/gemini-1.5-flash',                # Good multilingual support
                
                # Simple tasks - optimize for cost
                'simple_query': 'openai/gpt-4o-mini',                    # Cheap and reliable
                'formatting': 'meta-llama/llama-3.1-8b-instruct',        # Open source, very cheap
                'basic_qa': 'mistral/mistral-tiny',                      # Extremely cost-effective
                
                # Complex analysis - use specialized models
                'complex_analysis': 'openai/o1-preview',                 # Best reasoning model
                'math': 'openai/o1-mini',                                # Optimized for math/logic
                'creative': 'anthropic/claude-3-5-sonnet-latest',        # Creative writing
            }
        )
        
        # Rule 2: Code detection with provider-specific strengths
        # Different models excel at different programming tasks
        code_rule = CodeRule(
            name="code-detector",
            code=TaskRule(
                name="code-type-router",
                rules={
                    # Route based on detected programming language/framework
                    'python': 'anthropic/claude-3-5-sonnet-latest',      # Excellent Python support
                    'javascript': 'openai/gpt-4o',                       # Strong JS/TS support
                    'rust': 'anthropic/claude-3-5-sonnet-latest',        # Good at systems programming
                    'sql': 'openai/gpt-4o',                              # Strong SQL generation
                    'react': 'openai/gpt-4o',                            # React/frontend expertise
                    'backend': 'anthropic/claude-3-5-sonnet-latest',     # Backend architecture
                    'devops': 'openai/gpt-4o',                           # DevOps/infrastructure
                    'default': 'anthropic/claude-3-5-sonnet-latest'      # General code tasks
                }
            ),
            not_code=task_rule  # Fall back to task routing if no code
        )
        
        # Rule 3: Complexity-based routing
        # Analyze message complexity beyond just length
        complexity_rule = MessageLengthRule(
            name="complexity-router",
            short_threshold=300,          # < 300 chars = simple
            long_threshold=1500,          # > 1500 chars = complex
            
            # Simple messages - use cheapest effective models
            short_model='mistral/mistral-tiny',           # $0.00025/1K tokens
            
            # Medium complexity - balance cost and capability  
            medium_model='anthropic/claude-3-haiku',      # $0.00025/$0.00125 per 1K tokens
            
            # Complex messages - use powerful models
            long_model='anthropic/claude-3-5-sonnet-latest'  # Best overall performance
        )
        
        # Rule 4: Cost priority override
        # Allow dynamic cost optimization based on user preferences
        cost_priority_rule = TaskRule(
            name="cost-priority-router",
            rules={
                # Ultra-low cost mode (for high volume, low priority tasks)
                'ultra_low_cost': 'meta-llama/llama-3.1-8b-instruct',
                
                # Low cost mode (good balance)
                'low_cost': 'mistral/mistral-small-latest',
                
                # Balanced mode (default)
                'balanced': 'anthropic/claude-3-haiku',
                
                # High quality mode (when accuracy is critical)
                'high_quality': 'anthropic/claude-3-5-sonnet-latest',
                
                # Maximum quality (cost no object)
                'max_quality': 'openai/o1-preview'
            }
        )
        
        # Create router with rules evaluated in priority order
        lattice_router = Router(
            name="lattice-router",
            rules=[
                code_rule,           # First: Check for code (most specific)
                cost_priority_rule,  # Second: Check for explicit cost preference
                task_rule,          # Third: Route by task type
                complexity_rule     # Fourth: Fall back to complexity analysis
            ],
            default_model="anthropic/claude-3-haiku"  # Safe, cost-effective default
        )
        
        # Register the router
        register_router(lattice_router)
        self._router_registered = True
    
    async def route_request(
        self,
        prompt: str,
        task: str = "analysis",
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        explain: bool = False
    ) -> RoutingResponse:
        """
        Route a request using Deimos Router
        
        Args:
            prompt: The prompt to send to the LLM
            task: Task type for routing (analysis, coding, summarization, etc.)
            context: Additional context for the request
            max_tokens: Maximum tokens for the response
            temperature: Temperature for the LLM
            explain: Whether to include routing explanation
            
        Returns:
            RoutingResponse with the LLM response and metadata
        """
        
        if not self._router_registered:
            self._setup_router()
        
        # Build the full prompt
        full_prompt = prompt
        if context:
            full_prompt = f"Context: {context}\n\nTask: {prompt}"
        
        # Prepare the messages
        messages = [
            {"role": "user", "content": full_prompt}
        ]
        
        # Build request parameters
        request_params = {
            "model": "deimos/lattice-router",
            "messages": messages,
            "task": task,
            "explain": explain
        }
        
        # Add optional parameters
        if max_tokens:
            request_params["max_tokens"] = max_tokens
        if temperature is not None:
            request_params["temperature"] = temperature
        
        try:
            # Make the request using Deimos Router
            response = chat.completions.create(**request_params)
            
            # Extract routing metadata if available
            routing_metadata = None
            estimated_cost = None
            selected_model = "unknown"
            
            if hasattr(response, '_deimos_metadata'):
                routing_metadata = response._deimos_metadata
                selected_model = routing_metadata.get('selected_model', 'unknown')
                
                # Extract cost information if available
                if 'cost_estimate' in routing_metadata:
                    estimated_cost = routing_metadata['cost_estimate']
            
            return RoutingResponse(
                selected_model=selected_model,
                response=response.choices[0].message.content,
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
            
            return RoutingResponse(
                selected_model="openai/gpt-4o-mini",
                response=fallback_response.choices[0].message.content,
                routing_metadata={"error": str(e), "fallback": True}
            )

# Global router instance
_router_instance = None

def get_router() -> LatticeDeimosRouter:
    """Get the global Lattice Deimos Router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = LatticeDeimosRouter()
    return _router_instance

# Convenience functions for common routing tasks
async def route_analysis_request(
    prompt: str, 
    context: Optional[str] = None,
    explain: bool = False
) -> RoutingResponse:
    """Route a ticket analysis request"""
    router = get_router()
    return await router.route_request(
        prompt=prompt,
        task="analysis",
        context=context,
        max_tokens=2000,
        temperature=0.3,
        explain=explain
    )

async def route_ticket_analysis_request(
    prompt: str,
    context: Optional[str] = None,
    explain: bool = False
) -> RoutingResponse:
    """Route a Slack thread/ticket analysis request"""
    router = get_router()
    return await router.route_request(
        prompt=prompt,
        task="ticket_analysis",
        context=context,
        max_tokens=2500,
        temperature=0.2,
        explain=explain
    )

async def route_summarization_request(
    prompt: str,
    context: Optional[str] = None,
    explain: bool = False
) -> RoutingResponse:
    """Route a summarization request"""
    router = get_router()
    return await router.route_request(
        prompt=prompt,
        task="summarization",
        context=context,
        max_tokens=1000,
        temperature=0.2,
        explain=explain
    )

async def route_code_generation_request(
    prompt: str,
    context: Optional[str] = None,
    explain: bool = False
) -> RoutingResponse:
    """Route a code generation request"""
    router = get_router()
    return await router.route_request(
        prompt=prompt,
        task="coding",
        context=context,
        max_tokens=3000,
        temperature=0.1,
        explain=explain
    )
