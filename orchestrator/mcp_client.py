"""
MCP Client for communicating with the MCP server
"""

import asyncio
import json
import subprocess
import os
from typing import Dict, Any, Optional

class MCPClient:
    """Client for communicating with MCP server"""
    
    def __init__(self, server_path: str = "../mcp-server/src/server.py"):
        self.server_path = server_path
        self.process = None
        
    async def start_server(self):
        """Start the MCP server process"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                "python", self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(self.server_path)
            )
        except Exception as e:
            raise Exception(f"Failed to start MCP server: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        if not self.process:
            await self.start_server()
        
        # Prepare MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            # Send request to server
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                raise Exception(f"MCP server error: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            raise Exception(f"Error calling MCP tool {tool_name}: {e}")
    
    async def analyze_slack_context(self, context: Dict[str, Any], user_id: str, channel_id: str) -> Dict[str, Any]:
        """Analyze Slack context using MCP server"""
        
        # Convert context messages to description
        messages = context.get('messages', [])
        description = self._format_messages_for_analysis(messages)
        
        # Extract title from first message or use default
        title = self._extract_title_from_messages(messages)
        
        # Prepare arguments for analyze_request tool
        arguments = {
            "title": title,
            "description": description,
            "user_id": user_id,
            "channel_id": channel_id,
            "severity": "medium",
            "labels": [],
            "autofix_enabled": True
        }
        
        return await self.call_tool("analyze_request", arguments)
    
    def _format_messages_for_analysis(self, messages: list) -> str:
        """Format Slack messages into a description for analysis"""
        formatted = []
        
        for msg in messages:
            user = msg.get('user', 'unknown')
            text = msg.get('text', '')
            formatted.append(f"[{user}]: {text}")
        
        return "\n".join(formatted)
    
    def _extract_title_from_messages(self, messages: list) -> str:
        """Extract a meaningful title from the first few messages"""
        if not messages:
            return "Slack Issue"
        
        # Use first non-empty message as basis for title
        for msg in messages[:3]:
            text = msg.get('text', '').strip()
            if text and len(text) > 10:
                # Truncate and clean up for title
                title = text[:60].strip()
                if len(text) > 60:
                    title += "..."
                return title
        
        return "Slack Issue"
    
    async def close(self):
        """Close the MCP server process"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
