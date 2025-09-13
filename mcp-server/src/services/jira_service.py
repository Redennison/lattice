"""
Jira Service

Handles all Jira API interactions including issue creation,
status updates, and linking with GitHub PRs.
"""

import os
from typing import Optional, Dict, Any, List
from atlassian import Jira

from models.ticket import AnalysisResult, JiraIssue, AcceptanceCriteria
from utils.logger import logger

class JiraService:
  """Service for Jira API operations."""
  
  def __init__(self):
    """Initialize Jira client with API credentials."""
    self.url = os.getenv("JIRA_URL")
    self.username = os.getenv("JIRA_USERNAME")
    self.api_token = os.getenv("JIRA_API_TOKEN")
    self.project_key = os.getenv("JIRA_PROJECT_KEY")
    
    if not all([self.url, self.username, self.api_token, self.project_key]):
      raise ValueError("Jira environment variables are required: JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN, JIRA_PROJECT_KEY")
    
    self.client = Jira(
      url=self.url,
      username=self.username,
      password=self.api_token,
      cloud=True
    )
    
    logger.info(f"Jira service initialized for {self.url}")
  
  async def create_issue(self, analysis: AnalysisResult, user_id: str = None) -> Optional[JiraIssue]:
    """
    Create a Jira issue from analysis results.
    
    Args:
      analysis: Analysis result from analyze_request tool
      user_id: Optional Slack user ID for assignment
    
    Returns:
      JiraIssue object if successful, None otherwise
    """
    logger.info(f"Creating Jira issue: {analysis.title}")
    
    try:
      # Build issue description in ADF (Atlassian Document Format)
      description = self._build_description(analysis)
      
      # Prepare issue data
      issue_data = {
        "project": {"key": self.project_key},
        "summary": analysis.title,
        "description": description,
        "issuetype": {"name": analysis.issue_type},
        "priority": {"name": analysis.priority},
        "labels": analysis.labels
      }
      
      # Add assignee if user mapping exists
      if user_id:
        assignee = self._map_slack_user_to_jira(user_id)
        if assignee:
          issue_data["assignee"] = {"accountId": assignee}
      
      # Create the issue
      issue = self.client.create_issue(fields=issue_data)
      
      # Get issue details
      issue_key = issue["key"]
      issue_url = f"{self.url}/browse/{issue_key}"
      
      logger.info(f"Created Jira issue {issue_key}")
      
      return JiraIssue(
        key=issue_key,
        url=issue_url,
        id=issue["id"]
      )
    
    except Exception as e:
      logger.error(f"Failed to create Jira issue: {str(e)}")
      return None
  
  def _build_description(self, analysis: AnalysisResult) -> Dict[str, Any]:
    """
    Build Jira description in ADF format.
    
    Args:
      analysis: Analysis result
    
    Returns:
      ADF formatted description
    """
    # Build acceptance criteria list
    criteria_items = []
    for criteria in analysis.acceptance_criteria:
      criteria_items.append({
        "type": "listItem",
        "content": [
          {
            "type": "paragraph",
            "content": [
              {
                "type": "text",
                "text": criteria.description
              }
            ]
          }
        ]
      })
    
    # Build code queries list
    query_items = []
    for query in analysis.code_queries:
      query_items.append({
        "type": "listItem",
        "content": [
          {
            "type": "paragraph",
            "content": [
              {
                "type": "text",
                "text": f"`{query}`",
                "marks": [{"type": "code"}]
              }
            ]
          }
        ]
      })
    
    # Complete ADF document
    adf_content = {
      "version": 1,
      "type": "doc",
      "content": [
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": analysis.summary
            }
          ]
        },
        {
          "type": "heading",
          "attrs": {"level": 3},
          "content": [
            {
              "type": "text",
              "text": "Acceptance Criteria"
            }
          ]
        },
        {
          "type": "bulletList",
          "content": criteria_items
        },
        {
          "type": "heading",
          "attrs": {"level": 3},
          "content": [
            {
              "type": "text",
              "text": "Code Areas to Investigate"
            }
          ]
        },
        {
          "type": "bulletList",
          "content": query_items
        },
        {
          "type": "paragraph",
          "content": [
            {
              "type": "text",
              "text": f"Analysis Confidence: {analysis.confidence:.1%}",
              "marks": [{"type": "em"}]
            }
          ]
        }
      ]
    }
    
    return adf_content
  
  def _map_slack_user_to_jira(self, slack_user_id: str) -> Optional[str]:
    """
    Map Slack user ID to Jira account ID.
    
    Args:
      slack_user_id: Slack user ID
    
    Returns:
      Jira account ID if mapping exists, None otherwise
    """
    # In production, this would query a user mapping database
    # For hackathon, return None to leave unassigned
    logger.info(f"User mapping not implemented for {slack_user_id}")
    return None
  
  async def add_comment(self, issue_key: str, comment: str) -> bool:
    """
    Add a comment to a Jira issue.
    
    Args:
      issue_key: Jira issue key (e.g., PROJ-123)
      comment: Comment text
    
    Returns:
      True if successful, False otherwise
    """
    try:
      self.client.issue_add_comment(issue_key, comment)
      logger.info(f"Added comment to {issue_key}")
      return True
    
    except Exception as e:
      logger.error(f"Failed to add comment to {issue_key}: {str(e)}")
      return False
  
  async def link_github_pr(self, issue_key: str, pr_url: str) -> bool:
    """
    Link a GitHub PR to a Jira issue.
    
    Args:
      issue_key: Jira issue key
      pr_url: GitHub PR URL
    
    Returns:
      True if successful, False otherwise
    """
    comment = f"🔧 Proposed fix available: {pr_url}"
    return await self.add_comment(issue_key, comment)
  
  async def transition_issue(self, issue_key: str, transition_name: str) -> bool:
    """
    Transition a Jira issue to a new status.
    
    Args:
      issue_key: Jira issue key
      transition_name: Name of transition (e.g., "In Progress", "Done")
    
    Returns:
      True if successful, False otherwise
    """
    try:
      # Get available transitions
      transitions = self.client.get_issue_transitions(issue_key)
      
      # Find matching transition
      transition_id = None
      for transition in transitions["transitions"]:
        if transition["name"].lower() == transition_name.lower():
          transition_id = transition["id"]
          break
      
      if not transition_id:
        logger.warning(f"Transition '{transition_name}' not found for {issue_key}")
        return False
      
      # Execute transition
      self.client.issue_transition(issue_key, transition_id)
      logger.info(f"Transitioned {issue_key} to '{transition_name}'")
      return True
    
    except Exception as e:
      logger.error(f"Failed to transition {issue_key}: {str(e)}")
      return False

# Global service instance
jira_service = JiraService()
