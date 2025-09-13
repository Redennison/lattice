"""
Analyze Request Tool

This MCP tool takes raw ticket text from Slack and converts it into
structured data suitable for Jira ticket creation and code analysis.
"""

import re
import os
from typing import Dict, Any, List
from openai import AsyncOpenAI

from models.ticket import TicketRequest, AnalysisResult, AcceptanceCriteria
from utils.logger import logger

# Initialize OpenAI client
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
  Use AI to analyze the ticket and extract structured information.
  
  Args:
    ticket: Ticket request data
  
  Returns:
    Dictionary with AI analysis results
  """
  prompt = f"""
  Analyze this bug report and extract structured information:
    
    Title: {ticket.title}
    Description: {ticket.description}
    Severity: {ticket.severity}
    
    Please provide a JSON response with:
    1. "improved_title": A clear, concise title (max 80 chars)
    2. "summary": A 2-3 sentence summary for Jira
    3. "labels": Array of relevant labels (bug, frontend, api, etc.)
    4. "acceptance_criteria": Array of specific, testable criteria
    5. "code_queries": Array of search terms to find relevant code
    6. "confidence": Float 0-1 indicating how well you understand the issue
    7. "issue_type": "Bug", "Task", or "Story"
    8. "priority": "High", "Medium", or "Low"
    
    Focus on being specific and actionable. If information is unclear, indicate lower confidence.
    """
    
  try:
    response = await openai_client.chat.completions.create(
      model="gpt-4o-mini",  # Use cost-effective model for hackathon
      messages=[
        {"role": "system", "content": "You are a senior software engineer analyzing bug reports. Respond only with valid JSON."},
        {"role": "user", "content": prompt}
      ],
      temperature=0.1,  # Low temperature for consistent results
      max_tokens=1000
    )
        
    import json
    ai_result = json.loads(response.choices[0].message.content)
    logger.info("AI analysis completed successfully")
    return ai_result
        
  except Exception as e:
    logger.warning(f"AI analysis failed: {str(e)}, using fallback")
    # Fallback analysis if AI fails
    return {
      "improved_title": ticket.title[:80],
      "summary": ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description,
      "labels": ["bug"] + ticket.labels,
      "acceptance_criteria": ["Issue is resolved", "No regression in related functionality"],
      "code_queries": ["error", "bug", "fix"],
      "confidence": 0.3,  # Low confidence for fallback
      "issue_type": "Bug",
      "priority": ticket.severity.value.title()
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
        priority=ai_analysis.get("priority", ticket.severity.value.title())
    )
    