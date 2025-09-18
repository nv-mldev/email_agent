#!/bin/bash

# Email Agent - Health Check Script
# Verifies all components are working correctly

echo "🏥 Email Agent - Health Check"
echo "============================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check status
check_status() {
    local name=$1
    local test_command=$2
    local status_message=$3
    
    printf "%-30s" "$name:"
    if eval "$test_command" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $status_message${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed${NC}"
        return 1
    fi
}

# Function to check HTTP endpoint
check_http() {
    local name=$1
    local url=$2
    
    printf "%-30s" "$name:"
    if curl -s "$url" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Responding${NC}"
        return 0
    else
        echo -e "${RED}❌ Not responding${NC}"
        return 1
    fi
}

# Check prerequisites
echo "🔍 Prerequisites Check:"
check_status "Python 3" "python3 --version" "Installed"
check_status "PostgreSQL" "psql --version" "Installed"
check_status "RabbitMQ" "rabbitmq-server --version" "Installed"
check_status "Node.js" "node --version" "Installed"
echo ""

# Check services
echo "🔧 Service Status:"
check_status "PostgreSQL Service" "pg_isready" "Running"
check_status "RabbitMQ Service" "rabbitmqctl status" "Running"
echo ""

# Check application components
echo "🚀 Application Status:"
check_http "API Server" "http://localhost:8000/docs"
check_http "React UI" "http://localhost:3000"
echo ""

# Check configuration
echo "⚙️  Configuration Check:"
check_status ".env file" "test -f .env" "Present"
check_status "Virtual environment" "test -d venv" "Present"
check_status "React dependencies" "test -d react-ui/node_modules" "Installed"
echo ""

# Check database connectivity
echo "💾 Database Check:"
if [ -f ".env" ]; then
    source .env 2>/dev/null || true
    if [ ! -z "$DATABASE_URL" ]; then
        # Extract connection details for psql
        CLEAN_URL="${DATABASE_URL/postgresql+psycopg2:\/\//postgresql://}"
        check_status "Database connection" "psql '$CLEAN_URL' -c 'SELECT 1'" "Connected"
        check_status "Email table exists" "psql '$CLEAN_URL' -c '\dt email_processing_log'" "Table exists"
    else
        echo -e "Database URL                  ${YELLOW}⚠️  Not configured${NC}"
    fi
else
    echo -e "Configuration                 ${RED}❌ .env file missing${NC}"
fi
echo ""

# Check logs
echo "📊 Log Status:"
if [ -d "logs" ]; then
    for log in api parser summarizer react; do
        if [ -f "logs/$log.log" ]; then
            size=$(stat -f%z "logs/$log.log" 2>/dev/null || stat -c%s "logs/$log.log" 2>/dev/null || echo "0")
            if [ "$size" -gt 0 ]; then
                echo -e "${log^} service logs             ${GREEN}✅ Active (${size} bytes)${NC}"
            else
                echo -e "${log^} service logs             ${YELLOW}⚠️  Empty${NC}"
            fi
        else
            echo -e "${log^} service logs             ${RED}❌ Missing${NC}"
        fi
    done
else
    echo -e "Logs directory                ${RED}❌ Missing${NC}"
fi
echo ""

# Check processes
echo "🔄 Process Status:"
if [ -f ".email_agent_react_pids" ]; then
    echo "React mode PIDs found:"
    PIDS=$(cat .email_agent_react_pids)
    SERVICES=("API" "Parser" "Summarizer" "React")
    i=0
    for pid in $PIDS; do
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${SERVICES[$i]} Service (PID: $pid)        ${GREEN}✅ Running${NC}"
        else
            echo -e "${SERVICES[$i]} Service (PID: $pid)        ${RED}❌ Not running${NC}"
        fi
        i=$((i + 1))
    done
else
    echo -e "Service PIDs                  ${YELLOW}⚠️  No PID file found${NC}"
fi
echo ""

# Summary
echo "📋 Health Check Summary:"
echo "======================"
echo "If you see ❌ errors above:"
echo "• Check the specific service documentation"
echo "• Review logs in the logs/ directory"
echo "• Ensure all prerequisites are installed"
echo "• Verify .env configuration"
echo ""
echo "To start services:"
echo "• React UI:    ./quick_start_react.sh"