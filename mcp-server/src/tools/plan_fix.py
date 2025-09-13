"""
Plan Fix Tool

This MCP tool analyzes the codebase using code queries from analysis and generates
a comprehensive fix plan with specific code changes using Deimos Router.
"""

import re
from typing import Dict, Any, List, Optional

from models.schemas import (
    AnalysisResult, FixPlan, CodeChange,
    JiraTicketContent
)
from services.deimos_router_service import route_request
from services.repo_indexer import RepoIndexer
from utils.logger import logger

async def plan_fix_tool(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a fix plan based on analysis results and codebase context.
    
    Args:
        arguments: Contains analysis_result from analyze_request and jira_issue
        
    Returns:
        FixPlan as dictionary with code changes and implementation steps
    """
    logger.info("Starting fix planning with Deimos Router...")
    
    # Parse the inputs
    analysis_data = arguments.get("analysis_result", {})
    jira_issue = arguments.get("jira_issue", {})
    repo_path = arguments.get("repo_path", ".")
    
    if not analysis_data:
        raise ValueError("analysis_result is required")
    
    # Extract relevant data
    jira_ticket_data = analysis_data.get("jira_ticket", {})
    code_queries = analysis_data.get("code_queries", [])
    confidence_score = analysis_data.get("confidence_score", 0.5)
    
    # Use repo indexer to find relevant files
    repo_indexer = RepoIndexer(repo_path)
    relevant_files = await repo_indexer.search_relevant_files(code_queries)
    
    # Analyze the codebase context
    codebase_context = await _analyze_codebase(relevant_files, jira_ticket_data)
    
    # Generate fix plan using Deimos Router for optimal LLM selection
    fix_plan = await _generate_fix_with_deimos(jira_ticket_data, codebase_context, confidence_score)
    
    logger.info(f"Fix plan generated with {len(fix_plan.changes)} changes")
    
    # Return as dictionary for MCP compatibility
    return {
        "summary": fix_plan.summary,
        "root_cause": fix_plan.root_cause,
        "changes": [
            {
                "file_path": change.file_path,
                "change_type": change.change_type,
                "old_content": change.old_content,
                "new_content": change.new_content,
                "line_start": change.line_start,
                "line_end": change.line_end,
                "description": change.description
            } for change in fix_plan.changes
        ],
        "test_plan": fix_plan.test_plan,
        "risks": fix_plan.risks,
        "dependencies": fix_plan.dependencies,
        "jira_issue_key": jira_issue.get("key"),
        "confidence_score": confidence_score
    }

async def _analyze_codebase(relevant_files: List[Dict[str, Any]], jira_ticket: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes codebase to understand context for fix planning.
    
    Args:
        relevant_files: Files found by repo indexer
        jira_ticket: Jira ticket data with issue details
        
    Returns:
        Dictionary with codebase analysis
    """
    logger.info(f"Analyzing {len(relevant_files)} relevant files...")
    
    analysis = {
        "files": [],
        "patterns_found": [],
        "dependencies": [],
        "test_coverage": [],
        "similar_fixes": []
    }
    
    for file_info in relevant_files:
        file_path = file_info.get("path")
        content = file_info.get("content", "")
        relevance_score = file_info.get("relevance_score", 0.5)
        
        # Analyze file content for patterns
        patterns = _detect_code_patterns(content, jira_ticket)
        
        # Check for test files
        is_test = any(marker in file_path.lower() for marker in ['test', 'spec', '_test.', '.test.'])
        
        analysis["files"].append({
            "path": file_path,
            "relevance_score": relevance_score,
            "patterns": patterns,
            "is_test": is_test,
            "line_count": len(content.split('\n')) if content else 0
        })
        
        analysis["patterns_found"].extend(patterns)
        
        if is_test:
            analysis["test_coverage"].append(file_path)
    
    # Deduplicate patterns
    analysis["patterns_found"] = list(set(analysis["patterns_found"]))
    
    return analysis

def _detect_code_patterns(content: str, jira_ticket: Dict[str, Any]) -> List[str]:
    """
    Detects relevant code patterns in file content.
    
    Args:
        content: File content
        jira_ticket: Jira ticket data
        
    Returns:
        List of detected patterns
    """
    patterns = []
    
    # Check for error handling patterns
    if "try" in content and "catch" in content:
        patterns.append("error_handling")
    elif "try:" in content and "except" in content:
        patterns.append("error_handling")
    
    # Check for async patterns
    if "async" in content or "await" in content:
        patterns.append("async_code")
    
    # Check for validation patterns
    if "validate" in content.lower() or "check" in content.lower():
        patterns.append("validation")
    
    # Check for null/undefined checks
    if "null" in content or "undefined" in content or "None" in content:
        patterns.append("null_checks")
    
    # Check for specific error messages from ticket
    error_messages = jira_ticket.get("technical_details", {}).get("error_codes", [])
    for error in error_messages:
        if error in content:
            patterns.append(f"error_{error}")
    
    return patterns

async def _generate_fix_with_deimos(jira_ticket: Dict[str, Any], codebase_context: Dict[str, Any], confidence: float) -> FixPlan:
    """
    Generates fix plan using Deimos Router for intelligent LLM selection.
    
    Args:
        jira_ticket: Jira ticket details
        codebase_context: Analysis of relevant code
        confidence: Confidence score from analysis
        
    Returns:
        FixPlan with code changes
    """
    # Determine task complexity for routing
    task_complexity = _determine_fix_complexity(codebase_context)
    
    # Create prompt for fix generation
    prompt = _create_fix_generation_prompt(jira_ticket, codebase_context)
    
    # Determine cost priority based on complexity
    cost_priority = 'high_quality' if task_complexity == 'complex' else 'balanced'
    
    # Route to optimal LLM using the service
    response = await route_request(
        prompt=prompt,
        task='coding',  # This is a coding task
        context=str(codebase_context),
        max_tokens=3000,
        temperature=0.1,
        explain=False
    )
    
    # Parse the LLM response into FixPlan
    fix_plan = _parse_fix_response(response, jira_ticket)
    
    logger.info(f"Fix generated using {response.selected_model} (cost: ${response.estimated_cost:.4f})")
    
    return fix_plan

def _determine_fix_complexity(codebase_context: Dict[str, Any]) -> str:
    """
    Determines the complexity of the fix based on codebase analysis.
    """
    score = 0
    
    # Factor in number of files
    file_count = len(codebase_context['files'])
    if file_count > 5:
        score += 3
    elif file_count > 2:
        score += 2
    else:
        score += 1
    
    # Factor in patterns found
    patterns = codebase_context['patterns_found']
    if 'async_code' in patterns:
        score += 2
    if 'error_handling' in patterns:
        score += 1
    if any('error_' in p for p in patterns):
        score += 2
    
    # Factor in test coverage
    if not codebase_context['test_coverage']:
        score += 2  # No tests means higher complexity
    
    if score <= 3:
        return 'simple'
    elif score <= 6:
        return 'moderate'
    else:
        return 'complex'

def _create_fix_generation_prompt(jira_ticket: Dict[str, Any], codebase_context: Dict[str, Any]) -> str:
    """
    Creates a comprehensive prompt for fix generation.
    """
    # Extract relevant files info
    files_info = "\n".join([
        f"- {f['path']} (relevance: {f['relevance_score']:.2f}, patterns: {', '.join(f['patterns'])})"
        for f in codebase_context['files'][:10]  # Limit to top 10 files
    ])
    
    prompt = f"""
You are a senior software engineer tasked with generating a fix for the following issue.

ISSUE DETAILS:
Title: {jira_ticket.get('title', 'Unknown Issue')}
Description: {jira_ticket.get('description', '')}
Priority: {jira_ticket.get('priority', 'Medium')}
Issue Type: {jira_ticket.get('issue_type', 'Bug')}

ACCEPTANCE CRITERIA:
{chr(10).join(['- ' + ac for ac in jira_ticket.get('acceptance_criteria', [])])}

TECHNICAL DETAILS:
{jira_ticket.get('technical_details', 'No technical details provided')}

RELEVANT FILES IDENTIFIED:
{files_info}

CODE PATTERNS FOUND:
{', '.join(codebase_context['patterns_found'])}

TEST COVERAGE:
{len(codebase_context['test_coverage'])} test files found

Generate a fix plan with the following JSON structure:
{{
    "summary": "Brief summary of the fix approach",
    "root_cause": "Identified root cause of the issue",
    "changes": [
        {{
            "file_path": "path/to/file",
            "change_type": "modify",
            "old_content": "original code section",
            "new_content": "fixed code section",
            "line_start": 10,
            "line_end": 20,
            "description": "What this change does"
        }}
    ],
    "test_plan": ["Test step 1", "Test step 2"],
    "risks": ["Potential risk 1", "Potential risk 2"],
    "dependencies": ["External dependency if any"]
}}

IMPORTANT:
1. Make minimal, focused changes that directly address the issue
2. Include proper error handling and validation
3. Consider edge cases and potential side effects
4. Ensure backward compatibility
5. Follow the existing code style and patterns
6. Return ONLY valid JSON, no additional text
"""
    
    return prompt

def _parse_fix_response(response: Any, jira_ticket: Dict[str, Any]) -> FixPlan:
    """
    Parses the LLM response into a FixPlan object.
    """
    try:
        import json
        fix_data = json.loads(response.response)
        
        # Convert to FixPlan
        changes = []
        for change_data in fix_data.get('changes', []):
            changes.append(CodeChange(
                file_path=change_data.get('file_path', ''),
                change_type=change_data.get('change_type', 'modify'),
                old_content=change_data.get('old_content'),
                new_content=change_data.get('new_content'),
                line_start=change_data.get('line_start'),
                line_end=change_data.get('line_end'),
                description=change_data.get('description', '')
            ))
        
        return FixPlan(
            summary=fix_data.get('summary', 'Fix for ' + jira_ticket.get('title', 'issue')),
            root_cause=fix_data.get('root_cause', 'Root cause analysis pending'),
            changes=changes,
            test_plan=fix_data.get('test_plan', ['Manual testing required']),
            risks=fix_data.get('risks', []),
            dependencies=fix_data.get('dependencies', [])
        )
        
    except Exception as e:
        logger.warning(f"Failed to parse fix response: {e}")
        # Return a basic fix plan
        return FixPlan(
            summary=f"Fix for {jira_ticket.get('title', 'issue')}",
            root_cause="Unable to determine root cause automatically",
            changes=[],
            test_plan=["Manual code review and testing required"],
            risks=["Automated fix generation failed - manual intervention needed"],
            dependencies=[]
        )
