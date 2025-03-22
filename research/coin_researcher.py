import pandas as pd
from utils.logging import logger

def research_profitable_coins(historical_data):
    profits = {}
    for symbol, df in historical_data.items():
        if len(df) < 289:  # Need 24h data
            profits[symbol] = 0
            continue
        latest_close = df['close'].iloc[-1]
        day_ago_close = df['close'].iloc[-289]  # ~24h in 5m candles
        profit_percent = (latest_close - day_ago_close) / day_ago_close * 100
        profits[symbol] = profit_percent
    ranked = sorted(profits.items(), key=lambda x: x[1], reverse=True)
    top_symbols = [symbol for symbol, _ in ranked]
    logger.debug(f"Top coins at this step: {top_symbols[:4]}")
    return top_symbols