#!/bin/bash

# Stop Email Agent React services

if [ -f ".email_agent_react_pids" ]; then
    echo "🛑 Stopping Email Agent React services..."
    PIDS=$(cat .email_agent_react_pids)
    for pid in $PIDS; do
        if kill -0 $pid 2>/dev/null; then
            echo "   Stopping PID: $pid"
            kill $pid
        fi
    done
    rm .email_agent_react_pids
    echo "✅ All React services stopped!"
else
    echo "❌ No React PID file found. Services may not be running."
fi

# Also kill any remaining React processes
pkill -f "npm.*start" 2>/dev/null || true
echo "🧹 Cleaned up any remaining React processes"