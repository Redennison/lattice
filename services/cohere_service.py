"""Cohere LLM service for text processing."""

import cohere
from typing import Dict, Any, Optional, List
from config import Config
import json

class CohereService:
    """Service for interacting with Cohere API."""
    
    def __init__(self):
        """Initialize Cohere client."""
        self.client = cohere.Client(Config.COHERE_API_KEY)
    
    def parse_bug_report(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """Parse Slack conversation into structured bug report.
        
        Args:
            conversation: List of messages from Slack thread
            
        Returns:
            Structured bug report data
        """
        print(f"COHERE: parse_bug_report called with {len(conversation)} messages")
        
        # Format conversation for LLM
        try:
            formatted_conv = "\n".join([
                f"{msg['user']}: {msg['text']}" 
                for msg in conversation
            ])
            print(f"COHERE: Formatted conversation: {formatted_conv[:200]}...")
        except Exception as e:
            print(f"COHERE ERROR: Failed to format conversation: {e}")
            raise
        
        prompt = f"""You are analyzing a Slack conversation about a bug or issue. Extract and structure the information into a clear bug report.

Conversation:
{formatted_conv}

Extract the following information:
1. Bug Title (concise, descriptive)
2. Bug Description (detailed explanation)
3. Steps to Reproduce (if mentioned)
4. Expected Behavior
5. Actual Behavior  
6. Severity (Critical/High/Medium/Low)
7. Affected Components (files, services, features mentioned)
8. Additional Context

Return as JSON with these exact keys: title, description, steps_to_reproduce, expected_behavior, actual_behavior, severity, affected_components, additional_context"""

        print(f"COHERE: Sending prompt to API...")
        try:
            response = self.client.generate(
                prompt=prompt,
                model='command-r-plus',
                temperature=0.3,
                max_tokens=1000
            )
            print(f"COHERE: API responded")
        except Exception as api_error:
            print(f"COHERE API ERROR: {api_error}")
            raise
        
        # Parse response
        try:
            # Extract JSON from response
            text = response.generations[0].text.strip()
            print(f"COHERE: Response text preview: {text[:200]}...")
            
            # Find JSON in response
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                print(f"COHERE: Extracted JSON string: {json_str[:200]}...")
                
                result = json.loads(json_str)
                print(f"COHERE: Parsed result keys: {result.keys()}")
                return result
        except Exception as parse_err:
            print(f"COHERE PARSE ERROR: {parse_err}")
            import traceback
            traceback.print_exc()
        
        # Fallback structure
        return {
            "title": "Bug Report from Slack",
            "description": formatted_conv[:500],
            "steps_to_reproduce": "See conversation",
            "expected_behavior": "System should work as intended",
            "actual_behavior": "Issue reported in conversation",
            "severity": "Medium",
            "affected_components": [],
            "additional_context": formatted_conv
        }
    
    def generate_code_fix(self, bug_report: Dict[str, Any], code_context: str) -> Dict[str, Any]:
        """Generate code fix based on bug report and codebase context.
        
        Args:
            bug_report: Structured bug report
            code_context: Relevant code from the repository
            
        Returns:
            Generated fix with explanation
        """
        # Build prompt WITHOUT f-string to avoid code_context causing issues
        prompt = """You are a senior software engineer. You must modify the file to fix the issue.

Request:
Title: """ + str(bug_report.get('title', 'Change Request')) + """
Description: """ + str(bug_report.get('description', '')) + """
Task: """ + str(bug_report.get('additional_context', '')) + """

FILES PROVIDED BELOW (COMPLETE CONTENT):
""" + code_context[:15000] + """

CRITICAL REQUIREMENTS:
1. The above shows COMPLETE files - every line, every import, everything
2. In your response, for the 'changes' field, copy the ENTIRE file and make ONLY the requested change
3. DO NOT abbreviate, truncate, or use "..." anywhere
4. DO NOT add new imports unless absolutely necessary
5. DO NOT change any existing logic except what's requested
6. For Tailwind CSS color changes:
   - Change from red classes (bg-red-*, text-red-*, border-red-*) 
   - To blue classes (bg-blue-*, text-blue-*, border-blue-*)
   - Keep the same shade number (e.g., red-500 → blue-500)
7. The file MUST compile - keep all TypeScript types, all imports, all exports exactly as they are

Generate a JSON response with:
- root_cause: Brief analysis of the issue
- fix_description: What you're changing
- code_changes: Array of objects, each with:
  - file: The file path
  - changes: THE COMPLETE MODIFIED FILE CONTENT (not a description!)
- testing_notes: How to test the changes

Example format:
{
  "root_cause": "Button uses red color class",
  "fix_description": "Changed button from red to blue",
  "code_changes": [
    {
      "file": "components/Button.tsx",
      "changes": "// ENTIRE FILE CONTENT HERE WITH CHANGES APPLIED\\nimport React from 'react';\\n...entire modified file..."
    }
  ],
  "testing_notes": "Verify button appears blue"
}

Return ONLY valid JSON. The 'changes' field must contain the COMPLETE file content, not instructions."""

        print(f"COHERE generate_code_fix: Sending prompt ({len(prompt)} chars) to API...")
        print(f"COHERE generate_code_fix: Code context length: {len(code_context)} chars")
        
        try:
            response = self.client.generate(
                prompt=prompt,
                model='command-r-plus',  # Using highest Cohere model
                temperature=0.1,  # Lower temperature for more consistent output
                max_tokens=8000  # Maximum tokens for complete file generation
            )
            print(f"COHERE generate_code_fix: API responded successfully")
        except Exception as api_error:
            print(f"COHERE generate_code_fix API ERROR: {api_error}")
            import traceback
            traceback.print_exc()
            raise
        
        try:
            text = response.generations[0].text.strip()
            print(f"Cohere response preview: {text[:500]}...")
            
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                result = json.loads(json_str)
                
                # Log what we got
                print(f"Parsed JSON keys: {result.keys()}")
                if 'code_changes' in result:
                    print(f"Code changes count: {len(result['code_changes'])}")
                    for i, change in enumerate(result['code_changes'][:2]):
                        print(f"  Change {i}: file={change.get('file', 'none')}, changes_len={len(str(change.get('changes', '')))}")
                
                return result
        except Exception as e:
            print(f"Error parsing Cohere response: {e}")
            print(f"Full response: {text[:1000]}")
        
        # Fallback
        return {
            "root_cause": "Analysis needed",
            "fix_description": "Manual review required",
            "code_changes": [],
            "testing_notes": "Test thoroughly before deployment"
        }
    
    def summarize_for_pr(self, bug_report: Dict[str, Any], fix: Dict[str, Any]) -> str:
        """Generate PR description.
        
        Args:
            bug_report: Original bug report
            fix: Generated fix details
            
        Returns:
            PR description text
        """
        prompt = f"""Generate a professional GitHub PR description for this bug fix.

Bug: {bug_report.get('title', 'Bug Fix')}
Root Cause: {fix.get('root_cause', 'See analysis')}
Fix Description: {fix.get('fix_description', 'See changes')}

Create a PR description with:
- Summary
- Problem
- Solution
- Testing
- Related Issues

Keep it concise but informative."""

        response = self.client.generate(
            prompt=prompt,
            model='command-r',
            temperature=0.3,
            max_tokens=500
        )
        
        return response.generations[0].text.strip()
