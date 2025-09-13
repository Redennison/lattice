from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class SeverityLevel(str, Enum):
  """Ticket severity levels"""
  HIGH = "high"
  MEDIUM = "medium"
  LOW = "low"

class TicketRequest(BaseModel):
  """Input data from Slack app for ticket analysis"""
  title: str = Field(..., description="Ticket title")
  description: str = Field(..., description="Detailed ticket description")
  severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM)
  labels: List[str] = Field(default_factory=list, description="Ticket labels")
  user_id: str = Field(..., description="Slack user ID who created ticket")
  channel_id: str = Field(..., description="Slack channel ID")
  autofix_enabled: bool = Field(default=True, description="Whether to attempt auto-fix")
  attachments: List[str] = Field(default_factory=list, description="File attachments or screenshots")

class AcceptanceCriteria(BaseModel):
  """Acceptance criteria for the ticket"""
  description: str
  completed: bool = False

class AnalysisResult(BaseModel):
  """Result of ticket analysis"""
  title: str = Field(..., description="Processed ticket title")
  summary: str = Field(..., description="Clear summary for Jira")
  labels: List[str] = Field(default_factory=list)
  acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list)
  code_queries: List[str] = Field(default_factory=list, description="Search queries for code analysis")
  confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence score")
  issue_type: str = Field(default="Bug", description="Jira issue type")
  priority: str = Field(default="Medium")

class CodeFile(BaseModel):
  """Information about a code file to modify"""
  path: str = Field(..., description="File path relative to repo root")
  reason: str = Field(..., description="Why this file needs changes")
  current_content: Optional[str] = Field(None, description="Current file content")

class CodeDiff(BaseModel):
  """A code change diff"""
  path: str = Field(..., description="File path")
  patch: str = Field(..., description="Git-style diff patch")
  description: str = Field(..., description="Human-readable change description")

class FixPlan(BaseModel):
  """Plan for fixing the issue"""
  files: List[CodeFile] = Field(default_factory=list, description="Files to analyze/modify")
  diffs: List[CodeDiff] = Field(default_factory=list, description="Proposed code changes")
  commit_message: str = Field(..., description="Git commit message")
  checklist: List[str] = Field(default_factory=list, description="Implementation checklist")
  confidence: float = Field(..., ge=0.0, le=1.0, description="Fix confidence score")
  estimated_effort: str = Field(default="Medium", description="Estimated implementation effort")

class JiraIssue(BaseModel):
  """Jira issue creation result"""
  key: str = Field(..., description="Jira issue key (e.g., PROJ-123)")
  url: str = Field(..., description="Jira issue URL")
  id: str = Field(..., description="Jira issue ID")

class GitHubPR(BaseModel):
  """GitHub pull request result"""
  number: int = Field(..., description="PR number")
  url: str = Field(..., description="PR URL")
  branch: str = Field(..., description="Branch name")
  title: str = Field(..., description="PR title")

class WorkflowResult(BaseModel):
  """Complete workflow execution result"""
  analysis: AnalysisResult
  jira_issue: Optional[JiraIssue] = None
  fix_plan: Optional[FixPlan] = None
  github_pr: Optional[GitHubPR] = None
  success: bool = Field(default=True)
  error_message: Optional[str] = None
  execution_time: float = Field(..., description="Total execution time in seconds")
