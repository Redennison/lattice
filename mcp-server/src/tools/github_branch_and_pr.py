"""
GitHub Branch and PR Tool

This MCP tool creates branches, applies code changes from fix plan, and opens
pull requests with links to Jira issues.
"""

from typing import Dict, Any
from datetime import datetime

from models.schemas import FixPlan, PullRequest, CodeChange
from services.github_service import GitHubService
from utils.logger import logger

async def github_branch_and_pr_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a branch, applies fixes from plan, and opens a pull request.
    
    Args:
        arguments: Contains fix_plan from plan_fix and jira_issue from jira_create_issue
        
    Returns:
        PullRequest details as dictionary
    """
    logger.info("Creating GitHub branch and PR...")
    
    # Parse arguments
    fix_plan_data = arguments.get("fix_plan", {})
    jira_issue_data = arguments.get("jira_issue", {})
    base_branch = arguments.get("base_branch", "main")
    repo_url = arguments.get("repo_url", "")
    
    if not fix_plan_data:
        raise ValueError("fix_plan is required")
    
    # Extract data from fix plan
    changes = [CodeChange(**c) for c in fix_plan_data.get("changes", [])]
    summary = fix_plan_data.get("summary", "Automated fix")
    root_cause = fix_plan_data.get("root_cause", "")
    test_plan = fix_plan_data.get("test_plan", [])
    risks = fix_plan_data.get("risks", [])
    
    # Extract Jira info
    jira_key = jira_issue_data.get("key", "")
    jira_url = jira_issue_data.get("url", "")
    
    # Initialize GitHub service
    github_service = GitHubService()
    
    # Generate branch name
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_suffix = jira_key if jira_key else "fix"
    branch_name = f"auto/{branch_suffix}-{timestamp}"
    
    # Create branch
    branch_created = await github_service.create_branch(branch_name, base_branch)
    if not branch_created:
        raise Exception(f"Failed to create branch {branch_name}")
    
    logger.info(f"Created branch: {branch_name}")
    
    # Apply code changes
    if changes:
        for change in changes:
            try:
                if change.change_type == "create":
                    await github_service.create_file(
                        branch_name,
                        change.file_path,
                        change.new_content,
                        f"Create {change.file_path}: {change.description}"
                    )
                elif change.change_type == "delete":
                    await github_service.delete_file(
                        branch_name,
                        change.file_path,
                        f"Delete {change.file_path}: {change.description}"
                    )
                else:  # modify
                    # Use apply_changes for targeted replacement
                    file_changes = [{
                        'path': change.file_path,
                        'old_content': change.old_content,
                        'new_content': change.new_content
                    }]
                    await github_service.apply_changes(
                        branch_name,
                        file_changes,
                        f"Update {change.file_path}: {change.description}"
                    )
                
                logger.info(f"Applied change to {change.file_path}")
                
            except Exception as e:
                logger.error(f"Failed to apply change to {change.file_path}: {e}")
                # Continue with other changes
    
    # Create pull request
    pr_title = _generate_pr_title(jira_key, summary)
    pr_body = _generate_pr_body(
        summary=summary,
        root_cause=root_cause,
        changes=changes,
        test_plan=test_plan,
        risks=risks,
        jira_key=jira_key,
        jira_url=jira_url
    )
    
    pr_data = await github_service.create_pull_request(
        branch_name=branch_name,
        title=pr_title,
        body=pr_body,
        base_branch=base_branch
    )
    
    if not pr_data:
        raise Exception("Failed to create pull request")
    
    logger.info(f"Created PR #{pr_data.number}: {pr_title}")
    
    # Return PullRequest as dictionary
    return {
        "pr_number": pr_data.number,
        "pr_url": pr_data.url,
        "branch_name": branch_name,
        "base_branch": base_branch,
        "title": pr_title,
        "body": pr_body,
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "jira_key": jira_key
    }

def _generate_pr_title(jira_key: str, summary: str) -> str:
    """
    Generates a PR title with Jira key if available.
    """
    if jira_key:
        return f"[{jira_key}] {summary[:80]}"
    return summary[:100]

def _generate_pr_body(
    summary: str,
    root_cause: str,
    changes: list,
    test_plan: list,
    risks: list,
    jira_key: str = "",
    jira_url: str = ""
) -> str:
    """
    Generates a comprehensive PR description.
    """
    sections = []
    
    # Jira link
    if jira_key and jira_url:
        sections.append("## 🎫 Jira Issue")
        sections.append(f"[{jira_key}]({jira_url})")
        sections.append("")
    
    # Summary
    sections.append("## 📝 Summary")
    sections.append(summary)
    sections.append("")
    
    # Root cause
    if root_cause:
        sections.append("## 🔍 Root Cause")
        sections.append(root_cause)
        sections.append("")
    
    # Changes
    if changes:
        sections.append("## 🔧 Changes Made")
        for change in changes:
            emoji = "➕" if change.change_type == "create" else "✏️" if change.change_type == "modify" else "❌"
            sections.append(f"{emoji} **{change.file_path}**")
            if change.description:
                sections.append(f"   - {change.description}")
        sections.append("")
    
    # Test plan
    if test_plan:
        sections.append("## 🧪 Test Plan")
        for step in test_plan:
            sections.append(f"- [ ] {step}")
        sections.append("")
    
    # Risks
    if risks:
        sections.append("## ⚠️ Risks")
        for risk in risks:
            sections.append(f"- {risk}")
        sections.append("")
    
    # Footer
    sections.append("---")
    sections.append("*This PR was automatically generated by Lattice*")
    sections.append(f"*Generated at: {datetime.now().isoformat()}*")
    
    return "\n".join(sections)
