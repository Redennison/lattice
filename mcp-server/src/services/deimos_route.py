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
        
        # Create routing rules for different tasks
        task_rule = TaskRule(
            name="lattice-task-router",
            rules={
                # Ticket analysis - balance cost and quality
                'analysis': 'openai/gpt-4o-mini',
                'ticket_analysis': 'openai/gpt-4o-mini',
                
                # Code-related tasks - use more powerful models
                'coding': 'openai/gpt-4o',
                'code_generation': 'openai/gpt-4o',
                'code_review': 'openai/gpt-4o',
                
                # Simple tasks - use cost-effective models
                'summarization': 'openai/gpt-4o-mini',
                'classification': 'openai/gpt-4o-mini',
                'extraction': 'openai/gpt-4o-mini',
                
                # Creative tasks - use balanced model
                'creative': 'openai/gpt-4o-mini',
                
                # Complex analysis - use powerful model
                'complex_analysis': 'openai/gpt-4o'
            }
        )
        
        # Code detection rule - if code is detected, route to better model
        code_rule = CodeRule(
            name="lattice-code-detector",
            code='openai/gpt-4o',  # Use GPT-4o for code-heavy requests
            not_code=task_rule     # Otherwise use task-based routing
        )
        
        # Message length rule for fallback routing
        length_rule = MessageLengthRule(
            name="lattice-length-router",
            short_threshold=200,   # Short messages
            long_threshold=1500,   # Long messages
            short_model='openai/gpt-4o-mini',
            medium_model='openai/gpt-4o-mini', 
            long_model='openai/gpt-4o'  # Use better model for complex requests
        )
        
        # Create the main Lattice router
        lattice_router = Router(
            name="lattice-router",
            rules=[
                code_rule,    # First check for code
                task_rule,    # Then check task type
                length_rule   # Finally check message length
            ],
            default_model="openai/gpt-4o-mini"  # Cost-effective default
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
