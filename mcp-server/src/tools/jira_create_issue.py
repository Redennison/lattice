"""
Jira Create Issue Tool

This MCP tool creates Jira issues from analysis results.
"""

from typing import Dict, Any
from models.ticket import AnalysisResult, JiraIssue
from services.jira_service import jira_service
from utils.logger import logger

async def jira_create_issue_tool(arguments: Dict[str, Any]) -> JiraIssue:
  """
  Create a Jira issue from analysis results.
  
  Args:
    arguments: Contains analysis_result and optional user_id
    
  Returns:
    JiraIssue with issue details
  """
  logger.info("Creating Jira issue...")
  
  # Parse arguments
  analysis_data = arguments.get("analysis_result", {})
  user_id = arguments.get("user_id")
  
  if not analysis_data:
    raise ValueError("analysis_result is required")
  
  # Convert dict to AnalysisResult model
  try:
    analysis = AnalysisResult(**analysis_data)
  except Exception as e:
    logger.error(f"Invalid analysis result format: {str(e)}")
    raise ValueError(f"Invalid analysis result: {str(e)}")
  
  # Create Jira issue
  jira_issue = await jira_service.create_issue(analysis, user_id)
  
  if not jira_issue:
    raise Exception("Failed to create Jira issue")
  
  logger.info(f"Created Jira issue: {jira_issue.key}")
  return jira_issue
