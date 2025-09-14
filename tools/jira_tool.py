"""Jira integration tool for creating and managing tickets."""

from jira import JIRA
from typing import Dict, Any, Optional, List
from config import Config
import re

class JiraTool:
    """Tool for interacting with Jira."""
    
    def __init__(self):
        """Initialize Jira client."""
        self.jira = JIRA(
            server=f"https://{Config.JIRA_BASE_URL}",
            basic_auth=(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        )
        self.project_key = Config.JIRA_PROJECT_KEY
    
    def create_ticket(self, bug_report: Dict[str, Any], pr_url: Optional[str] = None) -> str:
        """Create Jira ticket from bug report.
        
        Args:
            bug_report: Structured bug report data
            pr_url: Optional PR URL to link
            
        Returns:
            Created ticket key (e.g., CCS-123)
        """
        # Map severity to Jira priority
        priority_map = {
            "Critical": "Highest",
            "High": "High",
            "Medium": "Medium",
            "Low": "Low"
        }
        
        # Build description
        description = self._format_description(bug_report, pr_url)
        
        # Create issue
        issue_dict = {
            'project': {'key': self.project_key},
            'summary': bug_report.get('title', 'Bug Report from Slack'),
            'description': description,
            'issuetype': {'name': 'Bug'},
            'priority': {'name': priority_map.get(bug_report.get('severity', 'Medium'), 'Medium')}
        }
        
        # Add labels for affected components
        labels = []
        for component in bug_report.get('affected_components', []):
            # Clean component name for label
            label = re.sub(r'[^a-zA-Z0-9_-]', '_', component)
            if label:
                labels.append(label)
        
        if labels:
            issue_dict['labels'] = labels
        
        try:
            new_issue = self.jira.create_issue(fields=issue_dict)
            
            # Add PR link as comment if provided
            if pr_url:
                self.add_comment(new_issue.key, f"🔧 Pull Request: {pr_url}")
            
            return new_issue.key
            
        except Exception as e:
            print(f"Error creating Jira ticket: {e}")
            raise
    
    def _format_description(self, bug_report: Dict[str, Any], pr_url: Optional[str] = None) -> str:
        """Format bug report into Jira description.
        
        Args:
            bug_report: Structured bug report
            pr_url: Optional PR URL
            
        Returns:
            Formatted description text
        """
        sections = []
        
        # Description
        if bug_report.get('description'):
            sections.append(f"h3. Description\n{bug_report['description']}")
        
        # Steps to Reproduce
        if bug_report.get('steps_to_reproduce'):
            sections.append(f"h3. Steps to Reproduce\n{bug_report['steps_to_reproduce']}")
        
        # Expected vs Actual
        if bug_report.get('expected_behavior'):
            sections.append(f"h3. Expected Behavior\n{bug_report['expected_behavior']}")
        
        if bug_report.get('actual_behavior'):
            sections.append(f"h3. Actual Behavior\n{bug_report['actual_behavior']}")
        
        # Affected Components
        if bug_report.get('affected_components'):
            components = '\n'.join([f"* {c}" for c in bug_report['affected_components']])
            sections.append(f"h3. Affected Components\n{components}")
        
        # Additional Context
        if bug_report.get('additional_context'):
            # Truncate if too long
            context = bug_report['additional_context']
            if len(context) > 2000:
                context = context[:2000] + "...\n[Truncated]"
            sections.append(f"h3. Additional Context\n{code}{context}{code}")
        
        # PR Link
        if pr_url:
            sections.append(f"h3. Pull Request\n[GitHub PR|{pr_url}]")
        
        return "\n\n".join(sections)
    
    def add_comment(self, issue_key: str, comment: str):
        """Add comment to existing issue.
        
        Args:
            issue_key: Jira issue key (e.g., CCS-123)
            comment: Comment text
        """
        try:
            issue = self.jira.issue(issue_key)
            self.jira.add_comment(issue, comment)
        except Exception as e:
            print(f"Error adding comment to {issue_key}: {e}")
    
    def update_issue_with_pr(self, issue_key: str, pr_url: str):
        """Update issue with PR link.
        
        Args:
            issue_key: Jira issue key
            pr_url: GitHub PR URL
        """
        self.add_comment(issue_key, f"🔧 Pull Request created: {pr_url}\nStatus: Ready for Review")
    
    def find_similar_issues(self, title: str, limit: int = 5) -> List[Dict[str, str]]:
        """Find similar existing issues.
        
        Args:
            title: Issue title to search
            limit: Maximum results
            
        Returns:
            List of similar issues
        """
        # Search using JQL
        jql = f'project = {self.project_key} AND summary ~ "{title}" ORDER BY created DESC'
        
        try:
            issues = self.jira.search_issues(jql, maxResults=limit)
            
            return [
                {
                    'key': issue.key,
                    'summary': issue.fields.summary,
                    'status': issue.fields.status.name,
                    'created': str(issue.fields.created)
                }
                for issue in issues
            ]
        except:
            return []

# Use {code} blocks for code/logs in Jira
code = "{code}"
