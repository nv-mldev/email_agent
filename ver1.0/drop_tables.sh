#!/bin/bash

# Drop tables script for email_agent database
# This script removes all tables from the email_agent database

echo "=== Drop Tables Script ==="
echo "This will remove all tables from the email_agent database"

# Database connection parameters from .env
DB_HOST="localhost"
DB_PORT="5432"
DB_USER="cargoa_user"
DB_NAME="email_agent"

# Function to execute SQL command
execute_sql() {
    local sql_command="$1"
    echo "Executing: $sql_command"
    PGPASSWORD="cargoa" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$sql_command"
}

# Function to check if table exists
table_exists() {
    local table_name="$1"
    local count=$(PGPASSWORD="cargoa" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '$table_name';")
    echo $count
}

echo ""
echo "Checking current tables..."
PGPASSWORD="cargoa" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

echo ""
echo "Dropping email_processing_log table..."

# Check if email_processing_log table exists
if [ "$(table_exists 'email_processing_log')" -gt 0 ]; then
    echo "Table 'email_processing_log' exists. Dropping it..."
    execute_sql "DROP TABLE IF EXISTS email_processing_log CASCADE;"
    echo "✓ Table 'email_processing_log' dropped successfully"
else
    echo "Table 'email_processing_log' does not exist"
fi

echo ""
echo "Checking tables after drop..."
PGPASSWORD="cargoa" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

echo ""
echo "=== Drop Tables Script Completed ==="
