"""
Analyze Request Tool

This MCP tool takes raw Slack conversation/thread and converts it into
structured Jira ticket information using Deimos Router for cost-effective LLM selection.
"""

import re
import os
import json
from typing import Dict, Any, List

from models.ticket import TicketRequest, AnalysisResult, AcceptanceCriteria
from services.deimos_route import route_ticket_analysis_request
from utils.logger import logger

async def analyze_request_tool(arguments: Dict[str, Any]) -> AnalysisResult:
  logger.info("Starting ticket analysis...")
  
  # Parse input arguments into TicketRequest model
  try:
    ticket_request = TicketRequest(**arguments)
  except Exception as e:
    logger.error(f"Invalid ticket request format: {str(e)}")
    raise ValueError(f"Invalid ticket request: {str(e)}")
    
  # Extract key information using pattern matching
  extracted_info = _extract_basic_info(ticket_request)
    
  # Use AI to enhance the analysis
  ai_analysis = await _ai_analyze_ticket(ticket_request)
    
  # Combine pattern matching and AI results
  result = _combine_analysis_results(ticket_request, extracted_info, ai_analysis)
    
  logger.info(f"Analysis complete with confidence: {result.confidence}")
  return result

def _extract_basic_info(ticket: TicketRequest) -> Dict[str, Any]:
  """
  Extract basic information using pattern matching.
  
  Args:
    ticket: Ticket request data
  
  Returns:
    Dictionary with extracted information
  """
  text = f"{ticket.title} {ticket.description}".lower()
    
  # Common error patterns
  error_patterns = {
    "500": ["server error", "internal error", "500"],
    "404": ["not found", "404", "missing"],
    "timeout": ["timeout", "slow", "hanging"],
    "null": ["null", "undefined", "cannot read property"],
    "auth": ["unauthorized", "403", "permission", "login"]
  }
    
  # Extract error types
  detected_errors = []
  for error_type, patterns in error_patterns.items():
    if any(pattern in text for pattern in patterns):
      detected_errors.append(error_type)
    
  # Extract file/function hints
  file_patterns = [
    r'(\w+\.(js|ts|py|java|go|rb))',  # File extensions
    r'(/[\w/]+\.(js|ts|py|java|go|rb))',  # File paths
    r'(\w+Controller|\w+Service|\w+Handler)',  # Common class patterns
  ]
    
  code_hints = []
  for pattern in file_patterns:
    matches = re.findall(pattern, text, re.IGNORECASE)
    code_hints.extend([match[0] if isinstance(match, tuple) else match for match in matches])
    
  # Extract endpoints
  endpoint_pattern = r'(GET|POST|PUT|DELETE|PATCH)\s+(/[\w/\-]+)'
  endpoints = re.findall(endpoint_pattern, text, re.IGNORECASE)
    
  return {
    "detected_errors": detected_errors,
    "code_hints": list(set(code_hints)),  # Remove duplicates
    "endpoints": [f"{method} {path}" for method, path in endpoints],
    "has_stack_trace": "stack trace" in text or "error:" in text,
    "mentions_recent_deploy": any(word in text for word in ["deploy", "deployment", "release", "merge"])
  }

async def _ai_analyze_ticket(ticket: TicketRequest) -> Dict[str, Any]:
  """
  Use Deimos Router to analyze the Slack conversation/thread and generate Jira ticket information.
  
  Args:
    ticket: Ticket request data containing Slack conversation
  
  Returns:
    Dictionary with AI analysis results formatted for Jira ticket creation
  """
  
  # Create the prompt for Jira ticket generation
  jira_prompt = f"""
You are analyzing a Slack conversation/thread about a bug report to create a Jira ticket. 

Slack Thread/Conversation:
Title: {ticket.title}
Description: {ticket.description}
Severity: {ticket.severity}

Please analyze this conversation and create a properly formatted Jira ticket response with the following structure:

**Summary of Problem:**
[Provide a clear, concise summary of the issue in 1-2 sentences]

**Acceptance Criteria for Issue:**
- [Specific, testable criterion 1]
- [Specific, testable criterion 2]
- [Additional criteria as needed]

**Issue Type:** [Bug/Task/Story]

**Priority:** [High/Medium/Low]

**Labels:** [Comma-separated relevant labels like: bug, frontend, api, authentication, etc.]

**Affected Components:**
- [Component/service/file mentioned in the conversation]
- [Additional components if applicable]

**Steps to Reproduce:** (if mentioned in conversation)
1. [Step 1]
2. [Step 2]
3. [Expected vs Actual behavior]

**Additional Context:**
[Any relevant technical details, error messages, or context from the Slack thread]

Focus on extracting actionable information from the Slack conversation. If certain details are unclear from the conversation, note that in the ticket for follow-up.
"""
  
  try:
    # Use Deimos Router for cost-effective model selection
    logger.info("Using Deimos Router for ticket analysis...")
    
    routing_response = await route_ticket_analysis_request(
      prompt=jira_prompt,
      context=f"Slack conversation analysis for bug: {ticket.title}",
      explain=True  # Get routing explanation for debugging
    )
    
    logger.info(f"Deimos selected model: {routing_response.selected_model}")
    if routing_response.estimated_cost:
      logger.info(f"Estimated cost: ${routing_response.estimated_cost}")
    
    # Log routing explanation if available
    if routing_response.routing_metadata and 'explain' in routing_response.routing_metadata:
      for entry in routing_response.routing_metadata['explain']:
        logger.debug(f"Rule: {entry.get('rule_name')} - Decision: {entry.get('decision')}")
    
    # Parse the structured response to extract JSON data
    ticket_content = routing_response.response
    
    # Extract structured information from the formatted response
    structured_data = _parse_jira_ticket_response(ticket_content, ticket)
    
    logger.info("Deimos analysis completed successfully")
    return structured_data
        
  except Exception as e:
    logger.warning(f"Deimos analysis failed: {str(e)}, using fallback")
    # Fallback analysis if Deimos fails
    return {
      "improved_title": ticket.title[:80],
      "summary": ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description,
      "labels": ["bug"] + ticket.labels,
      "acceptance_criteria": ["Issue is resolved", "No regression in related functionality"],
      "code_queries": ["error", "bug", "fix"],
      "confidence": 0.3,  # Low confidence for fallback
      "issue_type": "Bug",
      "priority": ticket.severity.value.title(),
      "jira_ticket_content": f"**Summary of Problem:**\n{ticket.description}\n\n**Acceptance Criteria for Issue:**\n- Issue is resolved\n- No regression in related functionality"
    }

def _parse_jira_ticket_response(ticket_content: str, ticket: TicketRequest) -> Dict[str, Any]:
  """
  Parse the Jira ticket formatted response from Deimos and extract structured data.
  
  Args:
    ticket_content: The formatted Jira ticket response from LLM
    ticket: Original ticket request for fallback data
    
  Returns:
    Dictionary with structured analysis results
  """
  try:
    # Extract summary
    summary_match = re.search(r'\*\*Summary of Problem:\*\*\s*\n(.*?)(?=\n\*\*|\n\n|\Z)', ticket_content, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ticket.description[:200]
    
    # Extract acceptance criteria
    criteria_match = re.search(r'\*\*Acceptance Criteria for Issue:\*\*\s*\n(.*?)(?=\n\*\*|\n\n|\Z)', ticket_content, re.DOTALL)
    criteria_text = criteria_match.group(1).strip() if criteria_match else ""
    criteria_list = [line.strip('- ').strip() for line in criteria_text.split('\n') if line.strip().startswith('-')]
    
    if not criteria_list:
      criteria_list = ["Issue is resolved", "No regression in related functionality"]
    
    # Extract issue type
    issue_type_match = re.search(r'\*\*Issue Type:\*\*\s*([^\n]+)', ticket_content)
    issue_type = issue_type_match.group(1).strip() if issue_type_match else "Bug"
    
    # Extract priority
    priority_match = re.search(r'\*\*Priority:\*\*\s*([^\n]+)', ticket_content)
    priority = priority_match.group(1).strip() if priority_match else ticket.severity.value.title()
    
    # Extract labels
    labels_match = re.search(r'\*\*Labels:\*\*\s*([^\n]+)', ticket_content)
    labels_text = labels_match.group(1).strip() if labels_match else "bug"
    labels = [label.strip() for label in labels_text.split(',')]
    
    # Extract components for code queries
    components_match = re.search(r'\*\*Affected Components:\*\*\s*\n(.*?)(?=\n\*\*|\n\n|\Z)', ticket_content, re.DOTALL)
    components_text = components_match.group(1).strip() if components_match else ""
    components = [line.strip('- ').strip() for line in components_text.split('\n') if line.strip().startswith('-')]
    
    # Generate improved title from summary
    title_words = summary.split()[:10]  # First 10 words
    improved_title = ' '.join(title_words)
    if len(improved_title) > 80:
      improved_title = improved_title[:77] + "..."
    
    return {
      "improved_title": improved_title,
      "summary": summary,
      "labels": labels + ticket.labels,  # Combine with existing labels
      "acceptance_criteria": criteria_list,
      "code_queries": components + labels,  # Use components and labels as search terms
      "confidence": 0.8,  # High confidence when using Deimos
      "issue_type": issue_type,
      "priority": priority,
      "jira_ticket_content": ticket_content  # Store the full formatted content
    }
    
  except Exception as e:
    logger.warning(f"Failed to parse Jira ticket response: {str(e)}")
    # Return basic structure if parsing fails
    return {
      "improved_title": ticket.title[:80],
      "summary": ticket.description,
      "labels": ["bug"] + ticket.labels,
      "acceptance_criteria": ["Issue is resolved"],
      "code_queries": ["bug", "error"],
      "confidence": 0.5,
      "issue_type": "Bug", 
      "priority": ticket.severity.value.title(),
      "jira_ticket_content": ticket_content
    }

def _combine_analysis_results(
  ticket: TicketRequest, 
  extracted: Dict[str, Any], 
  ai_analysis: Dict[str, Any]
) -> AnalysisResult:
  """
  Combine pattern matching and AI analysis into final result.
  
  Args:
    ticket: Original ticket request
    extracted: Pattern matching results
    ai_analysis: AI analysis results
  
  Returns:
    Combined AnalysisResult
  """
  # Combine code queries from both sources
  combined_queries = list(set(
    ai_analysis.get("code_queries", []) + 
    extracted.get("code_hints", []) +
    [error for error in extracted.get("detected_errors", [])]
  ))
    
  # Enhance labels with detected patterns
  enhanced_labels = list(set(
    ai_analysis.get("labels", []) + 
    ticket.labels +
    extracted.get("detected_errors", [])
  ))
    
  # Adjust confidence based on available information
  base_confidence = ai_analysis.get("confidence", 0.5)
    
  # Boost confidence if we have good technical details
  if extracted.get("has_stack_trace"):
    base_confidence += 0.1
    if extracted.get("code_hints"):
      base_confidence += 0.1
    if extracted.get("endpoints"):
      base_confidence += 0.1
    
    # Cap confidence at 1.0
    final_confidence = min(base_confidence, 1.0)
    
    # Create acceptance criteria objects
    acceptance_criteria = [
      AcceptanceCriteria(description=criteria)
      for criteria in ai_analysis.get("acceptance_criteria", [])
    ]
    
    return AnalysisResult(
      title=ai_analysis.get("improved_title", ticket.title),
      summary=ai_analysis.get("summary", ticket.description),
      labels=enhanced_labels,
      acceptance_criteria=acceptance_criteria,
      code_queries=combined_queries,
      confidence=final_confidence,
      issue_type=ai_analysis.get("issue_type", "Bug"),
      priority=ai_analysis.get("priority", ticket.severity.value.title()),
      jira_ticket_content=ai_analysis.get("jira_ticket_content")
    )
    