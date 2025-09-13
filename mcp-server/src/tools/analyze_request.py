"""
Analyze Request Tool

This MCP tool takes parsed Slack conversation and uses Deimos Router to create
optimized Jira ticket content with intelligent LLM selection.
"""

import re
from typing import Dict, Any, List, Optional

from models.schemas import (
    AnalysisRequest, SlackContext, ParsedSlackInfo,
    AnalysisResult, JiraTicketContent, IssueType, Severity
)
from services.deimos_route import DeimosRouter
from utils.logger import logger

async def analyze_request_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes Slack conversation and creates Jira ticket content using Deimos Router.
    
    Args:
        arguments: Contains slack_context, parsed_info, and severity
        
    Returns:
        AnalysisResult as dictionary containing Jira ticket and metadata
    """
    logger.info("Starting Slack conversation analysis...")
    
    # Parse input into structured format
    try:
        slack_context = SlackContext(**arguments.get('slack_context', {}))
        parsed_info = ParsedSlackInfo(**arguments.get('parsed_info', {}))
        severity = Severity(arguments.get('severity', 'medium'))
        
        request = AnalysisRequest(
            slack_context=slack_context,
            parsed_info=parsed_info,
            severity=severity
        )
    except Exception as e:
        logger.error(f"Invalid analysis request: {str(e)}")
        raise ValueError(f"Invalid analysis request: {str(e)}")
    
    # Analyze conversation to determine routing parameters
    routing_params = _analyze_conversation_complexity(request)
    
    # Use Deimos Router to create Jira ticket with optimal LLM
    jira_content = await _route_to_optimal_llm(request, routing_params)
    
    # Extract code search queries from the analysis
    code_queries = _extract_code_queries(request, jira_content)
    
    # Create analysis result
    result = AnalysisResult(
        jira_ticket=jira_content,
        code_queries=code_queries,
        confidence_score=routing_params.get('confidence', 0.8),
        routing_metadata=routing_params.get('metadata', {}),
        suggested_assignee=routing_params.get('suggested_assignee'),
        estimated_effort=routing_params.get('effort_estimate')
    )
    
    logger.info(f"Analysis complete with confidence: {result.confidence_score}")
    
    # Return as dictionary for MCP compatibility
    return {
        'jira_ticket': {
            'title': result.jira_ticket.title,
            'description': result.jira_ticket.description,
            'issue_type': result.jira_ticket.issue_type.value,
            'priority': result.jira_ticket.priority,
            'labels': result.jira_ticket.labels,
            'components': result.jira_ticket.components,
            'acceptance_criteria': result.jira_ticket.acceptance_criteria,
            'steps_to_reproduce': result.jira_ticket.steps_to_reproduce,
            'expected_behavior': result.jira_ticket.expected_behavior,
            'actual_behavior': result.jira_ticket.actual_behavior,
            'technical_details': result.jira_ticket.technical_details
        },
        'code_queries': result.code_queries,
        'confidence_score': result.confidence_score,
        'routing_metadata': result.routing_metadata,
        'suggested_assignee': result.suggested_assignee,
        'estimated_effort': result.estimated_effort
    }

def _analyze_conversation_complexity(request: AnalysisRequest) -> Dict[str, Any]:
    """
    Analyzes conversation complexity to determine optimal routing parameters.
    
    Args:
        request: Analysis request with Slack context and parsed info
        
    Returns:
        Dictionary with routing parameters and metadata
    """
    conversation = request.slack_context.conversation.lower()
    parsed = request.parsed_info
      
    # Determine complexity factors
    complexity_factors = {
        'has_code': any(marker in conversation for marker in ['```', 'def ', 'function', 'class ', 'import']),
        'has_errors': bool(parsed.error_messages),
        'has_stack_trace': 'traceback' in conversation or 'stack trace' in conversation,
        'message_count': len(request.slack_context.thread_messages) if request.slack_context.thread_messages else 1,
        'conversation_length': len(conversation),
        'technical_complexity': len(parsed.detected_keywords),
        'urgency_level': len(parsed.urgency_indicators)
    }
      
    # Detect programming languages and frameworks
    detected_languages = []
    language_keywords = {
        'python': ['python', '.py', 'django', 'flask', 'fastapi', 'pip', 'pytest'],
        'javascript': ['javascript', '.js', 'node', 'npm', 'react', 'vue', 'angular'],
        'typescript': ['typescript', '.ts', 'tsx', 'type', 'interface'],
        'java': ['java', '.java', 'spring', 'maven', 'gradle'],
        'go': ['golang', '.go', 'goroutine', 'channel'],
        'rust': ['rust', '.rs', 'cargo', 'crate'],
        'sql': ['sql', 'query', 'database', 'table', 'select', 'insert']
    }
    
    for lang, keywords in language_keywords.items():
        if any(kw in conversation for kw in keywords):
            detected_languages.append(lang)
      
    # Determine task type for Deimos routing
    task_type = _determine_task_type(complexity_factors, detected_languages, parsed)
    
    # Calculate effort estimate based on complexity
    effort_estimate = _estimate_effort(complexity_factors)
    
    # Suggest assignee based on detected components
    suggested_assignee = _suggest_assignee(parsed.mentioned_files, detected_languages)
    
    return {
        'task_type': task_type,
        'detected_languages': detected_languages,
        'complexity_factors': complexity_factors,
        'effort_estimate': effort_estimate,
        'suggested_assignee': suggested_assignee,
        'confidence': _calculate_confidence(complexity_factors),
        'metadata': {
            'severity': request.severity.value,
            'has_attachments': bool(request.slack_context.attachments),
            'channel_id': request.slack_context.channel_id,
            'user_id': request.slack_context.user_id
        }
    }

def _determine_task_type(complexity_factors: Dict[str, Any], languages: List[str], parsed: ParsedSlackInfo) -> str:
    """
    Determines the task type for Deimos routing based on complexity analysis.
    """
    if complexity_factors['has_errors'] and complexity_factors['has_stack_trace']:
        return 'debugging'
    elif complexity_factors['has_code']:
        return 'coding'
    elif 'architecture' in ' '.join(parsed.detected_keywords).lower():
        return 'architecture'
    elif complexity_factors['technical_complexity'] > 5:
        return 'complex_analysis'
    elif complexity_factors['conversation_length'] < 500:
        return 'simple_query'
    else:
        return 'ticket_analysis'

def _estimate_effort(complexity_factors: Dict[str, Any]) -> str:
    """
    Estimates effort based on complexity factors (T-shirt sizing).
    """
    score = 0
    score += 3 if complexity_factors['has_code'] else 0
    score += 2 if complexity_factors['has_errors'] else 0
    score += 2 if complexity_factors['has_stack_trace'] else 0
    score += 1 if complexity_factors['message_count'] > 5 else 0
    score += 2 if complexity_factors['conversation_length'] > 2000 else 0
    score += 1 if complexity_factors['technical_complexity'] > 3 else 0
    
    if score <= 2:
        return 'S'
    elif score <= 5:
        return 'M'
    elif score <= 8:
        return 'L'
    else:
        return 'XL'

def _suggest_assignee(mentioned_files: List[str], languages: List[str]) -> Optional[str]:
    """
    Suggests assignee based on detected components and languages.
    """
    # This would integrate with team expertise mapping
    # For now, return None to let Jira auto-assign
    return None

def _calculate_confidence(complexity_factors: Dict[str, Any]) -> float:
    """
    Calculates confidence score based on available information.
    """
    confidence = 0.5  # Base confidence
    
    if complexity_factors['has_errors']:
        confidence += 0.15
    if complexity_factors['has_stack_trace']:
        confidence += 0.15
    if complexity_factors['technical_complexity'] > 3:
        confidence += 0.1
    if complexity_factors['message_count'] > 3:
        confidence += 0.1
    
    return min(confidence, 1.0)

async def _route_to_optimal_llm(request: AnalysisRequest, routing_params: Dict[str, Any]) -> JiraTicketContent:

    """
    Routes to the optimal LLM using Deimos Router for Jira ticket creation.
    
    This is where the magic happens - Deimos intelligently selects the best model
    based on multiple factors to optimize cost and quality.
    """
    router = DeimosRouter()
    
    # Create sophisticated prompt for Jira ticket generation
    prompt = _create_jira_generation_prompt(request, routing_params)
    
    # Determine cost priority based on urgency and complexity
    cost_priority = _determine_cost_priority(request, routing_params)
    
    # Route through Deimos with rich metadata for intelligent decision
    response = await router.route_ticket_analysis_request(
        prompt=prompt,
        context=request.slack_context.conversation,
        task=routing_params['task_type'],
        cost_priority=cost_priority,
        metadata={
            'detected_languages': routing_params['detected_languages'],
            'complexity_factors': routing_params['complexity_factors'],
            'effort_estimate': routing_params['effort_estimate'],
            'severity': request.severity.value,
            'parsed_keywords': request.parsed_info.detected_keywords,
            'error_messages': request.parsed_info.error_messages,
            'mentioned_files': request.parsed_info.mentioned_files
        }
    )
    
    # Parse the LLM response into structured Jira ticket
    jira_content = _parse_llm_response_to_jira(response, request)
    
    # Store routing decision metadata
    routing_params['metadata']['selected_model'] = response.selected_model
    routing_params['metadata']['routing_reason'] = response.reasoning
    routing_params['metadata']['estimated_cost'] = response.estimated_cost
    
    logger.info(f"Routed to {response.selected_model} (cost: ${response.estimated_cost:.4f})")
    
    return jira_content

def _create_jira_generation_prompt(request: AnalysisRequest, routing_params: Dict[str, Any]) -> str:
    """
    Creates a sophisticated prompt for Jira ticket generation.
    """
    # Build context-aware prompt
    prompt = f"""
You are a senior software engineer analyzing a Slack conversation to create a comprehensive Jira ticket.

SLACK CONVERSATION:
{request.slack_context.conversation}

PARSED INFORMATION:
- Initial Summary: {request.parsed_info.initial_summary}
- Detected Keywords: {', '.join(request.parsed_info.detected_keywords)}
- Mentioned Files: {', '.join(request.parsed_info.mentioned_files) if request.parsed_info.mentioned_files else 'None'}
- Error Messages: {' | '.join(request.parsed_info.error_messages) if request.parsed_info.error_messages else 'None'}
- User Intent: {request.parsed_info.user_intent}
- Severity: {request.severity.value}

TECHNICAL CONTEXT:
- Detected Languages: {', '.join(routing_params['detected_languages']) if routing_params['detected_languages'] else 'Not specified'}
- Has Code Snippets: {routing_params['complexity_factors']['has_code']}
- Has Stack Trace: {routing_params['complexity_factors']['has_stack_trace']}
- Estimated Effort: {routing_params['effort_estimate']}

Create a detailed Jira ticket with the following JSON structure:
{{
    "title": "Clear, actionable title (max 100 chars)",
    "description": "Comprehensive description in Markdown/ADF format with all relevant details",
    "issue_type": "Bug|Task|Story",
    "priority": "Critical|High|Medium|Low",
    "labels": ["relevant", "labels"],
    "components": ["affected", "components"],
    "acceptance_criteria": [
        "Specific, testable criterion 1",
        "Specific, testable criterion 2"
    ],
    "steps_to_reproduce": ["Step 1", "Step 2"] or null if not applicable,
    "expected_behavior": "What should happen" or null,
    "actual_behavior": "What actually happens" or null,
    "technical_details": {{
        "stack_trace": "if available",
        "error_codes": ["list of error codes"],
        "affected_endpoints": ["endpoints"],
        "database_queries": ["problematic queries"]
    }} or null
}}

IMPORTANT:
1. Extract ALL actionable information from the Slack conversation
2. Be specific and technical in your descriptions
3. Ensure acceptance criteria are testable
4. Include any mentioned workarounds or temporary fixes
5. Note any urgency indicators or business impact
6. Return ONLY valid JSON, no additional text
"""
    
    return prompt

def _determine_cost_priority(request: AnalysisRequest, routing_params: Dict[str, Any]) -> Optional[str]:

    """
    Determines cost priority based on urgency and severity.
    """
    # High urgency or critical issues get quality priority
    if request.severity == Severity.CRITICAL:
        return 'high_quality'
    elif request.severity == Severity.HIGH and routing_params['complexity_factors']['urgency_level'] > 2:
        return 'high_quality'
    elif request.severity == Severity.LOW and routing_params['effort_estimate'] == 'S':
        return 'low_cost'
    else:
        return 'balanced'  # Let Deimos decide based on content

def _parse_llm_response_to_jira(response: Any, request: AnalysisRequest) -> JiraTicketContent:
    """
    Parses the LLM response into structured JiraTicketContent.
    """
    try:
        # Parse JSON response from LLM
        import json
        ticket_data = json.loads(response.response)
        
        # Map issue type string to enum
        issue_type_map = {
            'bug': IssueType.BUG,
            'task': IssueType.TASK,
            'story': IssueType.STORY,
            'epic': IssueType.EPIC
        }
        issue_type = issue_type_map.get(ticket_data.get('issue_type', 'Bug').lower(), IssueType.BUG)
        
        return JiraTicketContent(
            title=ticket_data.get('title', request.parsed_info.initial_summary[:100]),
            description=ticket_data.get('description', request.slack_context.conversation),
            issue_type=issue_type,
            priority=ticket_data.get('priority', 'Medium'),
            labels=ticket_data.get('labels', ['bug']),
            components=ticket_data.get('components', []),
            acceptance_criteria=ticket_data.get('acceptance_criteria', ['Issue is resolved']),
            steps_to_reproduce=ticket_data.get('steps_to_reproduce'),
            expected_behavior=ticket_data.get('expected_behavior'),
            actual_behavior=ticket_data.get('actual_behavior'),
            technical_details=ticket_data.get('technical_details')
        )
    except Exception as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        # Fallback to basic ticket
        return JiraTicketContent(
            title=request.parsed_info.initial_summary[:100],
            description=f"**Slack Conversation:**\n{request.slack_context.conversation}\n\n**Error Messages:**\n{chr(10).join(request.parsed_info.error_messages)}",
            issue_type=IssueType.BUG,
            priority='Medium',
            labels=['bug', 'needs-triage'],
            components=[],
            acceptance_criteria=['Issue is resolved', 'No regression'],
            steps_to_reproduce=None,
            expected_behavior=None,
            actual_behavior=None,
            technical_details=None
        )

def _extract_code_queries(request: AnalysisRequest, jira_content: JiraTicketContent) -> List[str]:
    """
    Extracts code search queries from the analysis.
    """
    queries = []
    
    # Add mentioned files
    queries.extend(request.parsed_info.mentioned_files)
    
    # Add detected keywords
    queries.extend(request.parsed_info.detected_keywords)
    
    # Add components from Jira ticket
    queries.extend(jira_content.components)
    
    # Add error-related queries
    for error in request.parsed_info.error_messages:
        # Extract error codes or class names
        error_parts = error.split()
        queries.extend([part for part in error_parts if len(part) > 3])
    
    # Add labels as queries
    queries.extend(jira_content.labels)
    
    # Deduplicate and filter
    unique_queries = list(set(queries))
    
    # Filter out common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    filtered_queries = [q for q in unique_queries if q.lower() not in stop_words and len(q) > 2]
    
    return filtered_queries[:20]  # Limit to top 20 queries
