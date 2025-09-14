#!/usr/bin/env python3
"""Test script for Lattice Bot components."""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import json

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from services.cohere_service import CohereService
from services.deimos_service import DeimosService
from tools.jira_tool import JiraTool
from tools.github_tool import GitHubTool
from mcp_server import MCPServer

class ComponentTester:
    """Test harness for Lattice Bot components."""
    
    def __init__(self):
        """Initialize tester."""
        self.results = []
        self.failed = False
    
    def test(self, name: str, func):
        """Run a test and track results."""
        print(f"\n🧪 Testing: {name}")
        try:
            result = func()
            if asyncio.iscoroutine(result):
                result = asyncio.run(result)
            print(f"   ✅ {name} passed")
            self.results.append((name, True, None))
            return True
        except Exception as e:
            print(f"   ❌ {name} failed: {str(e)}")
            self.results.append((name, False, str(e)))
            self.failed = True
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = sum(1 for _, success, _ in self.results if not success)
        
        for name, success, error in self.results:
            icon = "✅" if success else "❌"
            print(f"{icon} {name}")
            if error:
                print(f"   Error: {error}")
        
        print(f"\nTotal: {passed} passed, {failed} failed")
        return not self.failed

def test_config():
    """Test configuration loading."""
    assert Config.COHERE_API_KEY, "Cohere API key not set"
    assert Config.JIRA_BASE_URL, "Jira URL not set"
    assert Config.GITHUB_TOKEN, "GitHub token not set"
    return True

def test_cohere_service():
    """Test Cohere service."""
    service = CohereService()
    
    # Test bug parsing
    test_conversation = [
        {"user": "Alice", "text": "The login button is broken"},
        {"user": "Bob", "text": "It shows error 500 when clicked"},
        {"user": "Alice", "text": "This is affecting all users on production"}
    ]
    
    result = service.parse_bug_report(test_conversation)
    assert result is not None, "Failed to parse bug report"
    assert "title" in result, "Bug report missing title"
    print(f"   Parsed title: {result.get('title', 'N/A')}")
    return True

def test_deimos_service():
    """Test Deimos routing service."""
    service = DeimosService()
    
    # Test task routing
    model1 = service.route_task("parse_bug_report", "low")
    assert model1, "Failed to route bug parsing task"
    print(f"   Bug parsing routed to: {model1}")
    
    model2 = service.route_task("generate_code_fix", "high")
    assert model2, "Failed to route code fix task"
    print(f"   Code fix routed to: {model2}")
    
    return True

def test_jira_tool():
    """Test Jira tool connectivity."""
    tool = JiraTool()
    
    # Test connection
    projects = tool.jira.projects()
    assert projects, "Failed to connect to Jira"
    print(f"   Connected to Jira - found {len(projects)} projects")
    
    # Test search (non-destructive)
    similar = tool.find_similar_issues("test", limit=1)
    print(f"   Search works - found {len(similar)} issues")
    
    return True

def test_github_tool():
    """Test GitHub tool connectivity."""
    tool = GitHubTool()
    
    # Test repo access
    assert tool.repo, "Failed to access GitHub repo"
    print(f"   Connected to repo: {tool.repo.full_name}")
    
    # Test branch listing
    branches = list(tool.repo.get_branches())
    print(f"   Found {len(branches)} branches")
    
    return True

async def test_mcp_server():
    """Test MCP server initialization."""
    server = MCPServer()
    
    # Test workflow tracking
    test_workflow_id = "test_channel_123"
    server.active_workflows[test_workflow_id] = {
        'status': 'test',
        'started_at': datetime.now().isoformat(),
        'steps': []
    }
    
    status = server.get_workflow_status(test_workflow_id)
    assert status is not None, "Failed to track workflow"
    assert status['status'] == 'test', "Workflow status mismatch"
    print(f"   Workflow tracking works")
    
    return True

def test_sample_workflow():
    """Test a sample bug report parsing."""
    print("\n📝 Sample Bug Report Processing:")
    
    service = CohereService()
    
    # Sample conversation
    conversation = [
        {"user": "Developer1", "text": "We have a critical issue with the payment gateway"},
        {"user": "Developer2", "text": "Users are getting timeout errors after 30 seconds"},
        {"user": "Developer1", "text": "It seems to be happening in the checkout.js file"},
        {"user": "Developer2", "text": "The API endpoint /api/process-payment is returning 504"},
        {"user": "Developer1", "text": "We need to increase the timeout and add retry logic"}
    ]
    
    # Parse bug report
    bug_report = service.parse_bug_report(conversation)
    
    print("\n   Parsed Bug Report:")
    print(f"   Title: {bug_report.get('title', 'N/A')}")
    print(f"   Severity: {bug_report.get('severity', 'N/A')}")
    print(f"   Components: {', '.join(bug_report.get('affected_components', []))}")
    
    # Test Deimos routing
    deimos = DeimosService()
    model = deimos.route_task("generate_code_fix", "high")
    print(f"\n   Selected Model: {model}")
    
    return True

def main():
    """Main test runner."""
    print("""
╔══════════════════════════════════════╗
║   🧪 Lattice Bot Component Tests     ║
╚══════════════════════════════════════╝
    """)
    
    # Validate config first
    if not Config.validate():
        print("\n❌ Configuration validation failed")
        print("Please check your .env file")
        return False
    
    tester = ComponentTester()
    
    # Run tests
    tester.test("Configuration", test_config)
    tester.test("Cohere Service", test_cohere_service)
    tester.test("Deimos Service", test_deimos_service)
    tester.test("Jira Tool", test_jira_tool)
    tester.test("GitHub Tool", test_github_tool)
    tester.test("MCP Server", test_mcp_server)
    tester.test("Sample Workflow", test_sample_workflow)
    
    # Print summary
    success = tester.print_summary()
    
    if success:
        print("\n✅ All tests passed! System is ready.")
        print("\nNext steps:")
        print("1. Configure Slack tokens in .env")
        print("2. Run: python slack_bot.py")
    else:
        print("\n⚠️ Some tests failed. Please fix issues above.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
