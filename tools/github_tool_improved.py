"""Improved GitHub tool that works with search-replace edits."""

from github import Github, GithubException
from typing import Dict, Any, List, Optional
from config import Config
import base64
import re

class ImprovedGitHubTool:
    """GitHub tool optimized for search-replace edits."""
    
    def __init__(self):
        """Initialize GitHub client."""
        self.github = Github(Config.GITHUB_TOKEN)
        owner, repo_name = Config.get_github_owner_repo()
        self.repo = self.github.get_repo(f"{owner}/{repo_name}")
        self.default_branch = Config.GITHUB_DEFAULT_BRANCH
    
    def apply_search_replace_edits(self, branch_name: str, 
                                  edits_by_file: Dict[str, List[Dict]], 
                                  commit_message: str) -> bool:
        """Apply search-replace edits to multiple files.
        
        Args:
            branch_name: Target branch
            edits_by_file: {file_path: [{"find": str, "replace": str, "description": str}]}
            commit_message: Commit message
            
        Returns:
            Success status
        """
        if not edits_by_file:
            print("No edits to apply")
            return False
        
        success_count = 0
        for file_path, edits in edits_by_file.items():
            if not edits:
                continue
                
            try:
                print(f"Applying {len(edits)} edits to {file_path}")
                
                # Get current file content
                file_obj = self.repo.get_contents(file_path, ref=branch_name)
                current_content = base64.b64decode(file_obj.content).decode('utf-8')
                
                # Apply all edits
                modified_content = current_content
                changes_made = []
                
                for edit in edits:
                    find_str = edit.get('find', '')
                    replace_str = edit.get('replace', '')
                    description = edit.get('description', 'Applied edit')
                    
                    if find_str in modified_content:
                        count = modified_content.count(find_str)
                        modified_content = modified_content.replace(find_str, replace_str)
                        changes_made.append(f"{description} ({count}x)")
                        print(f"  ✓ {description}")
                    else:
                        print(f"  ✗ Could not find: '{find_str[:50]}...'")
                
                # Update file if changes were made
                if modified_content != current_content:
                    self.repo.update_file(
                        path=file_path,
                        message=f"{commit_message} - {file_path}\n\n" + "\n".join(f"- {c}" for c in changes_made),
                        content=modified_content,
                        sha=file_obj.sha,
                        branch=branch_name
                    )
                    success_count += 1
                    print(f"  Updated {file_path} with {len(changes_made)} changes")
                else:
                    print(f"  No changes applied to {file_path}")
                    
            except Exception as e:
                print(f"  Error updating {file_path}: {e}")
                continue
        
        return success_count > 0
    
    def create_fix_branch(self, issue_key: str, bug_title: str) -> str:
        """Create a new branch for the fix (inherited from original)."""
        clean_title = re.sub(r'[^a-zA-Z0-9-]', '-', bug_title.lower())
        clean_title = re.sub(r'-+', '-', clean_title)[:30]
        branch_name = f"fix/{issue_key.lower()}-{clean_title}"
        
        try:
            base_branch = self.repo.get_branch(self.default_branch)
            self.repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=base_branch.commit.sha
            )
            return branch_name
        except GithubException as e:
            if e.status == 422:  # Branch already exists
                import time
                branch_name = f"{branch_name}-{int(time.time())}"
                self.repo.create_git_ref(
                    ref=f"refs/heads/{branch_name}",
                    sha=base_branch.commit.sha
                )
                return branch_name
            raise
    
    def create_pull_request(self, branch_name: str, issue_key: str,
                          bug_report: Dict[str, Any], 
                          applied_edits: Dict[str, List[Dict]]) -> str:
        """Create PR with detailed change summary."""
        title = f"[{issue_key}] Fix: {bug_report.get('title', 'Bug fix')}"
        
        # Build detailed PR body
        body_parts = [
            f"## 🐛 Fix for {issue_key}",
            f"**Jira:** [{issue_key}](https://{Config.JIRA_BASE_URL}/browse/{issue_key})",
            "",
            "## Problem",
            bug_report.get('description', 'See Jira ticket'),
            "",
            "## Solution",
            "Applied targeted search-and-replace edits:",
            ""
        ]
        
        # List all changes
        for file_path, edits in applied_edits.items():
            body_parts.append(f"### `{file_path}`")
            for edit in edits:
                desc = edit.get('description', 'Change applied')
                body_parts.append(f"- {desc}")
            body_parts.append("")
        
        # Add testing notes
        body_parts.extend([
            "## Testing",
            "- [ ] Visual verification of changes",
            "- [ ] Functionality still works as expected",
            "- [ ] No unintended side effects",
            "",
            "---",
            "*This PR was generated using the improved search-and-replace strategy*"
        ])
        
        body = "\n".join(body_parts)
        
        try:
            pr = self.repo.create_pull(
                title=title,
                body=body,
                head=branch_name,
                base=self.default_branch
            )
            
            # Add labels
            try:
                pr.add_to_labels('bug', 'auto-generated', 'search-replace')
            except:
                pass
            
            return pr.html_url
        except Exception as e:
            print(f"Error creating PR: {e}")
            raise
