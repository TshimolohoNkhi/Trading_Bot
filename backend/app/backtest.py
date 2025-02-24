# Import required libraries
import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("backtest.log"), logging.StreamHandler()]
)

logger = logging.getLogger()

config = {
    "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
    "risk_percent": 2,  # 2% risk per trade
    "trailing_stop_percent": 0.01,  # 1% Trailing stop
    "tp_levels": [1.5, 2, 3],  # Take Profit at 1.5x, 2x, 3x risk
    "min_adx": 25,  # Minimum ADX value
    "max_spread": 0.0005,  # Maximum allowed spread
    "trade_timeout": 3600,  # Close trades after 1 hour if conditions are not met (in seconds)
    "slippage": 0.001,  # 0.1% slippage
    "fee": 0.00075  # Binance trading fee
}

# Initialize exchange
exchange = ccxt.binance()

# Backtest parameters
initial_balance = 1000  # Starting balance in USDT
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]  # Define symbols once

# Load historical data
def load_historical_data(symbol, interval='1h', limit=1000):
    """Load historical OHLCV data for backtesting."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Load historical data for all symbols
historical_data = {}
for symbol in symbols:
    df = load_historical_data(symbol)
    historical_data[symbol] = df
    print(f"Loaded data for {symbol}:")
    print(df.head())  # Display the first few rows

# Define strategy functions (e.g., get_market_trend, detect_market_structure, etc.)
def get_market_trend(df):
    df['ema200'] = ta.ema(df['close'], length=200)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['ema21'] = ta.ema(df['close'], length=21)

    if df['close'].iloc[-1] > df['ema200'].iloc[-1]:  # Above 200 EMA = Bullish Market
        return "bullish"
    else:  # Below 200 EMA = Bearish Market
        return "bearish"

def detect_market_structure(df):
    structure = []
    for i in range(2, len(df)):
        prev_high = df['high'].iloc[i - 1]
        prev_low = df['low'].iloc[i - 1]
        curr_high = df['high'].iloc[i]
        curr_low = df['low'].iloc[i]

        # ✅ Break of Structure (BOS) - Trend Continuation
        if curr_high > prev_high:
            structure.append({"type": "BOS", "direction": "bullish", "level": prev_high})
        elif curr_low < prev_low:
            structure.append({"type": "BOS", "direction": "bearish", "level": prev_low})

        # ❌ Change of Character (CHOCH) - Trend Reversal
        if curr_high < prev_high and curr_low > prev_low:
            structure.append({"type": "CHOCH", "level": curr_high})

    return structure

def detect_fvg(df):
    fvg_zones = []
    for i in range(2, len(df)):
        high1, low1 = df['high'].iloc[i - 2], df['low'].iloc[i - 2]
        high2, low2 = df['high'].iloc[i - 1], df['low'].iloc[i - 1]
        high3, low3 = df['high'].iloc[i], df['low'].iloc[i]

        if low3 > high1:  # Bullish FVG
            fvg_zones.append({"type": "bullish", "low": high1, "high": low3})
        elif high3 < low1:  # Bearish FVG
            fvg_zones.append({"type": "bearish", "low": low1, "high": high3})

    return fvg_zones

def detect_liquidity_sweep(df):
    sweeps = []
    for i in range(2, len(df)):
        prev_low = df['low'].iloc[i - 1]
        prev_high = df['high'].iloc[i - 1]
        curr_low = df['low'].iloc[i]
        curr_high = df['high'].iloc[i]
        curr_close = df['close'].iloc[i]

        if curr_low < prev_low and curr_close > prev_low:
            sweeps.append({"type": "bullish", "level": prev_low, "entry": curr_close})

        if curr_high > prev_high and curr_close < prev_high:
            sweeps.append({"type": "bearish", "level": prev_high, "entry": curr_close})

    return sweeps

def calculate_dynamic_sl_tp(df):
    latest_atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
    return latest_atr * 1.5, latest_atr * 3  # SL = 1.5x ATR, TP = 3x ATR

def is_trending(df, min_adx=25):
    """Check if the market is trending using ADX."""
    if len(df) < 14:
        return False  # Not enough data to compute ADX

    adx_result = ta.adx(df['high'], df['low'], df['close'], length=14)
    if adx_result is None:
        return False  # Fallback if ADX calculation fails

    df['adx'] = adx_result['ADX_14']
    return df['adx'].iloc[-1] > min_adx

# Define the backtest function using apply_smc_strategy
def apply_smc_strategy(df, initial_balance=1000):
    """Apply the SMC strategy to historical data and simulate trades."""
    balance = initial_balance
    trades = []
    position = None  # Track open position

    for i in range(len(df)):
        current_data = df.iloc[:i + 1]  # Data up to the current candle

        # Check if the market is trending
        if not is_trending(current_data, config["min_adx"]):
            continue

        # Detect market structure, FVG, and liquidity sweeps
        structure = detect_market_structure(current_data)
        fvg_zones = detect_fvg(current_data)
        sweeps = detect_liquidity_sweep(current_data)

        latest_structure = structure[-1] if structure else None
        latest_fvg = fvg_zones[-1] if fvg_zones else None
        latest_sweep = sweeps[-1] if sweeps else None

        if not latest_structure or not latest_fvg or not latest_sweep:
            continue  # No valid signals

        sl, tp = calculate_dynamic_sl_tp(current_data)  # Get dynamic SL/TP

        # Simulate trade execution
        if latest_structure["type"] == "BOS" and latest_fvg["type"] == latest_sweep["type"]:
            entry_price = latest_sweep["entry"]
            if latest_structure["direction"] == "bullish":
                position = {"side": "buy", "entry_price": entry_price, "sl": sl, "tp": tp}
            elif latest_structure["direction"] == "bearish":
                position = {"side": "sell", "entry_price": entry_price, "sl": sl, "tp": tp}

        # Simulate trade management
        if position:
            current_price = current_data['close'].iloc[-1]
            if position["side"] == "buy":
                if current_price <= position["sl"]:  # Stop-loss hit
                    balance *= (1 - (config["risk_percent"] / 100))
                    trades.append({"type": "loss", "balance": balance})
                    position = None
                elif current_price >= position["tp"]:  # Take-profit hit
                    balance *= (1 + (config["risk_percent"] / 100))
                    trades.append({"type": "win", "balance": balance})
                    position = None
            elif position["side"] == "sell":
                if current_price >= position["sl"]:  # Stop-loss hit
                    balance *= (1 - (config["risk_percent"] / 100))
                    trades.append({"type": "loss", "balance": balance})
                    position = None
                elif current_price <= position["tp"]:  # Take-profit hit
                    balance *= (1 + (config["risk_percent"] / 100))
                    trades.append({"type": "win", "balance": balance})
                    position = None

    return balance, trades

# Run backtest for each symbol
results = {}
for symbol in symbols:
    df = historical_data[symbol]
    final_balance, trades = apply_smc_strategy(df, initial_balance)
    results[symbol] = {
        "final_balance": final_balance,
        "total_trades": len(trades),
        "win_rate": len([t for t in trades if t['type'] == 'win']) / len(trades) * 100
    }

# Display results
for symbol, result in results.items():
    print(f"Backtest results for {symbol}:")
    print(f"Initial Balance: {initial_balance}")
    print(f"Final Balance: {result['final_balance']}")
    print(f"Total Trades: {result['total_trades']}")
    print(f"Win Rate: {result['win_rate']:.2f}%")
    print("-" * 50)

# Plot equity curve
plt.figure(figsize=(10, 6))
for symbol, result in results.items():
    plt.plot(result['final_balance'], label=symbol)
plt.title("Equity Curve")
plt.xlabel("Trade Number")
plt.ylabel("Balance (USDT)")
plt.legend()
plt.grid()
plt.show()


