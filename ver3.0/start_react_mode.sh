#!/bin/bash

# Email Agent - React UI Startup Script
echo "🚀 Starting Email Agent with React UI..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check if React dependencies are installed
if [ ! -d "react-ui/node_modules" ]; then
    echo "📦 Installing React dependencies..."
    cd react-ui
    npm install
    cd ..
    echo "✅ React dependencies installed!"
fi

# Create logs directory
mkdir -p logs

# Load environment variables
export $(grep -v '^#' .env | xargs)

echo "📊 Checking dependencies and database..."
source venv/bin/activate

# Clean up any existing processes to avoid conflicts
echo "🧹 Cleaning up any existing services..."
pkill -f "python.*email_parser_service" 2>/dev/null || true
pkill -f "python.*email_summarizer_service" 2>/dev/null || true
pkill -f "uvicorn.*api.main" 2>/dev/null || true
pkill -f "npm.*start" 2>/dev/null || true
sleep 2

python create_tables.py

echo "🔄 Starting services..."

# Function to wait for a service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name on port $port..."
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        echo "   Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "❌ $service_name failed to start within 60 seconds"
    return 1
}

# Start API Server
echo "▶️  Starting API Server..."
(source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload > logs/api.log 2>&1) &
API_PID=$!
echo "   PID: $API_PID (logs: logs/api.log)"

# Wait for API to be ready before starting other services
if ! wait_for_service "API Server" 8000; then
    echo "❌ Failed to start API Server. Check logs/api.log"
    exit 1
fi

# Start Email Parser Service
echo "▶️  Starting Email Parser Service..."
(source venv/bin/activate && python -m email_parser_service.main > logs/parser.log 2>&1) &
PARSER_PID=$!
echo "   PID: $PARSER_PID (logs: logs/parser.log)"

# Wait a bit for parser to initialize
sleep 3

# Start Email Summarizer Service
echo "▶️  Starting Email Summarizer Service..."
(source venv/bin/activate && python -m email_summarizer_service.main > logs/summarizer.log 2>&1) &
SUMMARIZER_PID=$!
echo "   PID: $SUMMARIZER_PID (logs: logs/summarizer.log)"

# Wait a bit for summarizer service to initialize
sleep 3

# Start React UI
echo "▶️  Starting React UI..."
(cd react-ui && npm start > ../logs/react.log 2>&1) &
REACT_PID=$!
echo "   PID: $REACT_PID (logs: logs/react.log)"

# Wait for React to be ready
if ! wait_for_service "React UI" 3000; then
    echo "❌ Failed to start React UI. Check logs/react.log"
    exit 1
fi

# Save PIDs for cleanup
echo "$API_PID $PARSER_PID $SUMMARIZER_PID $REACT_PID" > .email_agent_react_pids

echo ""
echo "✅ All services started!"
echo ""
echo "🎯 REACT UI MODE FEATURES:"
echo "   📧 Manual email fetching via UI button"
echo "   🎨 Modern React interface with Material-UI"
echo "   📊 Data grid for email management"
echo "   🔧 Perfect for production and testing"
echo ""
echo "=== ACCESS POINTS ==="
echo "📡 API Server: http://localhost:8000"
echo "📡 API Docs: http://localhost:8000/docs"
echo "🌐 React UI: http://localhost:3000"
echo ""
echo "=== USAGE ==="
echo "1. Open the React UI: http://localhost:3000"
echo "2. Click 'Fetch Emails' button to check for new messages"
echo "3. Click on any email row to view details"
echo "4. View AI-generated summaries and PO numbers"
echo ""
echo "=== MONITORING ==="
echo "📊 Service logs are in the 'logs/' directory"
echo "📊 Watch logs: tail -f logs/api.log"
echo ""
echo "=== SHUTDOWN ==="
echo "To stop services: ./stop_react_services.sh"
echo "Or manually: kill $API_PID $PARSER_PID $SUMMARIZER_PID $REACT_PID"