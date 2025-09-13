"""
Main orchestrator for coordinating LLM and MCP server interactions
"""

import asyncio
import json
from typing import Dict, Any, Optional
import cohere
from .mcp_client import MCPClient

class Orchestrator:
    """Orchestrates LLM interactions with MCP server tools"""
    
    def __init__(self, mcp_server_path: str = "../mcp-server/src/server.py"):
        self.cohere_client = cohere.Client()
        self.mcp_client = MCPClient(mcp_server_path)
        
    async def process_slack_mention(self, text: str, user_id: str, channel_id: str) -> str:
        """
        Process a Slack mention by coordinating LLM and MCP tools
        
        Args:
            text: The Slack message text
            user_id: Slack user ID
            channel_id: Slack channel ID
            
        Returns:
            Response text to send back to Slack
        """
        
        # Step 1: Use LLM to analyze the request and determine what tools to use
        analysis_prompt = f"""
        Analyze this Slack message and determine what actions should be taken:
        
        Message: {text}
        User: {user_id}
        Channel: {channel_id}
        
        Available MCP tools:
        - analyze_request: Analyze and extract structured ticket information
        - plan_fix: Create technical fix plans
        - jira_create_issue: Create Jira tickets
        - github_branch_and_pr: Create branches and PRs
        
        Respond with a JSON object indicating:
        1. What the user is asking for
        2. Which tools should be called and in what order
        3. Any parameters needed for the tools
        
        If this is just a general question or greeting, indicate no tools are needed.
        """
        
        try:
            # Get LLM analysis
            analysis_response = self.cohere_client.chat(
                model="command-r-plus",
                message=analysis_prompt,
                max_tokens=500
            )
            
            # Parse the analysis (simplified - in production you'd want better parsing)
            analysis_text = analysis_response.text
            
            # Check if tools are needed
            if "no tools" in analysis_text.lower() or "general" in analysis_text.lower():
                # Simple conversational response
                return await self._generate_conversational_response(text)
            else:
                # Use MCP tools for complex requests
                return await self._execute_mcp_workflow(text, user_id, channel_id, analysis_text)
                
        except Exception as e:
            return f"❌ Error processing request: {str(e)}"
    
    async def _generate_conversational_response(self, text: str) -> str:
        """Generate a simple conversational response using LLM"""
        prompt = f"You are a helpful assistant in a Slack channel. A user mentioned you with: '{text}'. Please provide a helpful response."
        
        response = self.cohere_client.chat(
            model="command-r-plus",
            message=prompt,
            max_tokens=300
        )
        
        return response.text
    
    async def _execute_mcp_workflow(self, text: str, user_id: str, channel_id: str, analysis: str) -> str:
        """Execute MCP server workflow based on analysis"""
        
        try:
            # For now, start with analyze_request tool
            result = await self.mcp_client.analyze_slack_context(
                context={"messages": [{"text": text, "user": user_id}]},
                user_id=user_id,
                channel_id=channel_id
            )
            
            # Format the result for Slack
            if result:
                return f"🎯 **Analysis Complete**\n```json\n{json.dumps(result, indent=2)}\n```"
            else:
                return "✅ Request processed successfully"
                
        except Exception as e:
            return f"❌ Error executing workflow: {str(e)}"
    
    async def close(self):
        """Clean up resources"""
        if self.mcp_client:
            await self.mcp_client.close()
