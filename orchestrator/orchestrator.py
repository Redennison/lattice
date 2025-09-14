"""
Main orchestrator for coordinating LLM and MCP server interactions
"""

import asyncio
import json
from typing import Dict, Any
from dotenv import load_dotenv
import cohere
from .mcp_client import MCPClient

# Load .env from the root directory
load_dotenv('../lattice/.env')

class Orchestrator:
    """Orchestrates LLM interactions with MCP server tools"""
    
    def __init__(self, mcp_server_path: str = "/Users/Evan/lattice/mcp-server/src/server.py"):
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
        
        try:
            # Step 1: Discover available tools from MCP server
            print("🔍 Discovering available MCP tools...")
            available_tools = await self.mcp_client.list_tools()
            print(f"📋 Available tools: {available_tools}")
            
            # Step 2: Use LLM to analyze the request and determine what tools to use
            tools_description = self._format_tools_for_llm(available_tools)
            analysis_prompt = f"""
            Analyze this Slack message and determine what actions should be taken:
            
            Message: {text}
            User: {user_id}
            Channel: {channel_id}
            
            Available MCP tools:
            {tools_description}
            
            Respond with a JSON object indicating:
            1. "user_intent": What the user is asking for
            2. "tools_needed": List of tool names that should be called (empty if none needed)
            3. "reasoning": Brief explanation of why these tools were selected
            
            If this is just a general question or greeting, set tools_needed to an empty list.
            """
            
            # Get LLM analysis
            analysis_response = self.cohere_client.chat(
                model="command-r-plus",
                message=analysis_prompt,
                max_tokens=500
            )
            
            analysis_text = analysis_response.text
            print(f"🤖 LLM Analysis: {analysis_text}")
            
            # Parse the analysis to determine if tools are needed
            if "tools_needed" in analysis_text and "[]" not in analysis_text:
                # Tools are needed - execute MCP workflow
                return await self._execute_mcp_workflow(text, user_id, channel_id, analysis_text, available_tools)
            else:
                # Simple conversational response
                return await self._generate_conversational_response(text)
                
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
    
    def _format_tools_for_llm(self, tools_response: Dict[str, Any]) -> str:
        """Format available tools for LLM consumption"""
        if not tools_response or "tools" not in tools_response:
            return "No tools available"
        
        tools = tools_response["tools"]
        formatted = []
        
        for tool in tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "No description")
            formatted.append(f"- {name}: {description}")
        
        return "\n".join(formatted)
    
    async def _execute_mcp_workflow(self, text: str, user_id: str, channel_id: str, analysis: str, available_tools: Dict[str, Any]) -> str:
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
