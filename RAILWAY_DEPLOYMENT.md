# Railway Deployment Guide for Binance Trading Bot

## Prerequisites

1. GitHub account with your code repository
2. Railway account (https://railway.app)
3. Binance API credentials

## Step-by-Step Deployment

### 1. Push Code to GitHub

```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2. Deploy to Railway

#### Option A: Using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

#### Option B: Using Railway Dashboard

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will automatically detect the Dockerfile

### 3. Set Environment Variables

In Railway dashboard, go to your project → Variables and add:

```
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
SIMULATION_MODE=true
DRY_RUN=true
MAX_TRADES=5
LEVERAGE=10
TYPE=ISOLATED
SL=0.02
TP=0.04
SPREAD_ADJUSTMENT=0.001
RISK_REWARD_RATIO=2.0
MAX_PORTFOLIO_RISK=0.1
SORTBY=volume
PAIRS_TO_PROCESS=10
DYNAMIC_POSITION_SIZING=true
PORT=8000
```

### 4. Monitor Deployment

- Railway will build the Docker image
- Check logs in Railway dashboard
- Visit the provided URL to access your API

### 5. API Endpoints

Once deployed, your bot will be available at:

- `https://your-app.railway.app/` - Main API
- `https://your-app.railway.app/docs` - Interactive API documentation
- `https://your-app.railway.app/health` - Health check

## Local Testing

### Test with Docker

```bash
# Build image
docker build -t binance-trading-bot .

# Run container
docker run -p 8000:8000 --env-file .env binance-trading-bot
```

### Test with Docker Compose

```bash
# Start services
docker-compose up --build

# Stop services
docker-compose down
```

## Important Notes

1. **Security**: Never commit API keys to Git
2. **Start in simulation mode**: Set SIMULATION_MODE=true for testing
3. **Monitor logs**: Check Railway logs for any issues
4. **Resource limits**: Railway has usage limits on free tier
5. **Persistent data**: Use Railway volumes for storing logs/data

## Troubleshooting

### Build Issues

- Check Dockerfile syntax
- Verify requirements.txt dependencies
- Check Railway build logs

### Runtime Issues

- Verify environment variables are set
- Check API credentials are valid
- Monitor application logs in Railway dashboard

### TA-Lib Issues

- The Dockerfile includes TA-Lib C library installation
- If issues persist, consider using the `ta` library instead

## Monitoring

- Use Railway metrics dashboard
- Set up alerts for downtime
- Monitor API response times
- Check trading performance logs

## Scaling

- Railway auto-scales based on traffic
- Monitor resource usage
- Upgrade plan if needed for higher limits
