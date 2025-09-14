#!/usr/bin/env python3
"""Test script to demonstrate the improved search-replace approach vs current approach."""

import json
from services.cohere_service_improved import ImprovedCohereService
from services.cohere_service import CohereService as OldCohereService

def test_simple_color_change():
    """Test a simple color change request."""
    
    # Sample bug report
    bug_report = {
        'title': 'Change button color from red to blue',
        'description': 'The submit button should be blue instead of red to match our brand colors',
        'affected_components': ['Button.tsx'],
        'severity': 'Low'
    }
    
    # Sample file content (simplified React component)
    sample_file = '''import React from 'react';

export const SubmitButton = ({ onClick, disabled }) => {
  return (
    <button
      className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded"
      onClick={onClick}
      disabled={disabled}
    >
      Submit
    </button>
  );
};

export const CancelButton = ({ onClick }) => {
  return (
    <button
      className="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-4 rounded"
      onClick={onClick}
    >
      Cancel
    </button>
  );
};'''

    print("=" * 60)
    print("TESTING IMPROVED SEARCH-REPLACE APPROACH")
    print("=" * 60)
    
    # Test improved approach
    improved_service = ImprovedCohereService()
    
    print("\n1. Testing Improved Service (Search-Replace):")
    print("-" * 40)
    
    result = improved_service.generate_search_replace_edits(
        bug_report=bug_report,
        file_path='components/Button.tsx',
        file_content=sample_file
    )
    
    print(f"Confidence: {result['confidence']}")
    print(f"Method: {result['method']}")
    print(f"Validation Test: {result['validation_test']}")
    print("\nGenerated Edits:")
    
    for i, edit in enumerate(result['edits'], 1):
        print(f"\nEdit {i}:")
        print(f"  Find: {edit['find'][:60]}...")
        print(f"  Replace: {edit['replace'][:60]}...")
        print(f"  Description: {edit['description']}")
    
    # Apply the edits
    if result['edits']:
        modified_content, changes = improved_service.apply_search_replace_edits(
            sample_file, 
            result['edits']
        )
        
        print("\n2. Applied Changes:")
        print("-" * 40)
        for change in changes:
            print(f"  ✓ {change}")
        
        print("\n3. Modified File Preview:")
        print("-" * 40)
        # Show just the changed lines
        for line in modified_content.split('\n'):
            if 'blue' in line:
                print(f"  >>> {line}")
            elif 'red' in line:
                print(f"  !!! {line}")  # Should not appear if change worked
    
    print("\n" + "=" * 60)
    print("COMPARISON WITH CURRENT APPROACH")
    print("=" * 60)
    
    # Show what the current approach would do
    print("\nCurrent Approach Problems:")
    print("-" * 40)
    print("1. Sends entire file (or multiple files) to Cohere")
    print(f"   - Current file size: {len(sample_file)} chars")
    print("2. Asks for COMPLETE file regeneration in response")
    print("3. Common failures:")
    print("   - Returns '...' or truncated code")
    print("   - Forgets imports or types")
    print("   - Changes unrelated parts")
    print("4. No validation that changes are correct")
    
    print("\n" + "=" * 60)
    print("ADVANTAGES OF SEARCH-REPLACE APPROACH")
    print("=" * 60)
    print("✓ Precise: Only changes exact strings")
    print("✓ Validated: Checks that find strings exist")
    print("✓ Minimal: Changes only what's needed")
    print("✓ Reliable: No truncation or abbreviation")
    print("✓ Traceable: Clear record of what changed")
    print("✓ Fast: Smaller prompts, faster responses")

if __name__ == "__main__":
    try:
        test_simple_color_change()
    except Exception as e:
        print(f"\nNote: This is a demonstration script.")
        print(f"To run actual tests, ensure Cohere API is configured.")
        print(f"Error: {e}")
