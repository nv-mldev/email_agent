#!/bin/bash

# Check status of Email Agent services

echo "📊 Email Agent Service Status"
echo "============================"

check_service() {
    local name=$1
    local port=$2
    local log_file=$3
    
    if nc -z localhost $port 2>/dev/null; then
        echo "✅ $name (Port $port): RUNNING"
    else
        echo "❌ $name (Port $port): NOT RUNNING"
    fi
    
    if [ -f "$log_file" ]; then
        echo "   📄 Log: $log_file (last 2 lines):"
        tail -n 2 "$log_file" | sed 's/^/      /'
    fi
    echo ""
}

check_service "API Server" 8000 "logs/api.log"
check_service "React UI" 3000 "logs/react.log"

echo "📋 Background Services (React Mode):"
if [ -f ".email_agent_react_pids" ]; then
    PIDS=$(cat .email_agent_react_pids)
    SERVICE_NAMES=("API Server" "Email Parser" "Email Summarizer" "React UI")
    i=0
    for pid in $PIDS; do
        if ps -p $pid > /dev/null 2>&1; then
            PROCESS_NAME=$(ps -p $pid -o comm= 2>/dev/null)
            echo "✅ PID $pid: ${SERVICE_NAMES[$i]} ($PROCESS_NAME) - RUNNING"
        else
            echo "❌ PID $pid: ${SERVICE_NAMES[$i]} - NOT RUNNING"
        fi
        i=$((i + 1))
    done
else
    echo "❌ No React PID file found. Services may not be running."
    echo "   Start services with: ./quick_start_react.sh"
fi

echo ""
echo "🧪 Staging Mode Features:"
echo "========================"
echo "📧 Manual email fetching via UI button"
echo "🚫 Automatic email polling: DISABLED"
echo "🔧 Perfect for testing and development"

echo ""
echo "📊 Recent log activity:"
echo "======================"
if [ -d "logs" ]; then
    ls -la logs/
    echo ""
    echo "📄 Parser Service Status:"
    if [ -f "logs/parser.log" ]; then
        echo "   Last parser activity:"
        tail -n 3 "logs/parser.log" | sed 's/^/      /'
    else
        echo "   ❌ No parser log found"
    fi
    echo ""
    echo "📄 Summarizer Service Status:"
    if [ -f "logs/summarizer.log" ]; then
        echo "   Last summarizer activity:"
        tail -n 3 "logs/summarizer.log" | sed 's/^/      /'
    else
        echo "   ❌ No summarizer log found"
    fi
fi
