"""
Data schemas for MCP tool communication.

These schemas define the structure of data passed between tools in the Lattice pipeline.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class Severity(Enum):
    """Issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IssueType(Enum):
    """Jira issue types"""
    BUG = "Bug"
    TASK = "Task"
    STORY = "Story"
    EPIC = "Epic"

@dataclass
class SlackContext:
    """
    Raw Slack conversation context passed to analyze_request tool.
    """
    conversation: str  # Full conversation text
    thread_messages: List[Dict[str, Any]]  # Thread messages if applicable
    channel_id: str
    user_id: str
    timestamp: str
    attachments: List[Dict[str, Any]] = None  # Images, files, etc.
    
@dataclass
class ParsedSlackInfo:
    """
    Information parsed from Slack by the initial LLM.
    """
    initial_summary: str  # Quick summary of the issue
    detected_keywords: List[str]  # Key technical terms found
    mentioned_files: List[str]  # Files mentioned in conversation
    error_messages: List[str]  # Error messages found
    user_intent: str  # What the user is trying to achieve
    urgency_indicators: List[str]  # Words indicating urgency
    
@dataclass
class AnalysisRequest:
    """
    Input to analyze_request tool from MCP.
    """
    slack_context: SlackContext
    parsed_info: ParsedSlackInfo
    severity: Severity = Severity.MEDIUM
    
@dataclass
class JiraTicketContent:
    """
    Formatted Jira ticket content from Deimos router.
    """
    title: str
    description: str  # Rich text/markdown description
    issue_type: IssueType
    priority: str  # High/Medium/Low
    labels: List[str]
    components: List[str]
    acceptance_criteria: List[str]
    steps_to_reproduce: Optional[List[str]] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    technical_details: Optional[Dict[str, Any]] = None
    affected_versions: Optional[List[str]] = None
    fix_versions: Optional[List[str]] = None
    
@dataclass
class AnalysisResult:
    """
    Output from analyze_request tool containing Jira ticket content and metadata.
    """
    jira_ticket: JiraTicketContent
    code_queries: List[str]  # Search queries for finding relevant code
    confidence_score: float  # 0.0 to 1.0
    routing_metadata: Dict[str, Any]  # Deimos routing decision details
    suggested_assignee: Optional[str] = None
    estimated_effort: Optional[str] = None  # T-shirt sizing: S/M/L/XL
    
@dataclass
class JiraIssue:
    """
    Created Jira issue details.
    """
    key: str  # e.g., "PROJ-123"
    id: str
    url: str
    status: str
    created_at: datetime
    
@dataclass
class CodeChange:
    """
    Represents a single code change to be made.
    """
    file_path: str
    change_type: str  # 'modify', 'create', 'delete'
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str = ""
    
@dataclass
class FixPlan:
    """
    Output from plan_fix tool.
    """
    summary: str  # Summary of the fix approach
    root_cause: str  # Identified root cause
    changes: List[CodeChange]  # List of code changes to make
    test_plan: List[str]  # How to test the fix
    risks: List[str]  # Potential risks or side effects
    dependencies: List[str]  # External dependencies or requirements
    
@dataclass
class PullRequest:
    """
    Created pull request details.
    """
    pr_number: int
    pr_url: str
    branch_name: str
    base_branch: str
    title: str
    body: str
    status: str
    created_at: datetime
