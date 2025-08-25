#!/usr/bin/env python3
"""
Minimal MCP server for OpenHands multi-agent collaboration.
Provides send() and get_messages() tools for non-blocking status sharing.
"""

import asyncio
import json
import sys
import logging
import sqlite3
import os
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

# SQLite database for shared message storage across containers
DB_PATH = "./shared/collaboration.db"

def init_database():
    """Initialize SQLite database with messages table."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            read_by TEXT DEFAULT ''  -- JSON array of agent_ids who have read this message
        )
    ''')

    conn.commit()
    conn.close()
    logger.info(f"📊 Database initialized at {DB_PATH}")

def get_db_connection():
    """Get a database connection."""
    return sqlite3.connect(DB_PATH)


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
            # Store message in SQLite database
            sender = arguments.get("agent_id", "unknown")
            message_text = arguments.get("message", "")

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (sender, message) VALUES (?, ?)",
                (sender, message_text)
            )
            conn.commit()
            conn.close()

            logger.info(f"📤 Message stored in DB from {sender}: {message_text}")

            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"✅ Message sent: {message_text}"
                        }
                    ]
                }
            }
            logger.debug(f"Send response: {json.dumps(response, indent=2)}")
            return response

        elif tool_name == "get_messages":
            agent_id = arguments.get("agent_id", "unknown")

            logger.info(f"📥 Getting unread messages for {agent_id}")

            conn = get_db_connection()
            cursor = conn.cursor()

            # Get unread messages from other agents
            cursor.execute("""
                SELECT id, sender, message, timestamp, read_by
                FROM messages
                WHERE sender != ?
                AND (read_by NOT LIKE ? OR read_by = '')
                ORDER BY timestamp ASC
            """, (agent_id, f"%{agent_id}%"))

            unread_rows = cursor.fetchall()

            logger.info(f"📨 Found {len(unread_rows)} unread messages for {agent_id}")

            if unread_rows:
                # Mark messages as read by this agent
                for row in unread_rows:
                    msg_id, sender, message, timestamp, read_by = row
                    current_read_by = read_by or ""

                    # Add this agent to read_by list if not already there
                    if agent_id not in current_read_by:
                        updated_read_by = f"{current_read_by},{agent_id}".strip(',')
                        cursor.execute(
                            "UPDATE messages SET read_by = ? WHERE id = ?",
                            (updated_read_by, msg_id)
                        )
                        logger.debug(f"Marked message {msg_id} as read by {agent_id}")

                content = "\n".join([
                    f"[STATUS] {row[1]}: {row[2]}"  # sender: message
                    for row in unread_rows
                ])
                logger.info(f"📬 Returning {len(unread_rows)} messages to {agent_id}")
            else:
                content = ""
                logger.info(f"No new messages for {agent_id}")

            conn.commit()
            conn.close()

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
    # Initialize database before starting server
    init_database()
    asyncio.run(main())
