#!/bin/bash

# Railway Deployment Script for Binance Trading Bot

echo "🚀 Deploying Binance Trading Bot to Railway..."

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Initializing..."
    git init
    git add .
    git commit -m "Initial commit for Railway deployment"
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "📝 Uncommitted changes found. Committing..."
    git add .
    git commit -m "Update for Railway deployment $(date)"
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin main

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm install -g @railway/cli
fi

# Login to Railway (if not already logged in)
echo "🔐 Checking Railway authentication..."
railway whoami || railway login

# Deploy to Railway
echo "🚢 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo "📊 Monitor your deployment at: https://railway.app/dashboard"
echo "🔗 Your API will be available at the URL shown in Railway dashboard"
echo ""
echo "📋 Don't forget to set these environment variables in Railway:"
echo "   - BINANCE_API_KEY"
echo "   - BINANCE_SECRET_KEY" 
echo "   - SIMULATION_MODE=true (for testing)"
echo "   - And other configuration variables from .env.railway"
