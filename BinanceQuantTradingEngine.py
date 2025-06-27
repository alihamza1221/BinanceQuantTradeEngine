import os
from dotenv import load_dotenv

load_dotenv()

class BinanceQuantTradingEngine:
    def __init__(self):
        # Access environment variables
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Missing required API credentials in environment variables")
