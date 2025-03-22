CONFIG = {
    "risk_percent": 5,           # 5% of $28 = $1.40/trade
    "trailing_stop_percent": 0.01,  # 1% trailing stop
    "tp_levels": [2],          # 1:1.5 TP ratio
    "max_spread": 0.0005,        # Max allowable spread
    "trade_timeout_candles": 48, # 4h timeout on 5m candles
    "slippage": 0.001,           # 0.1% slippage
    "fee": 0.00075,              # 0.075% Binance fee
    "min_atr_factor": 0.0001,    # Minimum ATR fallback
    "min_balance": 5,            # Stop if balance < $5
    "min_atr_percent": 0.005,    # 0.5% min ATR
    "min_volume_factor": 1.5,    # Volume > 1.5x 20-MA
    "profit_split_percent": 0.5  # 50% of profits to portfolio
}

INITIAL_BALANCE = 28  # Starting balance in USDT
CARRYOVER_PERCENT = 0.2 

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "DOGE/USDT", "XRP/USDT",
    "SOL/USDT", "BNB/USDT", "ADA/USDT", "UNI/USDT",
    "LTC/USDT", "TAO/USDT", "FET/USDT", "MANA/USDT",
]

INTERVAL = '5m'  # 5-minute candles