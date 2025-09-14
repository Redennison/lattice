#!/usr/bin/env python3
"""Debug script to find the 'file' is not defined error."""

import asyncio
from mcp_server import MCPServer

async def test_workflow():
    """Test the workflow with a simple request."""
    
    server = MCPServer()
    
    # Simple test conversation
    conversation = [{
        "user": "Test User",
        "text": "make the login button blue instead of red on the homepage navbar. This is a Next.js project with Tailwind CSS"
    }]
    
    try:
        result = await server.process_slack_conversation(
            conversation=conversation,
            channel_id="test_channel",
            thread_ts="test_thread"
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_workflow())
