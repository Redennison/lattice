"""
Jira Create Issue Tool

This MCP tool creates Jira issues from analysis results with formatted content.
"""

from typing import Dict, Any
from datetime import datetime
from models.schemas import AnalysisResult, JiraIssue, JiraTicketContent
from services.jira_service import JiraService
from utils.logger import logger

async def jira_create_issue_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a Jira issue from the analyzed and formatted ticket content.
    
    Args:
        arguments: Contains analysis_result from analyze_request tool
        
    Returns:
        JiraIssue details as dictionary
    """
    logger.info("Creating Jira issue from analyzed content...")
    
    # Parse the analysis result
    analysis_data = arguments.get("analysis_result", {})
    user_id = arguments.get("user_id")
    project_key = arguments.get("project_key", "PROJ")  # Default project
    
    if not analysis_data:
        raise ValueError("analysis_result is required")
    
    # Extract the Jira ticket content
    jira_ticket_data = analysis_data.get("jira_ticket", {})
    
    try:
        # Create JiraTicketContent from the data
        jira_ticket = JiraTicketContent(
            title=jira_ticket_data.get("title"),
            description=jira_ticket_data.get("description"),
            issue_type=jira_ticket_data.get("issue_type", "Bug"),
            priority=jira_ticket_data.get("priority", "Medium"),
            labels=jira_ticket_data.get("labels", []),
            components=jira_ticket_data.get("components", []),
            acceptance_criteria=jira_ticket_data.get("acceptance_criteria", []),
            steps_to_reproduce=jira_ticket_data.get("steps_to_reproduce"),
            expected_behavior=jira_ticket_data.get("expected_behavior"),
            actual_behavior=jira_ticket_data.get("actual_behavior"),
            technical_details=jira_ticket_data.get("technical_details")
        )
        
        # Add metadata to the ticket
        metadata = {
            "confidence_score": analysis_data.get("confidence_score"),
            "estimated_effort": analysis_data.get("estimated_effort"),
            "suggested_assignee": analysis_data.get("suggested_assignee"),
            "routing_metadata": analysis_data.get("routing_metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Invalid Jira ticket format: {str(e)}")
        raise ValueError(f"Invalid Jira ticket format: {str(e)}")
    
    # Create the issue in Jira
    jira_service = JiraService()
    
    try:
        # Format the description with rich ADF content
        formatted_description = _format_jira_description(jira_ticket, metadata)
        
        # Create the issue
        issue_data = {
            "project": {"key": project_key},
            "summary": jira_ticket.title,
            "description": formatted_description,
            "issuetype": {"name": jira_ticket.issue_type},
            "priority": {"name": jira_ticket.priority},
            "labels": jira_ticket.labels,
            "components": [{"name": comp} for comp in jira_ticket.components] if jira_ticket.components else []
        }
        
        # Add custom fields if available
        if jira_ticket.acceptance_criteria:
            issue_data["customfield_10001"] = _format_acceptance_criteria(jira_ticket.acceptance_criteria)
        
        if metadata.get("estimated_effort"):
            issue_data["customfield_10002"] = metadata["estimated_effort"]
        
        if metadata.get("suggested_assignee"):
            issue_data["assignee"] = {"name": metadata["suggested_assignee"]}
        
        # Create the issue
        created_issue = await jira_service.create_issue(issue_data, user_id)
        
        # Log the routing decision for analysis
        logger.info(f"Issue created using model: {metadata.get('routing_metadata', {}).get('selected_model')}")
        logger.info(f"Estimated cost: ${metadata.get('routing_metadata', {}).get('estimated_cost', 0):.4f}")
        
        # Return JiraIssue as dictionary
        return {
            "key": created_issue.key,
            "id": created_issue.id,
            "url": f"https://your-domain.atlassian.net/browse/{created_issue.key}",
            "status": "Open",
            "created_at": datetime.now().isoformat(),
            "project_key": project_key,
            "issue_type": jira_ticket.issue_type,
            "priority": jira_ticket.priority,
            "confidence_score": metadata.get("confidence_score"),
            "estimated_effort": metadata.get("estimated_effort")
        }
        
    except Exception as e:
        logger.error(f"Failed to create Jira issue: {str(e)}")
        raise Exception(f"Failed to create Jira issue: {str(e)}")

def _format_jira_description(ticket: JiraTicketContent, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the description as Atlassian Document Format (ADF) for rich content.
    """
    # Create ADF structure for rich formatting
    adf_content = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Issue Description"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": ticket.description}]
            }
        ]
    }
    
    # Add technical details section if available
    if ticket.technical_details:
        adf_content["content"].extend([
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Technical Details"}]
            },
            {
                "type": "codeBlock",
                "attrs": {"language": "json"},
                "content": [{"type": "text", "text": str(ticket.technical_details)}]
            }
        ])
    
    # Add steps to reproduce if available
    if ticket.steps_to_reproduce:
        adf_content["content"].extend([
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Steps to Reproduce"}]
            },
            {
                "type": "orderedList",
                "content": [
                    {"type": "listItem", "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": step}]},
                    ]} for step in ticket.steps_to_reproduce
                ]
            }
        ])
    
    # Add expected vs actual behavior
    if ticket.expected_behavior and ticket.actual_behavior:
        adf_content["content"].extend([
            {
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "Expected Behavior"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": ticket.expected_behavior}]
            },
            {
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "Actual Behavior"}]
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": ticket.actual_behavior}]
            }
        ])
    
    # Add metadata footer
    if metadata.get("routing_metadata"):
        routing = metadata["routing_metadata"]
        adf_content["content"].extend([
            {
                "type": "rule"
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"Analysis Confidence: {metadata.get('confidence_score', 0):.1%}", "marks": [{"type": "em"}]},
                    {"type": "text", "text": f" | Model: {routing.get('selected_model', 'Unknown')}", "marks": [{"type": "em"}]},
                    {"type": "text", "text": f" | Cost: ${routing.get('estimated_cost', 0):.4f}", "marks": [{"type": "em"}]}
                ]
            }
        ])
    
    return adf_content

def _format_acceptance_criteria(criteria: list) -> str:
    """
    Formats acceptance criteria for Jira custom field.
    """
    formatted = "Acceptance Criteria:\n"
    for i, criterion in enumerate(criteria, 1):
        formatted += f"{i}. {criterion}\n"
    return formatted
