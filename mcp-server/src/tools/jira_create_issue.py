"""
Jira Create Issue Tool

This MCP tool creates Jira issues from analysis results with formatted content.
"""

from typing import Dict, Any
from datetime import datetime
from models.schemas import JiraIssue, JiraTicketContent, IssueType
from services.jira_service import get_jira_service
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
        issue_type_str = jira_ticket_data.get("issue_type", "Bug")
        if isinstance(issue_type_str, str):
            issue_type_map = {
                'bug': IssueType.BUG,
                'task': IssueType.TASK,
                'story': IssueType.STORY,
                'epic': IssueType.EPIC
            }
            issue_type = issue_type_map.get(issue_type_str.lower(), IssueType.BUG)
        else:
            issue_type = issue_type_str
            
        jira_ticket = JiraTicketContent(
            title=jira_ticket_data.get("title"),
            description=jira_ticket_data.get("description"),
            issue_type=issue_type,
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
    jira_service = get_jira_service()
    
    try:
        # Use plain text description instead of ADF to avoid format issues
        plain_description = _format_plain_description(jira_ticket, metadata)
        
        # Create the issue with only standard fields
        issue_data = {
            "project": {"key": project_key},
            "summary": jira_ticket.title,
            "description": plain_description,
            "issuetype": {"name": jira_ticket.issue_type.value},
            "labels": jira_ticket.labels
        }
        
        # Try to add priority - skip if it causes issues
        try:
            # Map priority names to common Jira priority IDs
            priority_map = {
                "Critical": "1",
                "High": "2", 
                "Medium": "3",
                "Low": "4"
            }
            
            if jira_ticket.priority in priority_map:
                issue_data["priority"] = {"id": priority_map[jira_ticket.priority]}
            else:
                # Fallback to name format
                issue_data["priority"] = {"name": jira_ticket.priority}
        except:
            # Skip priority if it causes issues
            logger.warning(f"Skipping priority field due to format issues")
        
        # Only add optional fields if they exist in the project schema
        # Skip components and custom fields for now to avoid field errors
        
        # Create the issue
        created_issue = await jira_service.create_issue(issue_data, user_id)
        
        if not created_issue:
            raise Exception("Jira service returned None - issue creation failed")
        
        # Log the routing decision for analysis
        logger.info(f"Issue created using model: {metadata.get('routing_metadata', {}).get('selected_model')}")
        logger.info(f"Estimated cost: ${metadata.get('routing_metadata', {}).get('estimated_cost', 0):.4f}")
        
        # Return JiraIssue as dictionary
        return {
            "key": created_issue.key,
            "id": created_issue.id,
            "url": created_issue.url,
            "status": created_issue.status,
            "created_at": created_issue.created_at.isoformat(),
            "project_key": project_key,
            "issue_type": jira_ticket.issue_type.value,
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
    
    # Add acceptance criteria if available
    if ticket.acceptance_criteria:
        adf_content["content"].append({
            "type": "heading",
            "attrs": {"level": 2},
            "content": [{"type": "text", "text": "Acceptance Criteria"}]
        })
        
        criteria_list = []
        for criterion in ticket.acceptance_criteria:
            criteria_list.append({
                "type": "listItem",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": criterion}]
                }]
            })
        
        adf_content["content"].append({
            "type": "bulletList",
            "content": criteria_list
        })
    
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

def _format_plain_description(ticket: JiraTicketContent, metadata: Dict[str, Any]) -> str:
    """
    Formats the description as well-structured text for Jira with proper spacing and formatting.
    """
    description_parts = []
    
    # Main description with better formatting
    description_parts.append("h2. Issue Description")
    description_parts.append("")
    description_parts.append(ticket.description)
    description_parts.append("")
    
    # Technical details with code formatting
    if ticket.technical_details:
        description_parts.append("h2. Technical Details")
        description_parts.append("")
        
        # Format technical details nicely
        tech_details = ticket.technical_details
        if isinstance(tech_details, dict):
            if 'stack_trace' in tech_details:
                description_parts.append("*Stack Trace:*")
                description_parts.append("{code}")
                description_parts.append(tech_details['stack_trace'])
                description_parts.append("{code}")
                description_parts.append("")
            
            if 'error_codes' in tech_details:
                description_parts.append("*Error Codes:* " + ", ".join(tech_details['error_codes']))
                description_parts.append("")
            
            if 'affected_files' in tech_details:
                description_parts.append("*Affected Files:*")
                for file in tech_details['affected_files']:
                    description_parts.append(f"• {file}")
                description_parts.append("")
            
            if 'affected_endpoints' in tech_details and tech_details['affected_endpoints']:
                description_parts.append("*Affected Endpoints:*")
                for endpoint in tech_details['affected_endpoints']:
                    description_parts.append(f"• {endpoint}")
                description_parts.append("")
        else:
            description_parts.append("{code}")
            description_parts.append(str(tech_details))
            description_parts.append("{code}")
            description_parts.append("")
    
    # Acceptance criteria with proper numbering
    if ticket.acceptance_criteria:
        description_parts.append("h2. Acceptance Criteria")
        description_parts.append("")
        for i, criterion in enumerate(ticket.acceptance_criteria, 1):
            description_parts.append(f"# {criterion}")
        description_parts.append("")
    
    # Steps to reproduce with proper numbering
    if ticket.steps_to_reproduce:
        description_parts.append("h2. Steps to Reproduce")
        description_parts.append("")
        for i, step in enumerate(ticket.steps_to_reproduce, 1):
            # Clean up step text (remove numbering if already present)
            clean_step = step.strip()
            if clean_step.startswith(f"{i}."):
                clean_step = clean_step[len(f"{i}."):].strip()
            description_parts.append(f"# {clean_step}")
        description_parts.append("")
    
    # Expected vs actual behavior
    if ticket.expected_behavior and ticket.actual_behavior:
        description_parts.append("h3. Expected Behavior")
        description_parts.append("")
        description_parts.append(ticket.expected_behavior)
        description_parts.append("")
        description_parts.append("h3. Actual Behavior")
        description_parts.append("")
        description_parts.append(ticket.actual_behavior)
        description_parts.append("")
    
    # Metadata footer with better formatting
    if metadata.get("routing_metadata"):
        routing = metadata["routing_metadata"]
        description_parts.append("----")
        description_parts.append("")
        confidence = metadata.get('confidence_score', 0)
        model = routing.get('selected_model', 'Unknown')
        cost = routing.get('estimated_cost', 0)
        description_parts.append(f"_Analysis Confidence: {confidence:.1%} | Model: {model} | Cost: ${cost:.4f}_")
    
    # Filter out None values before joining
    clean_parts = [part for part in description_parts if part is not None]
    return "\n".join(clean_parts)

def _format_acceptance_criteria(criteria: list) -> str:
    """
    Formats acceptance criteria for Jira custom field.
    """
    formatted = "Acceptance Criteria:\n"
    for i, criterion in enumerate(criteria, 1):
        formatted += f"{i}. {criterion}\n"
    return formatted
