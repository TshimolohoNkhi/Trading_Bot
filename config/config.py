CONFIG = {
    "risk_percent": 5,           # 5% of $28 = $1.40/trade
    "trailing_stop_percent": 0.02,  # 5% trailing stop
    "carryover_percent": 0.2,  # 20% reinvest, 80% reserve
    "max_spread": 0.0005,        # Max allowable spread
    # "tp_levels": [1, 2, 3],      # Multi-level TPs
    "trade_timeout_candles": 50, # 4h timeout on 5m candles
    "tp_levels": [1.2, 2.4, 3.6],# Adjust if needed
    "slippage": 0.001,           # 0.1% slippage
    "fee": 0.00075,              # 0.075% Binance fee
    "min_atr_factor": 0.0001,    # Minimum ATR fallback
    "min_balance": 5,            # Stop if balance < $5
}

INITIAL_BALANCE = 28  # Starting balance in USDT

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "DOGE/USDT", "XRP/USDT", "BNB/USDT",
    "ADA/USDT", "SOL/USDT", "DOT/USDT", "LINK/USDT", "UNI/USDT",
    "SHIB/USDT", "AVAX/USDT", "LTC/USDT", "BCH/USDT", "XLM/USDT",
    "ALGO/USDT", "VET/USDT", "TRX/USDT", "EOS/USDT", "TRX/USDT"
]

INTERVAL = '5m'  # 5-minute candles

LIMIT = '1000'