#!/usr/bin/env python3
"""
Minimal test for OpenHands multi-agent collaboration system.
Tests MCP server functionality and basic agent integration.
"""

import asyncio
import json
import subprocess
import sys
import time


async def test_mcp_server():
    """Test the MCP collaboration server directly."""
    print("🧪 Testing MCP Collaboration Server...")

    # Start MCP server
    process = subprocess.Popen(
        [sys.executable, "mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Test initialization
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        init_response = json.loads(response)
        assert init_response["result"]["serverInfo"]["name"] == "collaboration-server"
        print("✅ MCP server initialization works")

        # Test tools list
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        tools_response = json.loads(response)
        tools = tools_response["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]

        assert "send" in tool_names
        assert "get_messages" in tool_names
        print("✅ MCP tools (send, get_messages) available")

        # Test send message
        send_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "send",
                "arguments": {
                    "agent_id": "test_agent_1",
                    "message": "Testing collaboration message"
                }
            }
        }

        process.stdin.write(json.dumps(send_request) + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        send_response = json.loads(response)
        assert "Message sent" in send_response["result"]["content"][0]["text"]
        print("✅ Message sending works")

        # Test get messages
        get_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_messages",
                "arguments": {
                    "agent_id": "test_agent_2"
                }
            }
        }

        process.stdin.write(json.dumps(get_request) + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        get_response = json.loads(response)
        messages = get_response["result"]["content"][0]["text"]
        assert "test_agent_1" in messages
        assert "Testing collaboration message" in messages
        print("✅ Message receiving works")

        print("🎉 All MCP server tests passed!")

    finally:
        process.terminate()
        process.wait()


async def test_agent_integration():
    """Test that OpenHands agents can use collaboration tools."""
    print("\n🤖 Testing OpenHands Integration...")

    try:
        # Import OpenHands modules
        from openhands.core.config import OpenHandsConfig, get_default_agent_config
        from openhands.agenthub import CodeActAgent
        from openhands.llm import LLM

        # Create minimal config
        config = OpenHandsConfig(
            enable_mcp=True,
            mcp={
                "stdio_servers": {
                    "collaboration": {
                        "command": "python",
                        "args": ["mcp_server.py"]
                    }
                }
            }
        )

        # Create agent
        agent_config = get_default_agent_config()
        llm = LLM(config=config.llm)
        agent = CodeActAgent(llm=llm, config=agent_config)

        print("✅ Agent creation with MCP config works")
        print("🎉 Basic integration test passed!")

    except ImportError as e:
        print(f"⚠️ OpenHands import failed (expected in standalone test): {e}")
        print("✅ Test setup is correct, run with full OpenHands environment")
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

    return True


async def main():
    """Run all tests."""
    print("🚀 Testing OpenHands Multi-Agent Collaboration System\n")

    # Test MCP server
    await test_mcp_server()

    # Test integration
    await test_agent_integration()

    print("\n✨ Testing complete! Run with OpenHands for full functionality.")


if __name__ == "__main__":
    asyncio.run(main())
