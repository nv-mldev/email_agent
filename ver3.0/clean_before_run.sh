#!/bin/bash

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Convert SQLAlchemy DATABASE_URL to psql-compatible URL
CLEAN_DATABASE_URL="${DATABASE_URL/postgresql+psycopg2:\/\//postgresql://}"

echo "==> Dropping and recreating tables..."
psql "$CLEAN_DATABASE_URL" -c "DROP TABLE IF EXISTS email_processing_log CASCADE;"

echo "==> Recreating tables using create_tables.py..."
source venv/bin/activate
python create_tables.py

echo "==> Purging RabbitMQ Queues..."
# Ensure management plugin host, port and vhost are specified for rabbitmqadmin
# Use HTTP management port for rabbitmqadmin (default 15672)
MGMT_PORT=${RABBITMQ_MGMT_PORT:-15672}
rabbitmqadmin -u $RABBITMQ_USER -p $RABBITMQ_PASS \
  --host=$RABBITMQ_HOST --port=$MGMT_PORT --vhost=/ purge queue name=$RABBITMQ_INPUT_QUEUE_NAME
rabbitmqadmin -u $RABBITMQ_USER -p $RABBITMQ_PASS \
  --host=$RABBITMQ_HOST --port=$MGMT_PORT --vhost=/ purge queue name=$RABBITMQ_OUTPUT_QUEUE_NAME

