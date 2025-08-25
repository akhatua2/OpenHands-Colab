#!/usr/bin/env python3
"""
Minimal MCP server for OpenHands multi-agent collaboration.
Provides send() and get_messages() tools for non-blocking status sharing.
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List
from datetime import datetime

# Set up detailed logging - focus on DEBUG/ERROR only
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler(sys.stderr)
    ]
)
# Suppress INFO messages in console output
logging.getLogger().handlers[1].setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

# Simple in-memory message storage
messages: List[Dict[str, Any]] = []
message_readers: Dict[str, int] = {}  # agent_id -> last_read_index


async def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP requests according to the protocol."""
    method = request.get("method", "")
    params = request.get("params", {})

    logger.info(f"📥 Received MCP request: {method}")
    logger.debug(f"Request details: {json.dumps(request, indent=2)}")

    if method == "initialize":
        logger.info("🚀 Initializing MCP server")
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "collaboration-server",
                    "version": "1.0.0"
                }
            }
        }
        logger.debug(f"Initialize response: {json.dumps(response, indent=2)}")
        return response

    elif method == "tools/list":
        logger.info("🔧 Listing available tools")
        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                        "tools": [
            {
                "name": "send",
                "description": "Send a status message to other agents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Status message to share"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Agent identifier (1, 2, 3, etc.)"
                        }
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "get_messages",
                "description": "Get unread messages from other agents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Requesting agent identifier"
                        }
                    },
                    "required": ["agent_id"]
                }
                        }
        ]
            }
        }
        logger.info("Available tools: send, get_messages")
        return response

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        logger.info(f"🛠️ Tool call: {tool_name}")
        logger.debug(f"Tool arguments: {json.dumps(arguments, indent=2)}")

        if tool_name == "send":
            # Store message with timestamp
            # agent_id is now required
            message = {
                "sender": arguments.get("agent_id", "unknown"),
                "message": arguments.get("message", ""),
                "timestamp": datetime.now().isoformat()
            }
            messages.append(message)

            logger.info(f"📤 Message stored from {message['sender']}: {message['message']}")
            logger.info(f"📊 Total messages in storage: {len(messages)}")

            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✅ Message sent: {message['message']}"
                        }
                    ]
                }
            }
            logger.debug(f"Send response: {json.dumps(response, indent=2)}")
            return response

        elif tool_name == "get_messages":
            agent_id = arguments.get("agent_id", "unknown")
            last_read = message_readers.get(agent_id, 0)

            logger.info(f"📥 Getting messages for {agent_id}, last_read: {last_read}")

            # Get unread messages from other agents
            unread = [
                msg for i, msg in enumerate(messages[last_read:], last_read)
                if msg["sender"] != agent_id
            ]

            logger.info(f"📨 Found {len(unread)} unread messages for {agent_id}")
            for msg in unread:
                logger.debug(f"  - {msg['sender']}: {msg['message']} ({msg['timestamp']})")

            # Update read position
            message_readers[agent_id] = len(messages)
            logger.debug(f"Updated read position for {agent_id} to {len(messages)}")

            if unread:
                content = "\n".join([
                    f"[STATUS] {msg['sender']}: {msg['message']}"
                    for msg in unread
                ])
            else:
                content = ""
                logger.info(f"No new messages for {agent_id}")

            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": content
                        }
                    ]
                }
            }
            logger.debug(f"Get messages response: {json.dumps(response, indent=2)}")
            return response

    # Default response
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }


async def main():
    """Run the MCP server using stdio."""
    logger.info("🚀 Starting MCP Collaboration Server")
    logger.info("📝 Logs will be written to mcp_server.log")

    while True:
        try:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                logger.info("📴 End of input received, shutting down")
                break

            logger.debug(f"📨 Raw input: {line.strip()}")
            request = json.loads(line.strip())
            response = await handle_mcp_request(request)

            # Send response to stdout
            response_json = json.dumps(response)
            print(response_json, flush=True)
            logger.debug(f"📤 Raw output: {response_json}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            # Send error response
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
