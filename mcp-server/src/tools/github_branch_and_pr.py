"""
GitHub Branch and PR Tool

This MCP tool creates branches, applies code changes, and opens pull requests.
"""

import os
from typing import Dict, Any
from datetime import datetime
from models.ticket import FixPlan, JiraIssue, GitHubPR
from services.github_service import github_service
from utils.logger import logger

async def github_branch_and_pr_tool(arguments: Dict[str, Any]) -> GitHubPR:
  """
  Create a branch, apply fixes, and open a pull request.
  
  Args:
    arguments: Contains fix_plan, jira_issue, and optional base_branch
    
  Returns:
    GitHubPR with pull request details
  """
  logger.info("Creating GitHub branch and PR...")
  
  # Parse arguments
  fix_plan_data = arguments.get("fix_plan", {})
  jira_issue_data = arguments.get("jira_issue", {})
  base_branch = arguments.get("base_branch", "main")
  
  if not fix_plan_data:
    raise ValueError("fix_plan is required")
  
  # Convert to models
  try:
    fix_plan = FixPlan(**fix_plan_data)
    jira_issue = JiraIssue(**jira_issue_data) if jira_issue_data else None
  except Exception as e:
    logger.error(f"Invalid input format: {str(e)}")
    raise ValueError(f"Invalid input: {str(e)}")
  
  # Generate branch name
  timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
  jira_key = jira_issue.key if jira_issue else "auto-fix"
  branch_name = f"auto/{jira_key}-{timestamp}"
  
  # Create branch
  success = await github_service.create_branch(branch_name, base_branch)
  if not success:
    raise Exception(f"Failed to create branch {branch_name}")
  
  # Apply code changes
  if fix_plan.diffs:
    file_changes = []
    
    for diff in fix_plan.diffs:
      # For hackathon demo, we'll apply simple changes
      # In production, this would parse git diffs and apply them properly
      new_content = _apply_diff_to_content(diff)
      
      file_changes.append({
        "path": diff.path,
        "content": new_content
      })
    
    success = await github_service.apply_changes(
      branch_name, 
      file_changes, 
      fix_plan.commit_message
    )
    
    if not success:
      raise Exception("Failed to apply code changes")
  
  # Create pull request
  pr_title = f"[{jira_issue.key}] {fix_plan.commit_message}" if jira_issue else fix_plan.commit_message
  pr_body = _build_pr_description(fix_plan, jira_issue)
  
  github_pr = await github_service.create_pull_request(
    branch_name,
    pr_title,
    pr_body,
    base_branch
  )
  
  if not github_pr:
    raise Exception("Failed to create pull request")
  
  logger.info(f"Created PR #{github_pr.number}: {pr_title}")
  return github_pr

def _apply_diff_to_content(diff) -> str:
  """
  Apply a diff to generate new file content.
  For hackathon demo, this creates simple fixed content.
  
  Args:
    diff: CodeDiff object
    
  Returns:
    New file content
  """
  # Mock implementation for demo
  # In production, this would parse the git diff and apply changes
  
  if "cart" in diff.path.lower():
    return """const express = require('express');
const CartService = require('../services/cart');

const router = express.Router();

router.post('/cart', async (req, res) => {
  try {
    const { cartId, items } = req.body;
    
    // Added null check for cartId
    if (!cartId) {
      return res.status(400).json({ error: 'cartId is required' });
    }
    
    const result = await CartService.updateCart(cartId, items);
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;"""
  
  # Default content for other files
  return f"// Fixed content for {diff.path}\n// {diff.description}\n"

def _build_pr_description(fix_plan: FixPlan, jira_issue: JiraIssue = None) -> str:
  """
  Build pull request description.
  
  Args:
    fix_plan: Fix plan with changes
    jira_issue: Optional Jira issue
    
  Returns:
    Formatted PR description
  """
  description = []
  
  # Link to Jira issue
  if jira_issue:
    description.append(f"## 🎫 Related Issue")
    description.append(f"Fixes [{jira_issue.key}]({jira_issue.url})")
    description.append("")
  
  # Changes summary
  description.append("## 🔧 Changes")
  for diff in fix_plan.diffs:
    description.append(f"- **{diff.path}**: {diff.description}")
  description.append("")
  
  # Implementation checklist
  description.append("## ✅ Checklist")
  for item in fix_plan.checklist:
    description.append(f"- [ ] {item}")
  description.append("")
  
  # Metadata
  description.append("## 📊 Metadata")
  description.append(f"- **Confidence**: {fix_plan.confidence:.1%}")
  description.append(f"- **Estimated Effort**: {fix_plan.estimated_effort}")
  description.append(f"- **Auto-generated**: Yes")
  
  return "\n".join(description)
