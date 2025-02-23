import ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import websockets
import json
import logging

# ✅ Initialize Exchange
exchange = ccxt.binance()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("trading_bot.log"), logging.StreamHandler()]
)

logger = logging.getLogger()

# ✅ Configurations
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

# ✅ Active Trades Dictionary
active_trades = {}

# ✅ Fetch Market Data
async def get_data(symbol, interval='1h', limit=100):
    for _ in range(3):  # Retry up to 3 times
        try:
            klines = await exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
            return pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}. Retrying...")
            await asyncio.sleep(2)
    return None

# ✅ Trend Identification Function
def get_market_trend(df):
    df['ema200'] = ta.ema(df['close'], length=200)
    df['ema50'] = ta.ema(df['close'], length=50)
    df['ema21'] = ta.ema(df['close'], length=21)

    if df['close'].iloc[-1] > df['ema200'].iloc[-1]:  # Above 200 EMA = Bullish Market
        return "bullish"
    else:  # Below 200 EMA = Bearish Market
        return "bearish"

# ✅ Detect Market Structure (BOS & CHOCH)
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

# ✅ Fair Value Gap (FVG) Detection
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

# ✅ Detect Liquidity Sweeps
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

# ✅ ATR-Based Dynamic Stop-Loss & Take-Profit
def calculate_dynamic_sl_tp(df):
    latest_atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
    return latest_atr * 1.5, latest_atr * 3  # SL = 1.5x ATR, TP = 3x ATR

# ✅ Trade Execution with SMC Strategy
async def apply_smc_strategy(symbol):
    """Apply the SMC strategy to a single symbol."""
    df = await get_data(symbol)
    if df is None:
        return

    # Check if the market is trending
    if not is_trending(df, min_adx):
        logger.info(f"⚠️ {symbol} - Market is not trending. Skipping trade.")
        return

    structure = detect_market_structure(df)
    fvg_zones = detect_fvg(df)
    sweeps = detect_liquidity_sweep(df)
    
    latest_structure = structure[-1] if structure else None
    latest_fvg = fvg_zones[-1] if fvg_zones else None
    latest_sweep = sweeps[-1] if sweeps else None

    if not latest_structure or not latest_fvg or not latest_sweep:
        return  # No valid signals

    sl, tp = calculate_dynamic_sl_tp(df)  # Get dynamic SL/TP

    # ✅ Confirm Entry: Liquidity Sweep + FVG + BOS
    if latest_structure["type"] == "BOS" and latest_fvg["type"] == latest_sweep["type"]:
        if latest_structure["direction"] == "bullish":
            logger.info(f"✅ BUY Entry for {symbol} at {latest_sweep['entry']} (SMC Confirmation)")
            order_id = await place_order(symbol, "buy", latest_sweep["entry"], sl)

        elif latest_structure["direction"] == "bearish":
            logger.info(f"❌ SELL Entry for {symbol} at {latest_sweep['entry']} (SMC Confirmation)")
            order_id = await place_order(symbol, "sell", latest_sweep["entry"], sl)

# ✅ Position & Order Sizing
async def calculate_trade_size(symbol, risk_per_trade):
    balance = await exchange.fetch_balance()
    usdt_balance = balance['total']['USDT']
    risk_amount = (risk_percent / 100) * usdt_balance
    trade_size = risk_amount / risk_per_trade
    return trade_size

# ✅ Place Order with TP Levels
# ✅ Track Open Orders
track_orders = {}

async def place_order(symbol, side, entry_price, atr):
    if symbol in track_orders:
        logger.info(f"⚠️ {symbol} - Order already exists. Skipping duplicate trade.")
        return

    try:
        slippage = 0.001  # 0.1% slippage
        fee = 0.00075  # Binance trading fee

        # Adjust entry price for slippage
        adjusted_entry = entry_price * (1 + slippage) if side == "buy" else entry_price * (1 - slippage)

        # Calculate stop-loss and take-profit levels
        stop_loss = adjusted_entry - (atr * 2) if side == "buy" else adjusted_entry + (atr * 2)
        tp_targets = [adjusted_entry + (abs(adjusted_entry - stop_loss)) * tp if side == "buy" else adjusted_entry - (abs(adjusted_entry - stop_loss)) * tp for tp in tp_levels]

        # Calculate position size, adjusting for fees
        position_size = await calculate_trade_size(symbol, abs(adjusted_entry - stop_loss))
        position_size *= (1 - fee)  # Adjust for fees

        # Place the order
        order = await exchange.create_market_order(symbol, side, position_size)
        logger.info(f"🚀 {side.upper()} order placed for {symbol} at {adjusted_entry:.2f}, Size: {position_size:.4f}")

        # Store trade details
        active_trades[symbol] = {
            "side": side,
            "entry_price": adjusted_entry,
            "stop_loss": stop_loss,
            "tp_targets": tp_targets,
            "tp_hit": [False, False, False],
            "entry_time": asyncio.get_event_loop().time()
        }
        track_orders[symbol] = order["id"]  # Track the order ID
    except Exception as e:
        logger.error(f"⚠️ Error placing order for {symbol}: {e}")

# ✅ Manage Trade (Break-Even & TP Handling)
async def manage_trade(symbol, current_price):
    """Manage active trades, including trailing stop updates."""
    if symbol not in active_trades:
        return

    trade = active_trades[symbol]
    side = trade["side"]
    tp_targets = trade["tp_targets"]
    old_stop_loss = trade["stop_loss"]
    entry_time = trade.get("entry_time", asyncio.get_event_loop().time())

    # ✅ Trade Expiration
    if asyncio.get_event_loop().time() - entry_time > trade_timeout:
        logger.info(f"⏳ {symbol} - Trade expired. Closing position.")
        del active_trades[symbol]
        return

    # ✅ Move SL to Entry at TP1
    if not trade["tp_hit"][0] and ((side == "buy" and current_price >= tp_targets[0]) or (side == "sell" and current_price <= tp_targets[0])):
        trade["stop_loss"] = trade["entry_price"]
        trade["tp_hit"][0] = True
        logger.info(f"🔄 {symbol} - TP1 HIT! Moving SL to ENTRY.")

    # ✅ Partial TP at TP2
    if not trade["tp_hit"][1] and ((side == "buy" and current_price >= tp_targets[1]) or (side == "sell" and current_price <= tp_targets[1])):
        trade["tp_hit"][1] = True
        logger.info(f"💰 {symbol} - TP2 HIT! Securing more profits.")

    # ✅ Close Position at TP3
    if not trade["tp_hit"][2] and ((side == "buy" and current_price >= tp_targets[2]) or (side == "sell" and current_price <= tp_targets[2])):
        trade["tp_hit"][2] = True
        logger.info(f"🏆 {symbol} - TP3 HIT! Closing trade for maximum profits.")
        del active_trades[symbol]  # Remove trade after full TP hit

    # ✅ Trailing Stop-Loss
    if side == "buy" and current_price > trade["entry_price"]:
        new_stop_loss = max(old_stop_loss, current_price * (1 - trailing_stop_percent))
        if new_stop_loss != old_stop_loss:
            logger.info(f"🔄 Adjusting STOP-LOSS for {symbol}: {old_stop_loss:.4f} → {new_stop_loss:.4f}")
            trade["stop_loss"] = new_stop_loss

async def rank_symbols(symbols):
    """Rank symbols based on volatility (ATR) and liquidity (volume)."""
    ranked_symbols = []
    for symbol in symbols:
        df = await get_data(symbol)
        if df is None:
            continue

        # Calculate volatility (ATR) and liquidity (volume)
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
        volume = df['volume'].mean()

        ranked_symbols.append({
            "symbol": symbol,
            "atr": atr,
            "volume": volume
        })

    # Sort by volatility and liquidity (higher is better)
    ranked_symbols.sort(key=lambda x: (x['atr'], x['volume']), reverse=True)
    return ranked_symbols

# ✅ WebSocket for Live Prices
async def binance_websocket():
    """WebSocket for real-time price updates and trailing stop management."""
    while True:
        try:
            uri = "wss://stream.binance.com:9443/ws"
            streams = "/".join([symbol.lower().replace("/", "") + "@ticker" for symbol in config["symbols"]])
            async with websockets.connect(f"{uri}/{streams}") as websocket:
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        symbol = data["s"]
                        price = float(data["c"])

                        # Update trailing stop for active trades
                        if symbol in active_trades:
                            await manage_trade(symbol, price)
                    except Exception as e:
                        logger.error(f"WebSocket error: {e}. Reconnecting...")
                        break
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)

# ✅ Run Bot
async def main():
    """Main function to run the bot."""
    # Start WebSocket for real-time price updates
    asyncio.create_task(binance_websocket())

    # Rank symbols based on volatility and liquidity
    ranked_symbols = await rank_symbols(config["symbols"])
    top_symbols = [s['symbol'] for s in ranked_symbols[:3]]
    logger.info(f"Top symbols for trading: {top_symbols}")

    # Apply the strategy to top symbols
    while True:
        await asyncio.gather(*[apply_smc_strategy(symbol) for symbol in top_symbols])
        await asyncio.sleep(60)  # Wait before the next iteration

asyncio.run(main())
