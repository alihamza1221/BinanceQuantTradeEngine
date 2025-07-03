from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Union
from BinanceQuantTradingEngine import BinanceQuantTradingEngine
from fastapi.middleware.cors import CORSMiddleware
import threading

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 Or use ["http://localhost:PORT"] for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CONFIG = {
    "SIMULATION_MODE": False, # True / False
    "DRY_RUN": False, # True / False
    "RISK_REWARD_RATIO": 2.0, #1.0 to 4.0
    "MAX_PORTFOLIO_RISK": 1.0, # 0.1 to 1.0
    "TRADE_FEE_RATE": 0.0018, # float
    "PRICE_UPDATE_THRESHOLD": 0.015, #float
    "SPREAD_ADJUSTMENT": 0.0075, #float
    "DYNAMIC_POSITION_SIZING": True, # True / False
    "LEVERAGE": 40, # 1 to 100
    "TYPE": "CROSSED", # "CROSSED" or "ISOLATED" (Isolated is not supported yet)
    "TP": 0.50, # 0.08 means 8% take profit
    "SL": 0.20, # 0.08 means -8% stop loss
    "PAIRS_TO_PROCESS": 10, # 0 to 150
    "SORTBY": "volume", # "volume" or "price"
    "TOTAL_TRADES_OPEN": 0, 
    "MAX_TRADES": 8,  # Maximum number of trades to open at once
}

engine = BinanceQuantTradingEngine(CONFIG)
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
    if hasattr(engine, key):
        setattr(engine, key, value)
    return {"message": f"{key} updated to {value}"}

@app.post("/refresh")
def run_refresh():
    result = engine.refresh_data()
    return {"refresh": result}

@app.post("/run_strategy")
def run_strategy():
    engine.execute_strategy()
    return {"status": "Strategy executed"}

@app.get("/positions")
def get_positions():
    return {"positions": engine.get_pos()}

@app.get("/orders")
def get_orders():
    return {"orders": engine.check_orders()}

@app.get("/status")
def get_status():
    return {
        "running": engine.running,
        "run_count": engine.run_count,
        "total_trades_open": CONFIG["TOTAL_TRADES_OPEN"],
    }

@app.post("/start")
def start_bot():
    engine.run()
    return {"message": "success"}

@app.post("/stop")
def stop_bot():
    engine.stop()
    return {"message": "Bot stopped"}

#to run:
#uvicorn AdminApi:app --reload --port 8000

