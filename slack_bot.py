"""Slack bot for handling @Lattice mentions and triggering bug fix workflow."""

import os
import re
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.errors import SlackApiError

from config import Config
from mcp_server import MCPServer

class LatticeSlackBot:
    """Slack bot for handling bug reports and fixes."""
    
    def __init__(self):
        """Initialize Slack bot."""
        # Initialize Slack app
        self.app = AsyncApp(
            token=Config.SLACK_BOT_TOKEN,
            signing_secret=Config.SLACK_SIGNING_SECRET
        )
        
        # Initialize MCP server
        self.mcp_server = MCPServer()
        
        # Track processing threads to avoid duplicates
        self.processing_threads = set()
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register Slack event handlers."""
        
        @self.app.event("app_mention")
        async def handle_app_mention(event, say, client):
            """Handle @Lattice mentions."""
            await self._process_mention(event, say, client)
        
        @self.app.event("message")
        async def handle_message(event, say, client):
            """Handle direct messages to the bot."""
            # Only process if it's a DM to the bot
            if event.get("channel_type") == "im":
                await self._process_direct_message(event, say, client)
    
    async def _process_mention(self, event: Dict[str, Any], say, client):
        """Process @Lattice mention in a channel.
        
        Args:
            event: Slack event data
            say: Slack say function
            client: Slack client
        """
        print(f"=== PROCESSING MENTION ===")
        print(f"Event: {event}")
        
        try:
            channel = event.get("channel")
            thread_ts = event.get("thread_ts") or event.get("ts")
            user = event.get("user")
            text = event.get("text", "")
            
            print(f"Channel: {channel}, Thread: {thread_ts}, User: {user}")
            print(f"Text: {text}")
            
            # Check if we're already processing this thread
            thread_id = f"{channel}_{thread_ts}"
            if thread_id in self.processing_threads:
                await say(
                    text="🔄 Already processing this thread...",
                    thread_ts=thread_ts
                )
                return
            
            self.processing_threads.add(thread_id)
            
            # Send initial acknowledgment
            ack_message = await say(
                text="👀 Looking at this thread...\n_Analyzing conversation and preparing to create a fix_",
                thread_ts=thread_ts
            )
            
            try:
                print("=== STARTING CONVERSATION PROCESSING ===")
                # Get thread messages
                print(f"Getting thread messages for channel={channel}, thread_ts={thread_ts}")
                conversation = await self._get_thread_messages(client, channel, thread_ts)
                print(f"Found {len(conversation)} messages in thread")
                print(f"Conversation content: {conversation}")
                
                # If single message, use the mention text as context
                if len(conversation) == 0:
                    print("No thread messages, extracting from mention")
                    # Extract text from the mention itself
                    try:
                        auth_info = await client.auth_test()
                        bot_id = auth_info["user_id"]
                        mention_text = text.replace(f'<@{bot_id}>', '').strip()
                        print(f"Extracted mention text: {mention_text[:100]}...")
                    except Exception as e:
                        print(f"Auth test failed: {e}")
                        # Fallback: just remove any @mentions
                        import re
                        mention_text = re.sub(r'<@[A-Z0-9]+>', '', text).strip()
                        print(f"Fallback mention text: {mention_text[:100]}...")
                    
                    if mention_text:
                        # Get user info
                        try:
                            user_info = await client.users_info(user=user)
                            username = user_info["user"]["real_name"] or user_info["user"]["name"]
                        except:
                            username = f"User_{user[:8]}"
                        
                        conversation = [{
                            "user": username,
                            "text": mention_text,
                            "ts": event.get("ts")
                        }]
                        print(f"Created conversation with 1 message")
                
                if len(conversation) < 1:
                    await client.chat_update(
                        channel=channel,
                        ts=ack_message["ts"],
                        text="❌ Please provide more context about the issue. Create a thread with details, then mention me."
                    )
                    return
                
                # Update status
                await client.chat_update(
                    channel=channel,
                    ts=ack_message["ts"],
                    text="🔍 Parsing bug report from conversation..."
                )
                
                print(f"Processing conversation with {len(conversation)} messages")
                print(f"About to call MCP server...")
                
                # Process through MCP server
                try:
                    result = await self.mcp_server.process_slack_conversation(
                        conversation=conversation,
                        channel_id=channel,
                        thread_ts=thread_ts
                    )
                    print(f"MCP server returned: {result}")
                except Exception as mcp_error:
                    print(f"!!! MCP SERVER ERROR: {mcp_error}")
                    import traceback
                    traceback.print_exc()
                    raise
                
                # Send result
                if result['success']:
                    response = self._format_success_response(result)
                else:
                    response = self._format_error_response(result)
                
                await client.chat_update(
                    channel=channel,
                    ts=ack_message["ts"],
                    text=response
                )
                
            finally:
                # Remove from processing set
                self.processing_threads.discard(thread_id)
                
        except Exception as e:
            print(f"Error processing mention: {e}")
            await say(
                text=f"❌ Error: {str(e)}",
                thread_ts=thread_ts
            )
    
    async def _process_direct_message(self, event: Dict[str, Any], say, client):
        """Process direct message to bot.
        
        Args:
            event: Slack event data
            say: Slack say function
            client: Slack client
        """
        text = event.get("text", "").lower()
        
        if "help" in text:
            await say(self._get_help_message())
        elif "status" in text:
            # Extract workflow ID if provided
            match = re.search(r'status\s+(\S+)', text)
            if match:
                workflow_id = match.group(1)
                status = self.mcp_server.get_workflow_status(workflow_id)
                if status:
                    await say(self._format_workflow_status(status))
                else:
                    await say(f"No workflow found with ID: {workflow_id}")
            else:
                await say("Please provide a workflow ID. Usage: `status <workflow_id>`")
        else:
            await say(self._get_help_message())
    
    async def _get_thread_messages(self, client, channel: str, thread_ts: str) -> List[Dict[str, str]]:
        """Get all messages from a thread.
        
        Args:
            client: Slack client
            channel: Channel ID
            thread_ts: Thread timestamp
            
        Returns:
            List of messages with user and text
        """
        try:
            # Get thread messages
            result = await client.conversations_replies(
                channel=channel,
                ts=thread_ts,
                limit=Config.MAX_THREAD_MESSAGES
            )
            
            messages = []
            
            for msg in result.get("messages", []):
                # Skip bot messages
                if msg.get("bot_id"):
                    continue
                
                # Get user info
                user_id = msg.get("user", "Unknown")
                try:
                    user_info = await client.users_info(user=user_id)
                    username = user_info["user"]["real_name"] or user_info["user"]["name"]
                except:
                    username = f"User_{user_id[:8]}"
                
                # Clean text (remove bot mentions)
                text = msg.get("text", "")
                text = re.sub(r'<@U[A-Z0-9]+>', '', text).strip()
                
                if text:
                    messages.append({
                        "user": username,
                        "text": text,
                        "ts": msg.get("ts")
                    })
            
            return messages
            
        except SlackApiError as e:
            print(f"Error getting thread messages: {e}")
            return []
    
    def _format_success_response(self, result: Dict[str, Any]) -> str:
        """Format successful workflow response.
        
        Args:
            result: Workflow result
            
        Returns:
            Formatted message
        """
        lines = [
            "✅ **Bug Report Processed Successfully!**",
            "",
            f"📝 **Jira Ticket:** [{result['issue_key']}]({result['issue_url']})",
            f"🏷️ **Severity:** {result.get('severity', 'Medium')}",
        ]
        
        if result.get('pr_url'):
            lines.append(f"🔧 **Pull Request:** [View PR]({result['pr_url']})")
            lines.append("")
            lines.append("_The PR has been created and is ready for review._")
        else:
            lines.append("")
            lines.append("_ℹ️ No automated fix could be generated. Manual investigation required._")
        
        if result.get('similar_issues'):
            lines.append("")
            lines.append("**Similar Issues Found:**")
            for issue in result['similar_issues'][:3]:
                lines.append(f"• {issue['key']}: {issue['summary']} ({issue['status']})")
        
        lines.append("")
        lines.append(f"_Workflow ID: `{result.get('workflow_id', 'N/A')}`_")
        
        return "\n".join(lines)
    
    def _format_error_response(self, result: Dict[str, Any]) -> str:
        """Format error response.
        
        Args:
            result: Error result
            
        Returns:
            Formatted error message
        """
        return f"""❌ **Failed to process bug report**

**Error:** {result.get('error', 'Unknown error')}

Please try again or create the ticket manually.

_Workflow ID: `{result.get('workflow_id', 'N/A')}`_"""
    
    def _format_workflow_status(self, status: Dict[str, Any]) -> str:
        """Format workflow status.
        
        Args:
            status: Workflow status
            
        Returns:
            Formatted status message
        """
        lines = [
            f"**Workflow Status:** {status.get('status', 'unknown')}",
            f"**Started:** {status.get('started_at', 'N/A')}",
            "",
            "**Steps:**"
        ]
        
        for step in status.get('steps', []):
            emoji = "✅" if "completed" in step['status'] else "🔄"
            lines.append(f"{emoji} {step['status']} - {step['timestamp']}")
        
        return "\n".join(lines)
    
    def _get_help_message(self) -> str:
        """Get help message.
        
        Returns:
            Help text
        """
        return """🤖 **Lattice Bot - Automated Bug Fix Assistant**

**How to use:**
1. Start or reply to a thread describing a bug
2. Mention @Lattice in the thread
3. I'll analyze the conversation and:
   • Create a Jira ticket
   • Analyze the codebase
   • Generate a fix (if possible)
   • Create a GitHub PR

**Commands (DM only):**
• `help` - Show this message
• `status <workflow_id>` - Check workflow status

**Tips:**
• Provide clear bug descriptions
• Mention affected files or components
• Include error messages or logs
• Describe expected vs actual behavior

_For best results, keep bug discussions focused and detailed._"""
    
    async def start(self):
        """Start the Slack bot."""
        try:
            # Validate configuration
            if not Config.SLACK_BOT_TOKEN:
                print("❌ SLACK_BOT_TOKEN not configured")
                print("Please set up a Slack app and add the token to .env")
                return
            
            if not Config.SLACK_APP_TOKEN:
                print("❌ SLACK_APP_TOKEN not configured")
                print("Please enable Socket Mode and add the app token to .env")
                return
            
            print("🚀 Starting Lattice Slack Bot...")
            
            # Start socket mode handler
            handler = AsyncSocketModeHandler(self.app, Config.SLACK_APP_TOKEN)
            await handler.start_async()
            
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            raise


async def main():
    """Main entry point."""
    # Validate configuration
    if not Config.validate():
        print("\n⚠️ Please configure the required environment variables in .env")
        return
    
    # Create and start bot
    bot = LatticeSlackBot()
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())
