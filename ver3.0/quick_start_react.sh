#!/bin/bash

# Email Agent - Quick Start with React UI
# This script sets up and starts the complete Email Agent system with React frontend

set -e  # Exit on any error

echo "🚀 Email Agent - Quick Start with React UI"
echo "=========================================="
echo ""

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo "❌ $1 is not installed. Please install $1 first."
        exit 1
    fi
}

# Function to kill processes running on a specific port
kill_port_process() {
    local port=$1
    local service_name=$2
    
    # Find process using the port
    local pid=$(lsof -ti:$port 2>/dev/null)
    
    if [ ! -z "$pid" ]; then
        echo "🔄 Killing existing $service_name process on port $port (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
        sleep 2
        
        # Verify the process is killed
        if lsof -ti:$port 2>/dev/null; then
            echo "⚠️  Failed to kill process on port $port. Please manually stop it."
            return 1
        else
            echo "✅ Successfully killed process on port $port"
        fi
    fi
    return 0
}

# Function to check if service is running and optionally kill it
check_service() {
    local service=$1
    local port=$2
    if nc -z localhost $port 2>/dev/null; then
        echo "⚠️  Port $port is already in use by $service."
        kill_port_process $port "$service"
        return $?
    fi
    return 0
}

# Check prerequisites
echo "🔍 Checking prerequisites..."
check_command python3
check_command node
check_command npm
check_command psql
check_command rabbitmq-server

# Check if ports are available and kill existing processes if needed
echo "🔍 Checking available ports..."
check_service "API" 8000
check_service "React" 3000

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Please copy .env.example to .env and configure your credentials:"
    echo "   cp .env.example .env"
    echo "   Then edit .env with your Azure and database settings."
    exit 1
fi

echo "✅ Prerequisites check passed!"
echo ""

# Setup Python environment
echo "🐍 Setting up Python environment..."
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

echo "   Activating virtual environment..."
source venv/bin/activate

echo "   Installing Python dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

echo "✅ Python environment ready!"
echo ""

# Setup React environment
echo "⚛️  Setting up React environment..."
if [ ! -d "react-ui/node_modules" ]; then
    echo "   Installing React dependencies..."
    cd react-ui
    npm install > /dev/null 2>&1
    cd ..
fi

echo "✅ React environment ready!"
echo ""

# Setup database
echo "💾 Setting up database..."
echo "   Creating/updating database tables..."
python create_tables.py

# Run migration if needed
if [ -f "migrate_po_to_project_id.py" ]; then
    echo "   Running Project ID migration..."
    echo "y" | python migrate_po_to_project_id.py > /dev/null 2>&1 || true
fi

echo "✅ Database setup complete!"
echo ""

# Create logs directory
mkdir -p logs

# Load environment variables
export $(grep -v '^#' .env | xargs) 2>/dev/null || true

# Clean up any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "python.*email_parser_service" 2>/dev/null || true
pkill -f "python.*email_summarizer_service" 2>/dev/null || true
pkill -f "uvicorn.*api.main" 2>/dev/null || true
pkill -f "npm.*start" 2>/dev/null || true

# Also kill any processes still using our ports as backup
kill_port_process 8000 "API Server" || true
kill_port_process 3000 "React UI" || true

sleep 2

echo "✅ Cleanup complete!"
echo ""

# Start services
echo "🚀 Starting services..."

# Function to wait for service
wait_for_service() {
    local name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "   Waiting for $name on port $port..."
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost $port 2>/dev/null; then
            echo "   ✅ $name is ready!"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
    done
    echo "   ❌ $name failed to start"
    return 1
}

# Start API Server
echo "   Starting API Server..."
(source venv/bin/activate && uvicorn api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1) &
API_PID=$!

# Wait for API
if ! wait_for_service "API Server" 8000; then
    echo "❌ Failed to start API Server. Check logs/api.log"
    exit 1
fi

# Start Email Parser Service
echo "   Starting Email Parser Service..."
(source venv/bin/activate && python -m email_parser_service.main > logs/parser.log 2>&1) &
PARSER_PID=$!
sleep 3

# Start Email Summarizer Service
echo "   Starting Email Summarizer Service..."
(source venv/bin/activate && python -m email_summarizer_service.main > logs/summarizer.log 2>&1) &
SUMMARIZER_PID=$!
sleep 3

# Start React UI
echo "   Starting React UI..."
(cd react-ui && npm start > ../logs/react.log 2>&1) &
REACT_PID=$!

# Wait for React
if ! wait_for_service "React UI" 3000; then
    echo "❌ Failed to start React UI. Check logs/react.log"
    exit 1
fi

# Save PIDs
echo "$API_PID $PARSER_PID $SUMMARIZER_PID $REACT_PID" > .email_agent_react_pids

echo ""
echo "🎉 Email Agent is now running!"
echo "============================="
echo ""
echo "📱 Access Points:"
echo "   🌐 React UI:       http://localhost:3000"
echo "   📡 API Server:     http://localhost:8000"
echo "   📚 API Docs:       http://localhost:8000/docs"
echo ""
echo "🎯 What to do next:"
echo "   1. Open http://localhost:3000 in your browser"
echo "   2. Click 'Fetch Emails' to check for new messages"
echo "   3. Click on any email row to view details and AI summaries"
echo ""
echo "📊 Monitoring:"
echo "   • Check status:    ./check_services.sh"
echo "   • View logs:       tail -f logs/api.log"
echo "   • Stop services:   ./stop_react_services.sh"
echo ""
echo "🚀 Happy email processing!"

# Try to open browser (optional)
if command -v xdg-open &> /dev/null; then
    sleep 5
    xdg-open http://localhost:3000 2>/dev/null || true
elif command -v open &> /dev/null; then
    sleep 5
    open http://localhost:3000 2>/dev/null || true
fi