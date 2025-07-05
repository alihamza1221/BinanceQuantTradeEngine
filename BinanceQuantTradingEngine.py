import os
from dotenv import load_dotenv
from binance.um_futures import UMFutures
from binance.error import ClientError
import time
from sklearn.linear_model import LinearRegression
import talib
import pandas as pd
import numpy as np
import logging


load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('LogsBinanceQuantTradingEngine.log'),
        logging.StreamHandler()
    ]
)


class BinanceQuantTradingEngine:
    def __init__(self, config=None):        
        # Merge provided config with defaults
        self.config = {**(config or {})}

        self.api_key = os.getenv('BINANCE_API_KEY')
        self.secret_key = os.getenv('BINANCE_SECRET_KEY')  # Fixed: was 'BINANCE_SECRET'
        self.client = UMFutures(key=self.api_key, secret=self.secret_key)

        if not self.api_key or not self.secret_key:
            logging.error("Missing required API credentials in environment variables")
            logging.error("Please set BINANCE_API_KEY and BINANCE_SECRET_KEY in your .env file")

        self.market_state = {}
        self.portfolio = {}
        self.risk_model = LinearRegression()
        self.market_metrics = pd.DataFrame()
        self.run_count = 0          
        self.running = False

    def get_balance(self):
        try:
            response = self.client.balance(recvWindow=6000)
            return response or []
        except ClientError as error:
            logging.error(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )

    def refresh_data(self):
        try:
            all_24hr_tickers = self.client.ticker_24hr_price_change()
            all_book_tickers = self.client.book_ticker()

            ticker_24hr_map = {item['symbol']: item for item in all_24hr_tickers}
            book_ticker_map = {item['symbol']: item for item in all_book_tickers}

            self.market_state = {}

            for symbol, book_data in book_ticker_map.items():
                ticker_data = ticker_24hr_map.get(symbol)
                if not ticker_data:
                    continue

                ask = float(book_data.get('askPrice', 0))
                bid = float(book_data.get('bidPrice', 0))
                ask_qty = float(book_data.get('askQty', 0))
                bid_qty = float(book_data.get('bidQty', 0))

                spread = ask - bid if ask > 0 and bid > 0 else 0
                liquidity = (bid * ask_qty) + (ask * bid_qty)

                price = float(ticker_data.get('lastPrice', 0))
                volume = float(ticker_data.get('volume', 0))

                self.market_state[symbol] = {
                    'price': price,
                    'volume': volume,
                    'spread': spread,
                    'liquidity': liquidity
                }

            SORTBY = str(self.config.get("SORTBY"))
            PAIRS_TO_PROCESS = int(self.config.get("PAIRS_TO_PROCESS"))

            top_symbols = sorted(
                self.market_state.items(),
                key=lambda x: x[1][SORTBY],
                reverse=True
            )[:PAIRS_TO_PROCESS]

            usdt_tickers = {}
            for symbol, data in top_symbols:
                if 'USDT' in symbol:
                    usdt_tickers[symbol] = data

            self.market_state = usdt_tickers

            self.portfolio = {
                item['asset']: {
                    'free': float(item['availableBalance']),
                    'locked': float(item['balance']) - float(item['availableBalance']),
                } for item in self.get_balance()
            }

            self._calculate_market_metrics()
            logging.info("Data refresh complete")
            return True

        except Exception as e:
            logging.error(f"Data refresh failed: {str(e)}")
            return False

    def _calculate_market_metrics(self):
        metrics = []
        logging.info("Calculating market metrics...")
        for symbol, data in self.market_state.items():
            order_book = self.client.depth(symbol)

            best_bid = float(order_book['bids'][0][0]) if order_book['bids'] else data['price']
            best_ask = float(order_book['asks'][0][0]) if order_book['asks'] else data['price']

            metrics.append({
                'pair': symbol,
                'mid_price': (data['price'] + best_bid) / 2,
                'order_book_imbalance': self._calculate_imbalance(order_book),
                'volatility': self._calculate_volatility(symbol),
                'volume_profile': data['volume']
            })

        self.market_metrics = pd.DataFrame(metrics)

    def _calculate_imbalance(self, order_book):
        try:
            bid_volume = sum(float(qty) for _, qty in order_book['bids'][:5])
            ask_volume = sum(float(qty) for _, qty in order_book['asks'][:5])
            return (bid_volume - ask_volume) / (bid_volume + ask_volume) if (bid_volume + ask_volume) != 0 else 0.0
        except (IndexError, ZeroDivisionError):
            return 0.0

    def _calculate_volatility(self, symbol):
        ohlc = self.get_historical_data(symbol, "15m")
        if not ohlc:
            return 0.0

        closes = [item[4] for item in ohlc if item[4] > 0]
        if len(closes) < 2:
            return 0.0

        try:
            returns = np.diff(np.log(closes))
            return np.nanstd(returns) * np.sqrt(365 * 24)
        except Exception as e:
            logging.error(f"Volatility calculation error: {str(e)}")
            return 0.0

    def get_historical_data(self, symbol,interval="15m"):
        try:
            raw_klines = self.client.klines(symbol=symbol, interval=interval)
            return [(int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5])) for k in raw_klines]
        except Exception as e:
            logging.error(f"Historical data error: {str(e)}")
            return []

    def execute_strategy(self):
        logging.info("Executing strategy cycle...")
        for pair in self.market_state:
            current_price = self.market_state[pair]['price']

            if not self._risk_approval(pair):
                continue

            trend_strength = self._analyze_trend(pair)
            volatility = self.market_metrics[self.market_metrics['pair'] == pair]['volatility'].values[0]
            liquidity = self.market_state[pair]['liquidity']

            position_size = self._calculate_position_size(pair, volatility, liquidity, trend_strength)

            if trend_strength > 0.6:
                self._execute_trade(pair, 'BUY', current_price, position_size)
            elif trend_strength < -0.6:
                self._execute_trade(pair, 'SELL', current_price, position_size)
            else:
                logging.info(f"No clear signal for {pair}")

    def _analyze_trend(self, pair):
        data = self.get_historical_data(pair, "15m")
        if not data or len(data) < 50:
            return 0.0

        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        if df['close'].min() <= 0:
            return 0.0

        df['returns'] = np.log(df['close']).diff().fillna(0)
        df['SMA20'] = talib.SMA(df['close'], 20)
        df['SMA50'] = talib.SMA(df['close'], 50)
        df['RSI'] = talib.RSI(df['close'], 14)
        df['MACD'], df['MACD_Signal'], _ = talib.MACD(df['close'])
        df['ADX'] = talib.ADX(df['high'], df['low'], df['close'], 14)
        df.dropna(inplace=True)
        if len(df) < 20:
            return 0.0

        score = pd.Series(0, index=df.index)
        score += np.where(df['SMA20'] > df['SMA50'], 1, -1)
        score += np.where(df['close'] > df['SMA20'], 1, -1)
        score += np.where(df['MACD'] > df['MACD_Signal'], 1, -1)
        score += np.where(df['RSI'] > 55, 1, 0)
        score += np.where(df['RSI'] < 45, -1, 0)

        adx_trend_direction = np.sign(df['SMA20'] - df['SMA50'])
        score += np.where(df['ADX'] > 25, adx_trend_direction, 0)

        normalized_trend = np.clip(score / 5.0, -1, 1)
        return normalized_trend.iloc[-1]

    def _calculate_position_size(self, pair, volatility, liquidity, trend_strength):
        if not bool(self.config.get("DYNAMIC_POSITION_SIZING")):
            return 0.1

        balance = self.portfolio.get('USDT', {}).get('free', 0)
        print(f"Balance for {pair}: {balance}")
        if balance <= 0:
            logging.warning("Insufficient balance for position sizing")
            return 0.0

        win_prob = max(0.55, abs(trend_strength))
        kelly_fraction = (win_prob * (self.config['RISK_REWARD_RATIO'] + 1) - 1) / self.config['RISK_REWARD_RATIO']
        risk_capital = balance * self.config['MAX_PORTFOLIO_RISK'] * kelly_fraction

        liquidity_factor = min(liquidity / (risk_capital * 2), 1) if risk_capital != 0 else 0
        volatility_factor = 1 / (1 + volatility) if volatility != 0 else 1

        return risk_capital * liquidity_factor * volatility_factor / self.market_state[pair]['price']

    def _risk_approval(self, pair):
        try:
            if self.market_metrics[self.market_metrics['pair'] == pair]['volatility'].values[0] > 1.3:
                logging.warning(f"High volatility blocking: {pair} volatility: {self.market_metrics[self.market_metrics['pair'] == pair]['volatility'].values[0]}")
                return False

            if self.market_state[pair]['spread'] / self.market_state[pair]['price'] > 0.1:
                logging.warning(f"Wide spread blocking: {pair}")
                return False

            return True
        except Exception as e:
            logging.error(f"Risk check error: {str(e)}")
            return False

    def _execute_trade(self, pair, side, price, quantity):
        try:
            if quantity < 1:
                logging.warning(f"Insufficient quantity for {pair}")
                return

            SPREAD_ADJUSTMENT = float(self.config.get("SPREAD_ADJUSTMENT"))
            LEVERAGE = int(self.config.get("LEVERAGE"))
            TYPE = str(self.config.get("TYPE"))
            SL = float(self.config.get("SL"))
            TP = float(self.config.get("TP"))



            qty_precision = self.get_qty_precision(pair)
            price_precision = self.get_price_precision(pair)

            order_book = self.client.depth(pair)
            best_bid = float(order_book['bids'][0][0]) if order_book['bids'] else price
            best_ask = float(order_book['asks'][0][0]) if order_book['asks'] else price

            if side.lower() == 'buy':
                price = best_bid * (1 - SPREAD_ADJUSTMENT)
            else:
                price = best_ask * (1 + SPREAD_ADJUSTMENT)

            qty = round(quantity, qty_precision)
            p_price = round(price, price_precision)
            print(f"""\n\nleverage: {LEVERAGE}, type: {TYPE}, sl: {SL}, tp: {TP} SPREAD_ADJUSTMENT: {SPREAD_ADJUSTMENT} pair: {pair}, price: {p_price}, qty: {qty} \n\n""")
            if qty * p_price < 5:
                logging.warning(f"Order size too small for {pair}")
                return

            if self.config["TOTAL_TRADES_OPEN"] >= self.config["MAX_TRADES"]:
                logging.warning("Max trades open limit reached")
                return

            self.set_leverage(pair, LEVERAGE)
            self.set_mode(pair, TYPE)

            resp1 = self.client.new_order(symbol=pair, side=side, type='LIMIT', quantity=qty,   timeInForce='GTC', price=p_price)
            logging.info(f"Order placed: {side} {qty} {pair} @ {p_price}")
            #sleep 
            time.sleep(2)

            self.config["TOTAL_TRADES_OPEN"] = len(self.get_pos()) or self.config["TOTAL_TRADES_OPEN"] + 1

            sl_price = round(price - price * SL, price_precision)
            resp2 = self.client.new_order(symbol=pair, side='SELL', type='STOP_MARKET',     quantity=qty, stopPrice=sl_price)
            #sleep
            time.sleep(2)
            
            # Take profit order
            tp_price = round(price + price * TP, price_precision)
            resp3 = self.client.new_order(symbol=pair, side='SELL', type='TAKE_PROFIT_MARKET',  quantity=qty, stopPrice=tp_price)

            logging.info(resp1)
            logging.info(resp2)
            logging.info(resp3)
        except ClientError as error:
            logging.error(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )

    def get_pos(self):
        try:
            resp = self.client.get_position_risk()
            pos = []
            for elem in resp:
                if float(elem['positionAmt']) != 0:
                    pos.append(elem['symbol'])
            return pos
        except ClientError as error:
            print(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
    def check_orders(self):
        try:
            response = self.client.get_orders(recvWindow=6000)
            sym = []
            for elem in response:
                sym.append(elem['symbol'])
            return sym
        except ClientError as error:
            print(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
    # Close open orders for the needed symbol. If one stop order is executed and another one is still there
    def close_open_orders(self, symbol):
        try:
            response = self.client.cancel_open_orders(symbol=symbol, recvWindow=6000)
            print(response)
        except ClientError as error:
            print(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
    
        # Set leverage for the needed symbol. You need this bcz different symbols can have different leverage
    def set_leverage(self,symbol, level):
        try:
            response = self.client.change_leverage(
                symbol=symbol, leverage=level, recvWindow=6000
            )
            print(response)
        except ClientError as error:
            logging.warning(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
    
    # The same for the margin type
    def set_mode(self,symbol, type):
        try:
            response = self.client.change_margin_type(
                symbol=symbol, marginType=type, recvWindow=6000
            )
            
        except ClientError as error:
            logging.warning(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )
  
    def get_price_precision(self, symbol):
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['pricePrecision']
        except ClientError as error:
            logging.warning(
                "Found error. status: {}, error code: {}, error message: {}".format(
                    error.status_code, error.error_code, error.error_message
                )
            )


    def get_qty_precision(self, symbol):
        try:
            resp = self.client.exchange_info()['symbols']
            for elem in resp:
                if elem['symbol'] == symbol:
                    return elem['quantityPrecision']
        except ClientError as error:
            logging.warning(
                "Found error. status: {}, error code: {},error  message: {}".format(
                    error.status_code, error.error_code,error.  error_message
                )
            )

    
    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        logging.info("Binance Quant Trading Engine Started")

        try:
                self.refresh_data()
                self.execute_strategy()
                self.run_count += 1 
        except KeyboardInterrupt:
            logging.info("Engine stopped by user")
            self.running = False
