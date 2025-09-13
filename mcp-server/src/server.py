import asyncio
import os
from typing import Any, Sequence
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
  Resource,
  Tools,
  TextContent,
  ImageContent,
  EmbeddedResource,
)

from utils.logger import logger
from tools.analyze_request import analyze_request_tool

load_dotenv()

server = Server("lattice")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
  return [
    Tool(
      name="analyze_request"
      description="Analyze a ticket request and extract structured information",
      inputSchema={
        "type": "object",
        "properties": {
          "title": "string",
          "description": "Ticket title",
        },
        "description": {
          "type": "string",
          "description": "Detailed ticket description"
        },
        "severity": {
          "type": "string",
          "enum": ["high", "medium", "low"]
          "description": "Ticket severity level"
        },
        "labels": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Ticket labels"
        },
        "user_id": {
          "type": "string",
          "description": "Slack user ID"
        },
        "channel_id": {
          "type": "string",
          "description": "Slack channel ID"
        },
        "autofix_enabled": {
          "type": "boolean",
          "description": "Whether to attempt automatic fix"
        }
      },
      "required": ["title", "description", "user_id", "channel_id"]
    )
  ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
  logger.info(f"Executing tool: {name} with arguments: {arguments}")

  try:
    if name == "analyze_request":
      result = await analyze_request_tool(arguments)
      return [TextContent(type="text", text=result.model_dump_json(indent=2))]
    else:
      raise ValueError(f"Unknown tool: {name}")
  
  except Exception as e:
    logger.error(f"Error executing tool {name}: {str(e)}")
    return [TextContent(type="text", text=f"Error: {str(e)}")]

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
  return []

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
  raise NotImplementedError("Resoruce reading not yet implemented")

async def main():
  logger.info("Starting MCP server...")

  logger.info(f"Server name: lattice")
  logger.info(f"Available tools: analyze_request")
  logger.info(f"Transport: stdio")

  async with stdio_server() as (read_stream, write_stream):
    await server.run(
      read_stream,
      write_stream,
      InitializationOptions(
        name="lattice",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
          notification_options=None,
          experimental_capabilities=None,
        ),
      ),
    )

if __name__ == "__main__":
  logger.info("MCP Server starting up...")
  asyncio.run(main())