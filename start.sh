#!/bin/bash

# Grok 3.0 Chat Application Startup Script
echo "🚀 Starting Grok 3.0 Chat Application..."

# Check if .env file exists and load it first
if [ -f .env ]; then
    echo "📄 Loading .env file..."
    set -a  # automatically export all variables
    source .env
    set +a  # stop automatically exporting
fi

# Set default environment variables if not already set
export MODEL_NAME=${MODEL_NAME:-"grok-3-fast-latest"}
export API_URL=${API_URL:-"https://api.x.ai/v1/chat/completions"}
export TEMPERATURE=${TEMPERATURE:-"0"}
export PORT=${PORT:-"10000"}
export HOST=${HOST:-"0.0.0.0"}
export DEBUG=${DEBUG:-"false"}
export PYTHONUNBUFFERED=${PYTHONUNBUFFERED:-"1"}
export PYTHONDONTWRITEBYTECODE=${PYTHONDONTWRITEBYTECODE:-"1"}

# Display configuration
echo "📋 Configuration:"
echo "   Model: $MODEL_NAME"
echo "   API URL: $API_URL"
echo "   Port: $PORT"
echo "   Host: $HOST"
echo "   Debug: $DEBUG"

# Start the application
echo "🎯 Starting application..."
python chat.py 