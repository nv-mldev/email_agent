#!/bin/bash

# Email Agent - Staging Mode (Manual Email Fetching)
# This script starts services without the automatic email polling

echo "🧪 Starting Email Agent System (STAGING MODE)..."
echo "   📧 Email fetching: MANUAL (via UI button)"
echo "   🔄 Auto-polling: DISABLED"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
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
pkill -f "python.*document_analysis_service" 2>/dev/null || true
pkill -f "uvicorn.*api.main" 2>/dev/null || true
pkill -f "streamlit.*streamlit_app" 2>/dev/null || true
sleep 2

python create_tables.py

echo "🔄 Starting staging services..."

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

# Start Document Analysis Service
echo "▶️  Starting Document Analysis Service..."
(source venv/bin/activate && python -m document_analysis_service.async_main > logs/analysis.log 2>&1) &
ANALYSIS_PID=$!
echo "   PID: $ANALYSIS_PID (logs: logs/analysis.log)"

# Wait a bit for analysis service to initialize
sleep 3

# Start Streamlit UI
echo "▶️  Starting Streamlit UI..."
(source venv/bin/activate && streamlit run streamlit_app.py --server.port 8501 > logs/streamlit.log 2>&1) &
STREAMLIT_PID=$!
echo "   PID: $STREAMLIT_PID (logs: logs/streamlit.log)"

# Wait for Streamlit to be ready
if ! wait_for_service "Streamlit UI" 8501; then
    echo "❌ Failed to start Streamlit UI. Check logs/streamlit.log"
    exit 1
fi

# Save PIDs for cleanup (without polling service)
echo "$API_PID $PARSER_PID $ANALYSIS_PID $STREAMLIT_PID" > .email_agent_staging_pids

echo ""
echo "✅ Staging services started!"
echo ""
echo "🧪 STAGING MODE FEATURES:"
echo "   📧 Manual email fetching via UI button"
echo "   🔧 Perfect for testing and development"
echo "   🚫 No automatic email polling"
echo ""
echo "=== ACCESS POINTS ==="
echo "📡 API Server: http://localhost:8000"
echo "📡 API Docs: http://localhost:8000/docs"
echo "🖥️  Streamlit UI: http://localhost:8501"
echo ""
echo "=== USAGE ==="
echo "1. Open the Streamlit UI: http://localhost:8501"
echo "2. Click 'Fetch Emails' button to check for new messages"
echo "3. Process and review emails manually"
echo ""
echo "=== MONITORING ==="
echo "📊 Service logs are in the 'logs/' directory"
echo "📊 Watch logs: tail -f logs/api.log"
echo ""
echo "=== SHUTDOWN ==="
echo "To stop services: ./stop_staging_services.sh"
echo "Or manually: kill $API_PID $PARSER_PID $ANALYSIS_PID $STREAMLIT_PID"
