#!/bin/bash
# Multi-Agent Collaboration Demo
# Runs 2 OpenHands agents in parallel with collaboration

echo "🤝 OpenHands Multi-Agent Collaboration Demo"
echo "🌿 BRANCH-BASED PARALLEL DEVELOPMENT:"
echo "   • Agent 1: Working on calculator implementation (Branch 1)"
echo "   • Agent 2: Working on test development (Branch 2)"
echo "📡 Agents will share detailed progress via MCP collaboration"
echo

# Set API key (export your OpenAI API key before running)
# export OPENAI_API_KEY="your-openai-api-key-here"
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: Please set your OPENAI_API_KEY environment variable first:"
    echo "   export OPENAI_API_KEY=\"your-api-key-here\""
    exit 1
fi

# Create workspaces and shared directory for SQLite database
mkdir -p workspace1 workspace2 shared

echo "🚀 Starting Agent 1 (Calculator Implementation) in workspace1/..."
WORKSPACE_DIR="/workspace" AGENT_ID="1" python -m openhands.core.main \
  --config config.agent1.toml \
  --task "BRANCH 1 DEVELOPMENT: Create calculator.py with arithmetic operations. Share detailed progress: 1) send('Agent 1: Starting calculator on branch 1 - creating Calculator class'), 2) send('Implemented add(a,b), subtract(a,b), multiply(a,b), divide(a,b) methods'), 3) send('Added division by zero error handling'), 4) send('Calculator class complete with all arithmetic functions - ready for testing')." &

AGENT1_PID=$!

# Wait a moment before starting second agent
sleep 3

echo "🚀 Starting Agent 2 (Test Creation) in workspace2/..."
WORKSPACE_DIR="/workspace" AGENT_ID="2" python -m openhands.core.main \
  --config config.agent2.toml \
  --task "BRANCH 2 TESTING: Create test_calculator.py based on Agent 1's implementation. Monitor their progress and create comprehensive tests: 1) send('Agent 2: Starting test development on branch 2'), 2) send('Creating tests for add/subtract functions'), 3) send('Testing division by zero error handling'), 4) send('Testing edge cases with negative numbers'), 5) send('All calculator tests completed - 100% coverage achieved')." &

AGENT2_PID=$!

echo "⏳ Both agents running in parallel..."
echo "Agent 1 PID: $AGENT1_PID"
echo "Agent 2 PID: $AGENT2_PID"
echo "📝 Check mcp_server.log for detailed collaboration logs!"
echo

# Wait for both agents to complete
wait $AGENT1_PID
wait $AGENT2_PID

echo "✅ Multi-agent collaboration demo completed!"
echo "📁 Check workspace1/ and workspace2/ for results"
echo "📋 Check logs/ for trajectory details"
