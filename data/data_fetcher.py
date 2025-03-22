# data/data_fetcher.py
import ccxt
import pandas as pd
from utils.logging import logger
from config.config import INTERVAL, SYMBOLS

exchange = ccxt.binance()

def load_historical_data(symbol, interval=INTERVAL, limit=4032):  # 14 days
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        logger.info(f"Loaded data for {symbol}: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error loading data for {symbol}: {e}")
        return None

exchange = ccxt.binance()
historical_data = {}
for symbol in SYMBOLS:
    df = load_historical_data(symbol)
    if df is not None:
        historical_data[symbol] = df
        logger.info(f"Loaded data for {symbol}: {len(df)} rows")
    else:
        logger.warning(f"Skipping {symbol} due to data loading error")