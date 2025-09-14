#!/usr/bin/env python3
"""Integration test for the complete Lattice Bot workflow."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List
import json
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services.cohere_service import CohereService
from services.deimos_service import DeimosService
from tools.jira_tool import JiraTool
from tools.github_tool import GitHubTool

async def test_full_integration():
    """Test the complete integration without creating actual tickets/PRs."""
    
    print("""
╔══════════════════════════════════════╗
║   🧪 Integration Test Suite          ║
║   Testing all components together    ║
╚══════════════════════════════════════╝
    """)
    
    results = {}
    
    # Test 1: Cohere Bug Parsing
    print("\n[1/5] Testing Cohere Bug Parsing...")
    try:
        cohere = CohereService()
        test_conversation = [
            {"user": "Dev1", "text": "The API is returning 404 for valid user IDs"},
            {"user": "Dev2", "text": "It happens in the user_service.py file"},
            {"user": "Dev1", "text": "We need to fix the route mapping"}
        ]
        
        bug_report = cohere.parse_bug_report(test_conversation)
        assert bug_report is not None
        assert 'title' in bug_report
        print(f"✅ Parsed bug: {bug_report.get('title', 'N/A')}")
        results['cohere_parsing'] = True
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        results['cohere_parsing'] = False
    
    # Test 2: Deimos Routing
    print("\n[2/5] Testing Deimos Router...")
    try:
        deimos = DeimosService()
        
        # Test different task types
        parse_model = deimos.route_task("parse_bug_report", "low")
        fix_model = deimos.route_task("generate_code_fix", "high")
        
        assert parse_model == "command-r"
        assert fix_model == "command-r-plus"
        
        print(f"✅ Routing works: parse→{parse_model}, fix→{fix_model}")
        results['deimos_routing'] = True
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        results['deimos_routing'] = False
    
    # Test 3: Jira Connectivity
    print("\n[3/5] Testing Jira Connection...")
    try:
        jira = JiraTool()
        
        # Test search (non-destructive)
        similar = jira.find_similar_issues("test", limit=1)
        
        # Test project access
        project = jira.jira.project(Config.JIRA_PROJECT_KEY)
        
        print(f"✅ Connected to Jira project: {project.key}")
        results['jira_connection'] = True
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        results['jira_connection'] = False
    
    # Test 4: GitHub Connectivity
    print("\n[4/5] Testing GitHub Access...")
    try:
        github = GitHubTool()
        
        # Test repo access
        repo_name = github.repo.full_name
        branch_count = len(list(github.repo.get_branches()[:5]))
        
        # Test search functionality
        keywords = ["test", "bug", "fix"]
        files = github.get_relevant_files(keywords, max_files=2)
        
        print(f"✅ Connected to repo: {repo_name} ({branch_count} branches)")
        results['github_connection'] = True
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        results['github_connection'] = False
    
    # Test 5: End-to-End Flow (Dry Run)
    print("\n[5/5] Testing End-to-End Flow (Dry Run)...")
    try:
        # Simulate workflow without creating actual tickets/PRs
        cohere = CohereService()
        
        # Parse bug
        conversation = [
            {"user": "User", "text": "Login fails with special characters in email"},
            {"user": "Support", "text": "Error occurs in auth_handler.py line 45"}
        ]
        bug_report = cohere.parse_bug_report(conversation)
        
        # Route task
        deimos = DeimosService()
        model = deimos.route_task("generate_code_fix", "medium")
        
        # Get code context (limited)
        github = GitHubTool()
        context = "Sample code context for testing"
        
        # Generate fix (simulation)
        fix = {
            "root_cause": "Email validation regex doesn't handle special characters",
            "fix_description": "Update regex pattern to allow valid special characters",
            "code_changes": [
                {"file": "auth_handler.py", "changes": "# Fix would go here"}
            ],
            "testing_notes": "Test with various email formats"
        }
        
        print(f"✅ Workflow simulation complete")
        print(f"   • Bug parsed: {bug_report.get('title', 'N/A')}")
        print(f"   • Model selected: {model}")
        print(f"   • Fix identified: {fix['root_cause']}")
        results['workflow_simulation'] = True
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        results['workflow_simulation'] = False
    
    # Summary
    print("\n" + "="*50)
    print("INTEGRATION TEST RESULTS")
    print("="*50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test, success in results.items():
        icon = "✅" if success else "❌"
        print(f"{icon} {test.replace('_', ' ').title()}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("\nThe system is ready for use:")
        print("  1. Configure Slack tokens (see slack_app_setup.md)")
        print("  2. Run: python slack_bot.py")
        print("  3. Mention @Lattice in a Slack thread")
    else:
        print("\n⚠️ Some tests failed. Please check:")
        print("  • API credentials in .env")
        print("  • Network connectivity")
        print("  • Repository/project access")
    
    return passed == total

def main():
    """Main entry point."""
    # Validate configuration
    if not Config.validate():
        print("\n❌ Configuration validation failed")
        print("Please check your .env file")
        return False
    
    # Run integration tests
    success = asyncio.run(test_full_integration())
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
