"""
GitHub Service

Handles all GitHub API interactions including file access, code search,
branch management, and pull request creation.
"""

import os
import base64
from typing import List, Dict, Any, Optional
from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile

from models.ticket import CodeFile, GitHubPR
from utils.logger import logger

class GitHubService:
  """Service for GitHub API operations."""
  
  def __init__(self):
    """Initialize GitHub client with API token."""
    self.token = os.getenv("GITHUB_TOKEN")
    if not self.token:
      print("Warning: GITHUB_TOKEN not set - GitHub operations will be disabled")
      self.client = None
    else:
      self.client = Github(self.token)
    
    self.client = Github(self.token)
    
    # Handle both formats: GITHUB_REPO=owner/repo or separate GITHUB_REPO_OWNER/NAME
    github_repo = os.getenv("GITHUB_REPO")
    if github_repo and "/" in github_repo:
      self.repo_owner, self.repo_name = github_repo.split("/", 1)
    else:
      self.repo_owner = os.getenv("GITHUB_REPO_OWNER")
      self.repo_name = os.getenv("GITHUB_REPO_NAME")
    
    if not self.repo_owner or not self.repo_name:
      raise ValueError("GITHUB_REPO (format: owner/repo) or GITHUB_REPO_OWNER and GITHUB_REPO_NAME environment variables are required")
    
    if self.client:
      try:
        self.repo = self.client.get_repo(f"{self.repo_owner}/{self.repo_name}")
        logger.info(f"GitHub service initialized for {self.repo_owner}/{self.repo_name}")
      except Exception as e:
        print(f"Warning: Could not initialize GitHub repo: {e}")
        self.repo = None
    else:
      self.repo = None
  
  async def search_files(self, queries: List[str], extensions: List[str] = None) -> List[CodeFile]:
    """
    Search for files in the repository based on queries.
    
    Args:
      queries: Search terms to look for
      extensions: File extensions to filter by (e.g., ['.js', '.py'])
    
    Returns:
      List of CodeFile objects with file information
    """
    logger.info(f"Searching GitHub repo for queries: {queries}")
    
    if extensions is None:
      extensions = ['.js', '.ts', '.py', '.java', '.go', '.rb', '.php']
    
    found_files = []
    
    try:
      # Use GitHub's code search API
      for query in queries:
        # Search in file contents
        search_query = f"{query} repo:{self.repo_owner}/{self.repo_name}"
        
        try:
          search_results = self.client.search_code(search_query)
          
          for result in search_results[:10]:  # Limit to top 10 results per query
            file_path = result.path
            
            # Filter by extension
            if any(file_path.endswith(ext) for ext in extensions):
              # Get file content
              content = await self._get_file_content(file_path)
              
              found_files.append(CodeFile(
                path=file_path,
                reason=f"Contains '{query}' - found in code search",
                current_content=content
              ))
        
        except Exception as e:
          logger.warning(f"Search failed for query '{query}': {str(e)}")
          continue
      
      # Remove duplicates based on file path
      unique_files = {}
      for file in found_files:
        if file.path not in unique_files:
          unique_files[file.path] = file
      
      result_files = list(unique_files.values())
      logger.info(f"Found {len(result_files)} unique files")
      return result_files
    
    except Exception as e:
      logger.error(f"GitHub file search failed: {str(e)}")
      # Fallback to common file patterns
      return await self._fallback_file_search(queries, extensions)
  
  async def _get_file_content(self, file_path: str) -> str:
    """
    Get the content of a specific file from the repository.
    
    Args:
      file_path: Path to the file in the repository
    
    Returns:
      File content as string
    """
    try:
      file_content = self.repo.get_contents(file_path)
      
      if isinstance(file_content, list):
        # If it's a directory, return empty
        return ""
      
      # Decode base64 content
      content = base64.b64decode(file_content.content).decode('utf-8')
      return content
    
    except Exception as e:
      logger.warning(f"Failed to get content for {file_path}: {str(e)}")
      return ""
  
  async def _fallback_file_search(self, queries: List[str], extensions: List[str]) -> List[CodeFile]:
    """
    Fallback file search using repository tree traversal.
    
    Args:
      queries: Search terms
      extensions: File extensions to include
    
    Returns:
      List of CodeFile objects
    """
    logger.info("Using fallback file search method")
    
    try:
      # Get repository tree
      tree = self.repo.get_git_tree("HEAD", recursive=True)
      
      matching_files = []
      
      for item in tree.tree:
        if item.type == "blob":  # It's a file
          file_path = item.path
          
          # Check if file extension matches
          if any(file_path.endswith(ext) for ext in extensions):
            # Check if any query matches the file path
            file_path_lower = file_path.lower()
            
            for query in queries:
              if query.lower() in file_path_lower:
                content = await self._get_file_content(file_path)
                
                matching_files.append(CodeFile(
                  path=file_path,
                  reason=f"File path contains '{query}'",
                  current_content=content
                ))
                break  # Don't add the same file multiple times
      
      logger.info(f"Fallback search found {len(matching_files)} files")
      return matching_files[:20]  # Limit to 20 files
    
    except Exception as e:
      logger.error(f"Fallback file search failed: {str(e)}")
      return []
  
  async def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
    """
    Create a new branch from the base branch.
    
    Args:
      branch_name: Name of the new branch
      base_branch: Base branch to create from
    
    Returns:
      True if successful, False otherwise
    """
    try:
      # Get the base branch reference
      base_ref = self.repo.get_git_ref(f"heads/{base_branch}")
      base_sha = base_ref.object.sha
      
      # Create new branch
      self.repo.create_git_ref(f"refs/heads/{branch_name}", base_sha)
      
      logger.info(f"Created branch '{branch_name}' from '{base_branch}'")
      return True
    
    except Exception as e:
      logger.error(f"Failed to create branch '{branch_name}': {str(e)}")
      return False
  
  async def create_file(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
    """Create a new file in the repository."""
    try:
      self.repo.create_file(
        path=file_path,
        message=commit_message,
        content=content,
        branch=branch_name
      )
      logger.info(f"Created file '{file_path}' in branch '{branch_name}'")
      return True
    except Exception as e:
      logger.error(f"Failed to create file '{file_path}': {str(e)}")
      return False
  
  async def update_file(self, branch_name: str, file_path: str, content: str, commit_message: str) -> bool:
    """Update an existing file in the repository."""
    try:
      # Get existing file to get its SHA
      existing_file = self.repo.get_contents(file_path, ref=branch_name)
      
      self.repo.update_file(
        path=file_path,
        message=commit_message,
        content=content,
        sha=existing_file.sha,
        branch=branch_name
      )
      logger.info(f"Updated file '{file_path}' in branch '{branch_name}'")
      return True
    except Exception as e:
      logger.error(f"Failed to update file '{file_path}': {str(e)}")
      return False
  
  async def delete_file(self, branch_name: str, file_path: str, commit_message: str) -> bool:
    """Delete a file from the repository."""
    try:
      # Get existing file to get its SHA
      existing_file = self.repo.get_contents(file_path, ref=branch_name)
      
      self.repo.delete_file(
        path=file_path,
        message=commit_message,
        sha=existing_file.sha,
        branch=branch_name
      )
      logger.info(f"Deleted file '{file_path}' from branch '{branch_name}'")
      return True
    except Exception as e:
      logger.error(f"Failed to delete file '{file_path}': {str(e)}")
      return False
  
  async def apply_changes(self, branch_name: str, file_changes: List[Dict[str, str]], commit_message: str) -> bool:
    """
    Apply file changes to a branch.
    
    Args:
      branch_name: Target branch name
      file_changes: List of dicts with 'path', 'old_content', 'new_content' keys
      commit_message: Commit message
    
    Returns:
      True if successful, False otherwise
    """
    try:
      # Get branch reference
      branch_ref = self.repo.get_git_ref(f"heads/{branch_name}")
      
      for change in file_changes:
        file_path = change['path']
        old_content = change.get('old_content', '')
        new_content = change.get('new_content', '')
        
        try:
          # Try to get existing file
          existing_file = self.repo.get_contents(file_path, ref=branch_name)
          current_content = existing_file.decoded_content.decode('utf-8')
          
          # Apply targeted replacement if old_content is specified
          if old_content and old_content in current_content:
            updated_content = current_content.replace(old_content, new_content)
            logger.info(f"Applying targeted change to {file_path}: replacing {len(old_content)} chars with {len(new_content)} chars")
          else:
            # Fallback to full replacement (for backward compatibility)
            updated_content = new_content
            logger.warning(f"Could not find old_content in {file_path}, replacing entire file")
          
          # Update existing file
          self.repo.update_file(
            path=file_path,
            message=commit_message,
            content=updated_content,
            sha=existing_file.sha,
            branch=branch_name
          )
          
        except Exception:
          # File doesn't exist, create it
          self.repo.create_file(
            path=file_path,
            message=commit_message,
            content=new_content,
            branch=branch_name
          )
        
        logger.info(f"Updated file '{file_path}' in branch '{branch_name}'")
      
      return True
    
    except Exception as e:
      logger.error(f"Failed to apply changes to branch '{branch_name}': {str(e)}")
      return False
  
  async def create_pull_request(self, branch_name: str, title: str, body: str, base_branch: str = "main") -> Optional[GitHubPR]:
    """
    Create a pull request.
    
    Args:
      branch_name: Source branch name
      title: PR title
      body: PR description
      base_branch: Target branch
    
    Returns:
      GitHubPR object if successful, None otherwise
    """
    try:
      pr = self.repo.create_pull(
        title=title,
        body=body,
        head=branch_name,
        base=base_branch,
        draft=True  # Create as draft initially
      )
      
      logger.info(f"Created pull request #{pr.number}: {title}")
      
      return GitHubPR(
        number=pr.number,
        url=pr.html_url,
        branch=branch_name,
        title=title
      )
    
    except Exception as e:
      logger.error(f"Failed to create pull request: {str(e)}")
      return None

# Global service instance (lazy initialization)
github_service = None

def get_github_service():
  """Get or create GitHub service instance."""
  global github_service
  if github_service is None:
    github_service = GitHubService()
  return github_service
