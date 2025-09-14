"""MCP Server for handling Slack requests and orchestrating tools."""

import asyncio
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from services.cohere_service import CohereService
from services.deimos_service import DeimosService
from tools.jira_tool import JiraTool
from tools.github_tool import GitHubTool
from config import Config

class MCPServer:
    """Main MCP server for processing bug reports and creating fixes."""
    
    def __init__(self):
        """Initialize MCP server with all services and tools."""
        self.cohere = CohereService()
        self.deimos = DeimosService()
        self.jira = JiraTool()
        self.github = GitHubTool()
        
        # Store active workflows
        self.active_workflows = {}
    
    async def process_slack_conversation(self, 
                                        conversation: List[Dict[str, str]], 
                                        channel_id: str,
                                        thread_ts: str) -> Dict[str, Any]:
        """Process Slack conversation through complete workflow.
        
        Args:
            conversation: List of Slack messages
            channel_id: Slack channel ID
            thread_ts: Thread timestamp
            
        Returns:
            Workflow result with status and details
        """
        workflow_id = f"{channel_id}_{thread_ts}"
        
        print(f"\n{'='*60}")
        print(f"MCP SERVER: Starting workflow {workflow_id}")
        print(f"Conversation: {conversation}")
        print(f"{'='*60}\n")
        
        try:
            # Initialize workflow tracking
            self.active_workflows[workflow_id] = {
                'status': 'started',
                'started_at': datetime.now().isoformat(),
                'steps': []
            }
            
            # Step 1: Parse bug report from conversation
            print(f"🔍 Parsing bug report from {len(conversation)} messages...")
            self._update_workflow(workflow_id, 'parsing_bug_report')
            
            # Route task to appropriate model
            model = self.deimos.route_task('parse_bug_report', 
                                          complexity='medium' if len(conversation) > 20 else 'low')
            print(f"Selected model for parsing: {model}")
            
            try:
                print("Calling cohere.parse_bug_report...")
                bug_report = self.cohere.parse_bug_report(conversation)
                print(f"Bug report parsed: {bug_report}")
            except Exception as parse_error:
                print(f"ERROR in parse_bug_report: {parse_error}")
                import traceback
                traceback.print_exc()
                raise
            
            if not bug_report or not bug_report.get('title'):
                raise ValueError("Failed to parse bug report from conversation")
            
            self._update_workflow(workflow_id, 'bug_report_parsed', {'bug_title': bug_report['title']})
            
            # Step 2: Check for duplicate issues
            print(f"🔎 Checking for duplicate issues...")
            similar_issues = self.jira.find_similar_issues(bug_report['title'])
            
            if similar_issues:
                print(f"⚠️ Found {len(similar_issues)} similar issues")
                # You might want to handle duplicates differently
            
            # Step 3: Get code context from GitHub
            print(f"📂 Analyzing codebase context...")
            self._update_workflow(workflow_id, 'analyzing_codebase')
            
            # Extract keywords from bug report for code search
            keywords = self._extract_keywords(bug_report)
            # Add file names from affected_components if they look like files
            if isinstance(bug_report.get('affected_components'), str):
                keywords.append(bug_report['affected_components'])
            elif isinstance(bug_report.get('affected_components'), list):
                keywords.extend(bug_report['affected_components'])
            print(f"Extracted keywords: {keywords}")
            
            # Get more files with complete content
            relevant_files = self.github.get_relevant_files(keywords, max_files=5)
            print(f"Found {len(relevant_files)} relevant files")
            
            # Get specific context for affected components
            try:
                code_context = self.github.analyze_codebase_context(
                    bug_report.get('affected_components', [])
                )
            except Exception as e:
                print(f"Error in analyze_codebase_context: {e}")
                import traceback
                traceback.print_exc()
                code_context = ""
            
            # Add COMPLETE file content for most relevant files
            if relevant_files:
                try:
                    # Get complete content of most relevant files
                    file_contexts = []
                    for f in relevant_files[:3]:  # Top 3 most relevant
                        print(f"Adding complete file: {f['path']} ({len(f.get('content', ''))} chars)")
                        file_contexts.append(f"=== COMPLETE FILE: {f['path']} ===\n{f.get('content', '')}")
                    
                    code_context = "\n\n".join(file_contexts)
                    print(f"Total code context length: {len(code_context)} characters")
                except Exception as e:
                    print(f"Error building file contexts: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Step 4: Two-pass code fix generation
            print(f"🔧 Locating change target...")
            self._update_workflow(workflow_id, 'locating_target')
            
            # Pass A: Locate exact change location using Deimos Router
            print(f"🎯 Using Deimos Router for locating change target...")
            location = self._locate_with_deimos(bug_report, code_context)
            
            if not location or location.get('confidence', 0) < 0.6 or not location.get('targets'):
                print(f"⚠️ Could not locate change target with confidence (got {location.get('confidence', 0)})")
                fix = None
            else:
                print(f"📍 Located target with confidence {location['confidence']}")
                
                # Pass B: Generate minimal patch
                print(f"🔧 Generating minimal patch...")
                self._update_workflow(workflow_id, 'generating_patch')
                
                # Get the specific code slice for the target
                target = location['targets'][0]
                target_file = next((f for f in relevant_files if f['path'] == target['path']), None)
                
                # If file not in context, try to fetch it directly
                if not target_file and target.get('path'):
                    print(f"📥 Fetching target file: {target['path']}")
                    try:
                        fetched = self.github.get_file_content(target['path'])
                        if fetched:
                            target_file = {'path': target['path'], 'content': fetched}
                            relevant_files.append(target_file)
                    except Exception as e:
                        print(f"Failed to fetch file: {e}")
                
                if target_file:
                    print(f"🎯 Using Deimos Router for generating patch...")
                    fix = self._generate_patch_with_deimos(bug_report, target_file['content'], location)
                    
                    # Check confidence threshold
                    if fix.get('confidence', 0) < 0.6:
                        print(f"⚠️ Patch confidence too low: {fix.get('confidence', 0)}")
                        fix = None
                else:
                    print(f"⚠️ Target file not found in context or repository")
                    fix = None
            
            if not fix:
                fix = {
                    'root_cause': 'Manual analysis required',
                    'fix_description': 'This issue requires manual investigation',
                    'code_changes': [],
                    'testing_notes': 'Manual testing required'
                }
            
            self._update_workflow(workflow_id, 'fix_generated', {'files_to_change': len(fix.get('code_changes', []))})
            
            # Step 5: Create Jira ticket
            print(f"📝 Creating Jira ticket...")
            self._update_workflow(workflow_id, 'creating_jira_ticket')
            
            issue_key = self.jira.create_ticket(bug_report)
            print(f"✅ Created Jira ticket: {issue_key}")
            
            self._update_workflow(workflow_id, 'jira_ticket_created', {'issue_key': issue_key})
            
            # Step 6: Create GitHub PR (if fix exists with patches)
            pr_url = None
            if fix and fix.get('patches'):
                print(f"🌿 Creating GitHub branch and PR...")
                self._update_workflow(workflow_id, 'creating_pr')
                
                # Create branch
                branch_name = self.github.create_fix_branch(issue_key, bug_report['title'])
                
                # Apply patches using unified diff
                if self.github.apply_unified_diff(branch_name, fix['patches'], fix.get('commit_message', f"Fix: {bug_report['title']}")):
                    # Create PR
                    pr_url = self.github.create_pull_request(
                        branch_name=branch_name,
                        issue_key=issue_key,
                        bug_report=bug_report,
                        fix=fix
                    )
                    
                    if pr_url:
                        print(f"✅ Created PR: {pr_url}")
                        # Link PR to Jira  
                        self.jira.add_comment(issue_key, f"🔗 Pull Request created: {pr_url}")
                        self._update_workflow(workflow_id, 'pr_created', {'pr_url': pr_url})
                    else:
                        print(f"❌ Failed to create PR")
                        self._update_workflow(workflow_id, 'pr_failed')
            elif fix and fix.get('code_changes'):
                # Fallback to old method if using old format
                print(f"🌿 Creating GitHub branch and PR (legacy mode)...")
                self._update_workflow(workflow_id, 'creating_pr')
                
                branch_name = self.github.create_fix_branch(issue_key, bug_report['title'])
                
                if self.github.apply_code_changes(branch_name, fix['code_changes'], f"Fix: {bug_report['title']}"):
                    pr_url = self.github.create_pull_request(
                        branch_name=branch_name,
                        issue_key=issue_key,
                        bug_report=bug_report,
                        fix=fix
                    )
                    
                    if pr_url:
                        print(f"✅ Created PR: {pr_url}")
                        self.jira.add_comment(issue_key, f"🔗 Pull Request created: {pr_url}")
                        self._update_workflow(workflow_id, 'pr_created', {'pr_url': pr_url})
            else:
                self.jira.add_comment(issue_key, 
                    "ℹ️ No automated fix generated. Manual investigation required.")
            
            # Step 7: Complete workflow
            self._update_workflow(workflow_id, 'completed')
            
            result = {
                'success': True,
                'workflow_id': workflow_id,
                'issue_key': issue_key,
                'issue_url': f"https://{Config.JIRA_BASE_URL}/browse/{issue_key}",
                'pr_url': pr_url,
                'bug_title': bug_report['title'],
                'severity': bug_report.get('severity', 'Medium'),
                'similar_issues': similar_issues,
                'message': f"Successfully created Jira ticket {issue_key}" + 
                          (f" and PR {pr_url}" if pr_url else " (manual fix required)")
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Workflow failed: {e}")
            self._update_workflow(workflow_id, 'failed', {'error': str(e)})
            
            return {
                'success': False,
                'workflow_id': workflow_id,
                'error': str(e),
                'message': f"Failed to process bug report: {str(e)}"
            }
    
    def _locate_with_deimos(self, bug_report: Dict[str, Any], code_context: str) -> Dict[str, Any]:
        """Use Deimos Router for locating change target.
        
        Args:
            bug_report: Structured bug report
            code_context: Relevant code from repository
            
        Returns:
            Location information with confidence
        """
        # Build messages for Deimos routing
        messages = [
            {"role": "system", "content": "You are a code analysis expert. Locate the exact code region to fix."},
            {"role": "user", "content": f"""Bug Report:
Title: {bug_report.get('title', '')}
Description: {bug_report.get('description', '')}
Expected: {bug_report.get('expected_behavior', '')}
Actual: {bug_report.get('actual_behavior', '')}

Code Context:
{code_context[:8000]}

Find the exact file and region that needs to be changed. Return JSON with targets array containing path, anchor_before, anchor_after, and reason."""}
        ]
        
        try:
            # Route through Deimos for PR editing task
            response = self.deimos.route_pr_edit_request(messages, task="locate_change_target")
            
            if hasattr(response, 'choices'):
                text = response.choices[0].message.content.strip()
            else:
                text = str(response).strip()
            
            print(f"Deimos locate response preview: {text[:300]}...")
            
            # Parse JSON from response
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                result = json.loads(json_str)
                print(f"Located target via Deimos: {result.get('targets', [])[:1]}, confidence: {result.get('confidence', 0)}")
                return result
        except Exception as e:
            print(f"Deimos routing failed for locate_change_target: {e}")
            # Fallback to Cohere
            print(f"Falling back to Cohere for location...")
            return self.cohere.locate_change_target(bug_report, code_context)
        
        return {"targets": [], "confidence": 0.0}
    
    def _generate_patch_with_deimos(self, bug_report: Dict[str, Any], code_slice: str, location: Dict[str, Any]) -> Dict[str, Any]:
        """Use Deimos Router for generating code patch.
        
        Args:
            bug_report: Structured bug report  
            code_slice: The specific code region to edit
            location: Target location from Pass A
            
        Returns:
            Patch with unified diff and confidence
        """
        if not location.get('targets'):
            return {"patches": [], "confidence": 0.0}
        
        target = location['targets'][0]
        
        # Build messages for Deimos routing
        messages = [
            {"role": "system", "content": "You are a precise code editor. Generate a minimal unified diff to fix the issue."},
            {"role": "user", "content": f"""Target File: {target['path']}
Reason for Change: {target['reason']}

Original Code:
{code_slice}

Change Required: {bug_report.get('description', '')}

Generate a unified diff (git format) with minimal changes. Return JSON with patches array containing path and unified_diff, plus commit_message and confidence."""}
        ]
        
        try:
            # Route through Deimos for PR editing task
            response = self.deimos.route_pr_edit_request(messages, task="generate_patch")
            
            if hasattr(response, 'choices'):
                text = response.choices[0].message.content.strip()
            else:
                text = str(response).strip()
            
            print(f"Deimos patch response preview: {text[:300]}...")
            
            # Parse JSON from response
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                result = json.loads(json_str)
                
                # Count changed lines
                if result.get('patches'):
                    diff = result['patches'][0].get('unified_diff', '')
                    changed = sum(1 for line in diff.split('\n') 
                                if line.startswith('+') or line.startswith('-'))
                    print(f"Generated patch via Deimos with {changed} changed lines")
                
                return result
        except Exception as e:
            print(f"Deimos routing failed for generate_patch: {e}")
            # Fallback to Cohere
            print(f"Falling back to Cohere for patch generation...")
            return self.cohere.generate_small_patch(bug_report, code_slice, location)
        
        return {"patches": [], "confidence": 0.0}
    
    def _extract_keywords(self, bug_report: Dict[str, Any]) -> List[str]:
        """Extract keywords from bug report for code search.
        
        Args:
            bug_report: Parsed bug report
            
        Returns:
            List of keywords
        """
        keywords = []
        
        # Extract from title
        if bug_report.get('title'):
            words = bug_report['title'].split()
            keywords.extend([w for w in words if len(w) > 3])
        
        # Extract from affected components
        keywords.extend(bug_report.get('affected_components', []))
        
        # Common programming terms to filter out
        stopwords = {'the', 'and', 'for', 'with', 'from', 'into', 'when', 'where', 'this', 'that'}
        
        return [k for k in keywords if k.lower() not in stopwords][:5]
    
    def _update_workflow(self, workflow_id: str, status: str, data: Optional[Dict] = None):
        """Update workflow status.
        
        Args:
            workflow_id: Workflow identifier
            status: Current status
            data: Additional data
        """
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id]['status'] = status
            self.active_workflows[workflow_id]['steps'].append({
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            })
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow.
        
        Args:
            workflow_id: Workflow identifier
            
        Returns:
            Workflow status or None
        """
        return self.active_workflows.get(workflow_id)


class MCPTool:
    """Base class for MCP tools."""
    
    def __init__(self, name: str, description: str):
        """Initialize tool.
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with parameters.
        
        Args:
            params: Tool parameters
            
        Returns:
            Execution result
        """
        raise NotImplementedError


class CreateJiraTicketTool(MCPTool):
    """Tool for creating Jira tickets."""
    
    def __init__(self):
        super().__init__(
            name="create_jira_ticket",
            description="Create a Jira ticket from bug report"
        )
        self.jira = JiraTool()
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create Jira ticket.
        
        Args:
            params: Must contain 'bug_report'
            
        Returns:
            Result with issue_key
        """
        bug_report = params.get('bug_report')
        if not bug_report:
            return {'error': 'bug_report parameter required'}
        
        issue_key = self.jira.create_ticket(bug_report)
        
        return {
            'success': True,
            'issue_key': issue_key,
            'url': f"https://{Config.JIRA_BASE_URL}/browse/{issue_key}"
        }


class AnalyzeCodebaseTool(MCPTool):
    """Tool for analyzing codebase."""
    
    def __init__(self):
        super().__init__(
            name="analyze_codebase",
            description="Analyze codebase for bug context"
        )
        self.github = GitHubTool()
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze codebase.
        
        Args:
            params: Must contain 'keywords' or 'components'
            
        Returns:
            Code context
        """
        keywords = params.get('keywords', [])
        components = params.get('components', [])
        
        relevant_files = self.github.get_relevant_files(keywords)
        code_context = self.github.analyze_codebase_context(components)
        
        return {
            'success': True,
            'relevant_files': relevant_files,
            'code_context': code_context
        }


class CreateGitHubPRTool(MCPTool):
    """Tool for creating GitHub PRs."""
    
    def __init__(self):
        super().__init__(
            name="create_github_pr",
            description="Create GitHub PR with fix"
        )
        self.github = GitHubTool()
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create GitHub PR.
        
        Args:
            params: Must contain issue_key, bug_report, fix
            
        Returns:
            PR details
        """
        issue_key = params.get('issue_key')
        bug_report = params.get('bug_report')
        fix = params.get('fix')
        
        if not all([issue_key, bug_report, fix]):
            return {'error': 'Missing required parameters'}
        
        # Create branch
        branch_name = self.github.create_fix_branch(issue_key, bug_report['title'])
        
        # Apply changes
        if fix.get('code_changes'):
            self.github.apply_code_changes(
                branch_name, 
                fix['code_changes'], 
                f"[{issue_key}] Fix: {bug_report['title']}"
            )
        
        # Create PR
        pr_url = self.github.create_pull_request(branch_name, issue_key, bug_report, fix)
        
        return {
            'success': True,
            'pr_url': pr_url,
            'branch_name': branch_name
        }
