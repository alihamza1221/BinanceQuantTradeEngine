from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Union
from BinanceQuantTradingEngine import BinanceQuantTradingEngine
from fastapi.middleware.cors import CORSMiddleware
import threading
import os
import logging

app = FastAPI(title="Binance Trading Bot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Or use ["http://localhost:PORT"] for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint for Railway
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "binance-trading-bot"}

@app.get("/")
async def root():
    return {"message": "Binance Quant Trading Bot API", "status": "running"}

# Load configuration from environment variables with fallbacks
CONFIG = {
    "SIMULATION_MODE": os.getenv("SIMULATION_MODE", "true").lower() == "true",
    "DRY_RUN": os.getenv("DRY_RUN", "true").lower() == "true",
    "RISK_REWARD_RATIO": float(os.getenv("RISK_REWARD_RATIO", "2.0")),
    "MAX_PORTFOLIO_RISK": float(os.getenv("MAX_PORTFOLIO_RISK", "0.1")),
    "TRADE_FEE_RATE": float(os.getenv("TRADE_FEE_RATE", "0.0018")),
    "PRICE_UPDATE_THRESHOLD": float(os.getenv("PRICE_UPDATE_THRESHOLD", "0.015")),
    "SPREAD_ADJUSTMENT": float(os.getenv("SPREAD_ADJUSTMENT", "0.001")),
    "DYNAMIC_POSITION_SIZING": os.getenv("DYNAMIC_POSITION_SIZING", "true").lower() == "true",
    "LEVERAGE": int(os.getenv("LEVERAGE", "10")),
    "TYPE": os.getenv("TYPE", "ISOLATED"),
    "TP": float(os.getenv("TP", "0.04")),
    "SL": float(os.getenv("SL", "0.02")),
    "SORTBY": os.getenv("SORTBY", "volume"),
    "PAIRS_TO_PROCESS": int(os.getenv("PAIRS_TO_PROCESS", "10")),
    "MAX_TRADES": int(os.getenv("MAX_TRADES", "5")),
    "TOTAL_TRADES_OPEN": int(os.getenv("TOTAL_TRADES_OPEN", "0"))
}

# Global trading engine instance
engine = None
engine_thread = None

# Initialize engine with CONFIG
def get_engine():
    global engine
    if engine is None:
        engine = BinanceQuantTradingEngine(CONFIG)
    return engine

READONLY_KEYS = {"TOTAL_TRADES_OPEN"}

class ConfigUpdate(BaseModel):
    key: str
    value: Union[float, int, bool, str]

@app.get("/config")
def get_config():
    return CONFIG

@app.post("/config")
def update_config(update: ConfigUpdate):
    key = update.key
    value = update.value
    if key not in CONFIG:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found.")
    if key in READONLY_KEYS:
        raise HTTPException(status_code=400, detail=f"Config key '{key}' is read-only.")
    CONFIG[key] = value
    # Update engine config if it exists
    engine = get_engine()
    if hasattr(engine, 'config') and key in engine.config:
        engine.config[key] = value
    return {"message": f"{key} updated to {value}"}

@app.post("/refresh")
def run_refresh():
    engine = get_engine()
    result = engine.refresh_data()
    return {"refresh": result}

@app.post("/run_strategy")
def run_strategy():
    engine = get_engine()
    engine.execute_strategy()
    return {"status": "Strategy executed"}

@app.get("/balance")
def get_balance():
    engine = get_engine()
    return {"balance": engine.get_balance()}

@app.get("/positions")
def get_positions():
    engine = get_engine()
    return {"positions": engine.get_pos()}

@app.get("/orders")
def get_orders():
    engine = get_engine()
    return {"orders": engine.check_orders()}

@app.get("/status")
def get_status():
    engine = get_engine()
    return {
        "running": engine.running,
        "run_count": engine.run_count,
        "total_trades_open": CONFIG["TOTAL_TRADES_OPEN"],
    }

@app.post("/start")
def start_bot():
    engine = get_engine()
    engine.start()
    return {"message": "Bot started successfully"}

@app.post("/stop")
def stop_bot():
    engine = get_engine()
    engine.stop()
    return {"message": "Bot stopped"}

#to run:
#uvicorn AdminApi:app --reload --port 8000

