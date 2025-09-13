"""
Handler for Slack app mention events
"""

import asyncio
import sys
import os

# Add orchestrator to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

from orchestrator import Orchestrator

# Initialize orchestrator
orchestrator = Orchestrator()

def handle_app_mention(event, say, client):
    """Handle when the bot is mentioned"""
    text = event['text']
    channel = event['channel']
    ts = event['ts']
    user = event['user']
    
    # Use orchestrator to process the mention
    try:
        # Run async orchestrator in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        response_text = loop.run_until_complete(
            orchestrator.process_slack_mention(text, user, channel)
        )
        
        client.chat_postMessage(
            channel=channel,
            text=response_text,
            thread_ts=ts
        )
        
        loop.close()
        
    except Exception as e:
        print(f"Error processing with orchestrator: {e}")
        client.chat_postMessage(
            channel=channel,
            text=f"❌ Error processing request: {str(e)}",
            thread_ts=ts
        )
