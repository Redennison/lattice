"""
MCP Client for communicating with the MCP server
"""

import asyncio
import json
import itertools
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class MCPClient:
    """Client for communicating with MCP server via JSON-RPC"""
    
    def __init__(self, server_path: str = "../mcp-server/src/server.py"):
        self.server_path = str(Path(server_path).expanduser().resolve())
        self.process = None
        self._id_gen = itertools.count(1)
        self._pending = {}  # id -> future
        
    async def start_server(self):
        """Start the MCP server process and perform handshake"""
        if self.process:
            return
        
        try:
            # Validate path
            if not os.path.isfile(self.server_path):
                raise FileNotFoundError(f"MCP server script not found: {self.server_path}")
            
            print("CWD:", os.getcwd())
            print("Resolved server_path:", self.server_path)
            
            # Start MCP server process with absolute path, no cwd
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # no cwd here
            )
            
            # Start background reader
            asyncio.create_task(self._reader())
            
            # --- MCP handshake ---
            init_id = await self._send({
                "jsonrpc": "2.0",
                "id": next(self._id_gen),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": { "roots": {}, "tools": {}, "resources": {} },
                    "clientInfo": {"name": "lattice-client", "version": "1.0.0"},
                }
            })
            await self._await(init_id)  # wait for initialize result
            
            # notify initialized (no id; it's a notification)
            await self._write({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {}
            })
            
        except Exception as e:
            raise Exception(f"Failed to start MCP server: {e}")
    
    async def list_tools(self) -> Dict[str, Any]:
        """Get list of available tools from MCP server"""
        await self.start_server()
        msg_id = await self._send({
            "jsonrpc": "2.0",
            "id": next(self._id_gen),
            "method": "tools/list",
            "params": {}
        })
        resp = await self._await(msg_id)
        return resp.get("result", {})

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        await self.start_server()
        msg_id = await self._send({
            "jsonrpc": "2.0",
            "id": next(self._id_gen),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        })
        resp = await self._await(msg_id)
        return resp.get("result", {})

    async def _send(self, obj):
        """Send a message and return the message ID for awaiting response"""
        msg_id = obj.get("id")
        if msg_id is None:
            # notification; no future to await
            await self._write(obj)
            return None
        fut = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = fut
        await self._write(obj)
        return msg_id

    async def _write(self, obj):
        """Write a JSON object to the server"""
        line = json.dumps(obj) + "\n"
        self.process.stdin.write(line.encode())
        await self.process.stdin.drain()

    async def _await(self, msg_id):
        """Wait for a response with the given message ID"""
        fut = self._pending[msg_id]
        return await fut

    async def _reader(self):
        """Background reader for server responses"""
        # read BOTH stdout and stderr (stderr just log-print)
        async def read_stdout():
            while True:
                line_b = await self.process.stdout.readline()
                if not line_b:
                    break
                line = line_b.decode().strip()
                if not line:
                    continue
                # ignore non-JSON lines
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # notifications have no id
                if "id" in obj and obj["id"] in self._pending:
                    fut = self._pending.pop(obj["id"])
                    fut.set_result(obj)
                # else: it's a notification; you could handle logs/progress here

        async def read_stderr():
            while True:
                e = await self.process.stderr.readline()
                if not e:
                    break
                print("MCP[stderr]:", e.decode().rstrip())

        await asyncio.gather(read_stdout(), read_stderr())
    
    async def analyze_slack_context(self, context: Dict[str, Any], user_id: str, channel_id: str) -> Dict[str, Any]:
        """Analyze Slack context using MCP server"""
        
        # Convert context messages to conversation text
        messages = context.get('messages', [])
        conversation = self._format_messages_for_analysis(messages)
        
        # Extract basic info from messages using simple parsing
        parsed_info = self._extract_parsed_info_from_messages(messages)
        
        # Prepare arguments matching the analyze_request tool schema
        arguments = {
            "slack_context": {
                "conversation": conversation,
                "thread_messages": messages,
                "channel_id": channel_id,
                "user_id": user_id,
                "timestamp": str(int(__import__('time').time())),
                "attachments": []
            },
            "parsed_info": parsed_info,
            "severity": "medium"
        }
        
        print(f"🔍 Sending arguments to MCP server:")
        print(json.dumps(arguments, indent=2))
        
        return await self.call_tool("analyze_request", arguments)
    
    def _format_messages_for_analysis(self, messages: list) -> str:
        """Format Slack messages into a description for analysis"""
        formatted = []
        
        for msg in messages:
            user = msg.get('user', 'unknown')
            text = msg.get('text', '')
            formatted.append(f"[{user}]: {text}")
        
        return "\n".join(formatted)
    
    def _extract_parsed_info_from_messages(self, messages: list) -> Dict[str, Any]:
        """Extract parsed info structure from messages for analyze_request tool"""
        conversation = self._format_messages_for_analysis(messages)
        
        # Simple keyword detection
        detected_keywords = []
        error_messages = []
        mentioned_files = []
        urgency_indicators = []
        
        # Look for common technical keywords
        tech_keywords = ['error', 'bug', 'issue', 'problem', 'fix', 'broken', 'fail', 'crash', 'exception']
        for keyword in tech_keywords:
            if keyword.lower() in conversation.lower():
                detected_keywords.append(keyword)
        
        # Look for file mentions (simple pattern matching)
        import re
        file_patterns = [r'\w+\.\w+', r'\/[\w\/]+\.\w+']
        for pattern in file_patterns:
            matches = re.findall(pattern, conversation)
            mentioned_files.extend(matches)
        
        # Look for error patterns
        error_patterns = ['error:', 'exception:', 'traceback', 'failed']
        for line in conversation.split('\n'):
            for pattern in error_patterns:
                if pattern.lower() in line.lower():
                    error_messages.append(line.strip())
        
        # Look for urgency indicators
        urgency_words = ['urgent', 'critical', 'asap', 'immediately', 'emergency', 'broken', 'down']
        for word in urgency_words:
            if word.lower() in conversation.lower():
                urgency_indicators.append(word)
        
        # Generate initial summary (first 100 chars of conversation)
        initial_summary = conversation[:100].strip()
        if len(conversation) > 100:
            initial_summary += "..."
        
        # Determine user intent
        user_intent = "Request assistance with technical issue"
        if any(word in conversation.lower() for word in ['fix', 'solve', 'resolve']):
            user_intent = "Fix or resolve an issue"
        elif any(word in conversation.lower() for word in ['create', 'build', 'make']):
            user_intent = "Create or build something"
        elif any(word in conversation.lower() for word in ['help', 'question', 'how']):
            user_intent = "Get help or ask a question"
        
        return {
            "initial_summary": initial_summary,
            "detected_keywords": list(set(detected_keywords))[:10],  # Limit to 10
            "mentioned_files": list(set(mentioned_files))[:10],      # Limit to 10
            "error_messages": list(set(error_messages))[:5],         # Limit to 5
            "user_intent": user_intent,
            "urgency_indicators": list(set(urgency_indicators))
        }
    
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
