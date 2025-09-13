import asyncio
import os
from typing import Any, Sequence
from dotenv import load_dotenv

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
  Resource,
  Tool,
  TextContent,
  ImageContent,
  EmbeddedResource,
)

from utils.logger import logger
from tools.analyze_request import analyze_request_tool
from tools.plan_fix import plan_fix_tool
from tools.jira_create_issue import jira_create_issue_tool
from tools.github_branch_and_pr import github_branch_and_pr_tool

load_dotenv()

server = Server("lattice")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
  return [
    Tool(
      name="analyze_request",
      description="Analyze a ticket request and extract structured information",
      inputSchema={
        "type": "object",
        "properties": {
          "slack_context": {
            "type": "object",
            "description": "Raw Slack conversation context",
            "properties": {
              "conversation": {"type": "string", "description": "Full conversation text"},
              "thread_messages": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Thread messages if applicable"
              },
              "channel_id": {"type": "string", "description": "Slack channel ID"},
              "user_id": {"type": "string", "description": "Slack user ID"},
              "timestamp": {"type": "string", "description": "Message timestamp"},
              "attachments": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Images, files, etc."
              }
            },
            "required": ["conversation", "channel_id", "user_id", "timestamp"]
          },
          "parsed_info": {
            "type": "object",
            "description": "Information parsed from Slack by initial LLM",
            "properties": {
              "initial_summary": {"type": "string", "description": "Quick summary of the issue"},
              "detected_keywords": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key technical terms found"
              },
              "mentioned_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files mentioned in conversation"
              },
              "error_messages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Error messages found"
              },
              "user_intent": {"type": "string", "description": "What the user is trying to achieve"},
              "urgency_indicators": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Words indicating urgency"
              }
            },
            "required": ["initial_summary", "detected_keywords", "mentioned_files", "error_messages", "user_intent", "urgency_indicators"]
          },
          "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"],
            "description": "Issue severity level",
            "default": "medium"
          }
        },
        "required": ["slack_context", "parsed_info"]
      },
    ),
    Tool(
      name="plan_fix",
      description="Plan a fix for a ticket",
      inputSchema={
        "type": "object",
        "properties": {
          "analysis_result": {
            "type": "object",
            "description": "Analysis result from analyze_request tool"
          }
        },
        "required": ["analysis_result"]
      }
    ),
    Tool(
      name="jira_create_issue",
      description="Create a Jira issue from analysis results",
      inputSchema={
        "type": "object",
        "properties": {
          "analysis_result": {
            "type": "object",
            "description": "Analysis result from analyze_request tool"
          },
          "user_id": {
            "type": "string",
            "description": "Slack user ID for assignment"
          }
        },
        "required": ["analysis_result"]
      }
    ),
    Tool(
      name="github_branch_and_pr",
      description="Create branch, apply fixes, and open pull request",
      inputSchema={
        "type": "object",
        "properties": {
          "fix_plan": {
            "type": "object",
            "description": "Fix plan from plan_fix tool"
          },
          "jira_issue": {
            "type": "object",
            "description": "Jira issue from jira_create_issue tool"
          },
          "base_branch": {
            "type": "string",
            "description": "Base branch name",
            "default": "main"
          }
        },
        "required": ["fix_plan"]
      }
    )
  ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
  logger.info(f"Executing tool: {name} with arguments: {arguments}")

  try:
    if name == "analyze_request":
      result = await analyze_request_tool(arguments)
      return [TextContent(type="text", text=result.model_dump_json(indent=2))]
    elif name == "plan_fix":
      result = await plan_fix_tool(arguments)
      return [TextContent(type="text", text=result.model_dump_json(indent=2))]
    elif name == "jira_create_issue":
      result = await jira_create_issue_tool(arguments)
      return [TextContent(type="text", text=result.model_dump_json(indent=2))]
    elif name == "github_branch_and_pr":
      result = await github_branch_and_pr_tool(arguments)
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
  raise NotImplementedError("Resource reading not yet implemented")

async def main():
  logger.info("Starting MCP server...")

  logger.info(f"Server name: lattice")
  logger.info(f"Available tools: analyze_request, plan_fix, jira_create_issue, github_branch_and_pr")
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