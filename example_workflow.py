#!/usr/bin/env python3
"""Example workflow demonstrating the complete bug fix pipeline."""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List

from config import Config
from mcp_server import MCPServer

async def run_example_workflow():
    """Run an example bug fix workflow."""
    
    print("""
╔══════════════════════════════════════╗
║   🚀 Example Workflow Demo           ║
║   Automated Bug Fix Pipeline         ║
╚══════════════════════════════════════╝
    """)
    
    # Example bug conversation from Slack
    example_conversation = [
        {
            "user": "Sarah Chen",
            "text": "We have a critical issue in production with the payment processing"
        },
        {
            "user": "Mike Johnson",
            "text": "I'm seeing timeout errors after 30 seconds on the /api/process-payment endpoint"
        },
        {
            "user": "Sarah Chen", 
            "text": "It looks like the issue is in the payment_gateway.py file, the timeout is set too low"
        },
        {
            "user": "Mike Johnson",
            "text": "Yes, and we're not handling the retry logic properly when the payment provider is slow"
        },
        {
            "user": "Sarah Chen",
            "text": "We need to increase the timeout to 60 seconds and add exponential backoff for retries"
        },
        {
            "user": "Alex Kumar",
            "text": "This is affecting about 15% of our transactions right now"
        }
    ]
    
    print("\n📝 Example Slack Conversation:")
    print("-" * 50)
    for msg in example_conversation:
        print(f"{msg['user']}: {msg['text']}")
    print("-" * 50)
    
    # Initialize MCP server
    print("\n🔧 Initializing MCP Server...")
    mcp_server = MCPServer()
    
    # Process the conversation
    print("\n🤖 Processing conversation through Lattice Bot workflow...")
    print("This will:")
    print("  1. Parse the bug report using Cohere")
    print("  2. Create a Jira ticket")
    print("  3. Analyze the codebase")
    print("  4. Generate a fix")
    print("  5. Create a GitHub PR")
    
    input("\nPress Enter to start the workflow (or Ctrl+C to cancel)...")
    
    try:
        # Run the workflow
        result = await mcp_server.process_slack_conversation(
            conversation=example_conversation,
            channel_id="C123456789",  # Example channel ID
            thread_ts="1234567890.123456"  # Example thread timestamp
        )
        
        # Display results
        print("\n" + "="*50)
        print("WORKFLOW RESULTS")
        print("="*50)
        
        if result['success']:
            print("\n✅ Workflow completed successfully!")
            print(f"\n📋 Jira Ticket: {result.get('issue_key', 'N/A')}")
            print(f"   URL: {result.get('issue_url', 'N/A')}")
            print(f"   Title: {result.get('bug_title', 'N/A')}")
            print(f"   Severity: {result.get('severity', 'N/A')}")
            
            if result.get('pr_url'):
                print(f"\n🔧 GitHub PR: {result.get('pr_url')}")
                print("   Status: Ready for review")
            else:
                print("\n⚠️ No automated fix generated")
                print("   Manual investigation required")
            
            if result.get('similar_issues'):
                print(f"\n📊 Found {len(result['similar_issues'])} similar issues:")
                for issue in result['similar_issues'][:3]:
                    print(f"   - {issue['key']}: {issue['summary']}")
            
            # Show workflow details
            workflow_id = result.get('workflow_id')
            if workflow_id:
                status = mcp_server.get_workflow_status(workflow_id)
                if status:
                    print(f"\n📈 Workflow Steps:")
                    for step in status.get('steps', []):
                        icon = "✅" if 'completed' in step['status'] or 'created' in step['status'] else "🔄"
                        print(f"   {icon} {step['status']}")
                        if step.get('data'):
                            for key, value in step['data'].items():
                                print(f"      • {key}: {value}")
        else:
            print(f"\n❌ Workflow failed: {result.get('error', 'Unknown error')}")
            print("\nThis might be due to:")
            print("  - Invalid API credentials")
            print("  - Network connectivity issues")
            print("  - Repository access problems")
            print("\nPlease check your .env configuration and try again")
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Workflow cancelled by user")
    except Exception as e:
        print(f"\n❌ Error running workflow: {str(e)}")
        print("\nPlease ensure:")
        print("  1. All API keys are configured in .env")
        print("  2. You have access to the configured Jira project")
        print("  3. You have access to the configured GitHub repository")

def main():
    """Main entry point."""
    # Check configuration
    if not Config.validate():
        print("\n❌ Configuration validation failed")
        print("Please ensure all required values are set in .env")
        print("\nRequired:")
        print("  - CO_API_KEY (Cohere)")
        print("  - JIRA_* settings")
        print("  - GITHUB_* settings")
        return
    
    # Run the example
    asyncio.run(run_example_workflow())
    
    print("\n" + "="*50)
    print("\n🎉 Example workflow complete!")
    print("\nNext steps:")
    print("  1. Configure Slack tokens in .env")
    print("  2. Run: python slack_bot.py")
    print("  3. Mention @Lattice in a Slack thread")
    print("\nFor more details, see README.md")

if __name__ == "__main__":
    main()
