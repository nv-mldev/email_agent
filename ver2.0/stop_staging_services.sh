#!/bin/bash

# Stop Email Agent staging services

if [ -f ".email_agent_staging_pids" ]; then
    echo "🛑 Stopping Email Agent staging services..."
    PIDS=$(cat .email_agent_staging_pids)
    for pid in $PIDS; do
        if kill -0 $pid 2>/dev/null; then
            echo "   Stopping PID: $pid"
            kill $pid
        fi
    done
    rm .email_agent_staging_pids
    echo "✅ All staging services stopped!"
else
    echo "❌ No staging PID file found. Services may not be running."
fi
