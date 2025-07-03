#!/bin/bash

# Startup script for Railway deployment

echo "🚀 Starting Binance Trading Bot..."

# Check if required environment variables are set
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_SECRET_KEY" ]; then
    echo "❌ Missing required environment variables: BINANCE_API_KEY and BINANCE_SECRET_KEY"
    echo "ℹ️  Please set these in your Railway dashboard"
    exit 1
fi

echo "✅ Environment variables validated"

# Start the FastAPI server
echo "🌐 Starting FastAPI server on port ${PORT:-8000}..."
python -m uvicorn AdminApi:app --host 0.0.0.0 --port ${PORT:-8000}
