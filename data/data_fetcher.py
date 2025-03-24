import ccxt
import pandas as pd
from utils.logging import logger
from config.config import INTERVAL, SYMBOLS

"Connects to Binance"
exchange = ccxt.binance()

"Fetches the open, high, low, close and volume data and organises the data into a table as well as turns the date and time into a readable format"
def load_historical_data(symbol, interval=INTERVAL, limit=1000):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error loading data for {symbol}: {e}")
        return None

"Creates an empty dictionary to store data per crypto coin"
historical_data = {}

"Loops through a list of crypto coins and applies the load_historical_data function to each of them"
for symbol in SYMBOLS:
    df = load_historical_data(symbol)
    if df is not None:
        historical_data[symbol] = df
        logger.info(f"Loaded data for {symbol}: {len(df)} rows")
    else:
        logger.warning(f"Skipping {symbol} due to data loading error")