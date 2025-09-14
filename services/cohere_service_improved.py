"""Improved Cohere service with search-and-replace strategy."""

import cohere
from typing import Dict, Any, List, Tuple, Optional
import json
from config import Config
import re

class ImprovedCohereService:
    """Improved service for generating precise code edits."""
    
    def __init__(self):
        """Initialize Cohere client."""
        self.client = cohere.Client(Config.COHERE_API_KEY)
    
    def generate_search_replace_edits(self, 
                                     bug_report: Dict[str, Any], 
                                     file_path: str,
                                     file_content: str,
                                     context_radius: int = 50) -> Dict[str, Any]:
        """Generate precise search-and-replace edits for a file.
        
        This is the RECOMMENDED approach for simple fixes.
        
        Args:
            bug_report: Structured bug report
            file_path: Path to the file being edited
            file_content: Complete content of the file
            context_radius: Lines to show around potential change areas
            
        Returns:
            Dict with search-replace pairs and metadata
        """
        # First, identify the likely change location
        location_prompt = f"""You are analyzing a code file to find where to make changes.

File: {file_path}
Issue: {bug_report.get('title', '')}
Description: {bug_report.get('description', '')}

Code excerpt (showing relevant sections):
```
{self._extract_relevant_sections(file_content, bug_report)}
```

Identify the EXACT strings that need to be changed. Be very specific.
For example, if changing a button from red to blue, find the exact className or style.

Return JSON:
{{
  "target_indicators": ["unique strings near the change", "component names"],
  "change_type": "color|text|logic|style",
  "confidence": 0.0-1.0
}}"""

        # Get location hints
        location_response = self.client.generate(
            prompt=location_prompt,
            model='command-r-plus',
            temperature=0.1,
            max_tokens=500
        )
        
        location_info = self._parse_json_response(location_response.generations[0].text)
        
        # Now generate the actual search-replace pairs
        edit_prompt = f"""Generate EXACT search-and-replace pairs to fix the issue.

File: {file_path}
Task: {bug_report.get('description', '')}

Relevant code sections:
```
{self._get_targeted_sections(file_content, location_info.get('target_indicators', []))}
```

CRITICAL RULES:
1. The "find" string MUST exist EXACTLY in the code (including whitespace, quotes, everything)
2. The "replace" string should be the minimal change needed
3. For Tailwind color changes: change red-* to blue-* (keep same number)
4. Preserve all formatting, indentation, quotes exactly
5. Make the smallest change possible

Return JSON with multiple find-replace pairs if needed:
{{
  "edits": [
    {{
      "find": "EXACT string from the code including all spaces and characters",
      "replace": "EXACT replacement string",
      "description": "what this change does"
    }}
  ],
  "validation_test": "how to verify the fix worked"
}}

Example for changing button color:
{{
  "edits": [
    {{
      "find": "className=\\"bg-red-500 hover:bg-red-600 text-white\\"",
      "replace": "className=\\"bg-blue-500 hover:bg-blue-600 text-white\\"",
      "description": "Change button background from red to blue"
    }}
  ],
  "validation_test": "Button should appear blue instead of red"
}}"""

        # Generate edits
        edit_response = self.client.generate(
            prompt=edit_prompt,
            model='command-r-plus',
            temperature=0.05,  # Very low for precision
            max_tokens=2000
        )
        
        edits = self._parse_json_response(edit_response.generations[0].text)
        
        # Validate that find strings actually exist
        validated_edits = self._validate_edits(edits.get('edits', []), file_content)
        
        return {
            'file_path': file_path,
            'edits': validated_edits,
            'confidence': location_info.get('confidence', 0.5),
            'validation_test': edits.get('validation_test', ''),
            'method': 'search-replace'
        }
    
    def _extract_relevant_sections(self, content: str, bug_report: Dict) -> str:
        """Extract sections of code most relevant to the bug."""
        lines = content.split('\n')
        relevant_sections = []
        
        # Keywords to search for
        keywords = []
        if bug_report.get('affected_components'):
            if isinstance(bug_report['affected_components'], list):
                keywords.extend(bug_report['affected_components'])
            else:
                keywords.append(bug_report['affected_components'])
        
        # Add common patterns based on description
        description = bug_report.get('description', '').lower()
        if 'color' in description or 'red' in description or 'blue' in description:
            keywords.extend(['className', 'style', 'bg-red', 'text-red', 'border-red'])
        if 'button' in description:
            keywords.extend(['Button', 'button', 'onClick', 'onPress'])
        
        # Find lines containing keywords
        for i, line in enumerate(lines):
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # Add context around the match
                    start = max(0, i - 5)
                    end = min(len(lines), i + 6)
                    section = '\n'.join(f"{j+1}: {lines[j]}" for j in range(start, end))
                    relevant_sections.append(f"// Section around line {i+1} (keyword: {keyword}):\n{section}")
                    break
        
        # Limit total size
        result = '\n\n'.join(relevant_sections[:5])
        return result[:3000] if result else content[:2000]
    
    def _get_targeted_sections(self, content: str, indicators: List[str]) -> str:
        """Get code sections around target indicators."""
        if not indicators:
            return content[:2000]
        
        lines = content.split('\n')
        sections = []
        
        for indicator in indicators[:3]:  # Top 3 indicators
            for i, line in enumerate(lines):
                if indicator.lower() in line.lower():
                    start = max(0, i - 10)
                    end = min(len(lines), i + 11)
                    section = '\n'.join(lines[start:end])
                    sections.append(f"// Around '{indicator}':\n{section}")
                    break
        
        return '\n\n'.join(sections) if sections else content[:2000]
    
    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from LLM response."""
        try:
            # Find JSON in response
            if '{' in text and '}' in text:
                json_str = text[text.index('{'):text.rindex('}')+1]
                return json.loads(json_str)
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
        return {}
    
    def _validate_edits(self, edits: List[Dict], file_content: str) -> List[Dict]:
        """Validate that find strings actually exist in the file."""
        validated = []
        
        for edit in edits:
            find_str = edit.get('find', '')
            replace_str = edit.get('replace', '')
            
            if not find_str or not replace_str:
                print(f"  Skip edit: missing find or replace")
                continue
            
            if find_str == replace_str:
                print(f"  Skip edit: find and replace are identical")
                continue
            
            # Check if find string exists
            if find_str in file_content:
                validated.append(edit)
                count = file_content.count(find_str)
                print(f"  ✓ Valid edit: '{find_str[:50]}...' found {count} time(s)")
            else:
                print(f"  ✗ Invalid edit: '{find_str[:50]}...' not found in file")
                
                # Try to find a close match
                similar = self._find_similar_string(find_str, file_content)
                if similar:
                    print(f"    Suggestion: Did you mean '{similar[:50]}...'?")
                    edit['find'] = similar
                    validated.append(edit)
        
        return validated
    
    def _find_similar_string(self, target: str, content: str, threshold: int = 5) -> Optional[str]:
        """Find a similar string in content (fuzzy matching)."""
        # Simple approach: look for strings with similar keywords
        target_words = re.findall(r'\w+', target)
        if len(target_words) < 2:
            return None
        
        lines = content.split('\n')
        for line in lines:
            if all(word in line for word in target_words[:2]):
                # Found a line with similar keywords
                return line.strip()
        
        return None
    
    def apply_search_replace_edits(self, file_content: str, edits: List[Dict]) -> Tuple[str, List[str]]:
        """Apply validated search-replace edits to file content.
        
        Args:
            file_content: Original file content
            edits: List of search-replace pairs
            
        Returns:
            Tuple of (modified_content, list_of_changes_made)
        """
        modified = file_content
        changes_made = []
        
        for edit in edits:
            find_str = edit.get('find', '')
            replace_str = edit.get('replace', '')
            description = edit.get('description', 'Change applied')
            
            if find_str in modified:
                count = modified.count(find_str)
                modified = modified.replace(find_str, replace_str)
                changes_made.append(f"{description} ({count} occurrence(s))")
                print(f"  Applied: {description}")
            else:
                print(f"  Skipped: '{find_str[:30]}...' not found")
        
        return modified, changes_made


# For backward compatibility
class CohereService(ImprovedCohereService):
    """Backward compatible wrapper."""
    
    def generate_code_fix(self, bug_report: Dict[str, Any], code_context: str) -> Dict[str, Any]:
        """Generate fix using the improved search-replace strategy."""
        # Parse the code context to extract file information
        files = self._parse_code_context(code_context)
        
        all_edits = []
        for file_info in files[:3]:  # Process top 3 files
            result = self.generate_search_replace_edits(
                bug_report=bug_report,
                file_path=file_info['path'],
                file_content=file_info['content']
            )
            
            if result['confidence'] > 0.6 and result['edits']:
                # Convert to old format for compatibility
                modified_content, changes = self.apply_search_replace_edits(
                    file_info['content'],
                    result['edits']
                )
                
                all_edits.append({
                    'file': file_info['path'],
                    'changes': modified_content,
                    'description': ' | '.join(changes)
                })
        
        return {
            'root_cause': f"Identified {len(all_edits)} file(s) needing changes",
            'fix_description': 'Applied targeted search-and-replace edits',
            'code_changes': all_edits,
            'testing_notes': bug_report.get('testing_notes', 'Verify changes visually'),
            'method': 'search-replace'
        }
    
    def _parse_code_context(self, context: str) -> List[Dict]:
        """Parse the code context string into individual files."""
        files = []
        
        # Split by the file separator pattern
        parts = re.split(r'=== COMPLETE FILE: (.*?) ===\n', context)
        
        for i in range(1, len(parts), 2):
            if i+1 < len(parts):
                files.append({
                    'path': parts[i].strip(),
                    'content': parts[i+1]
                })
        
        return files if files else [{'path': 'unknown', 'content': context}]
