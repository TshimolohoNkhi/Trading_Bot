import ccxt.async_support as ccxt
import pandas as pd
import talib
import asyncio
import websockets
import json

# ✅ Initialize Exchange
exchange = ccxt.binance()

# ✅ Configurations
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
risk_percent = 2  # 2% risk per trade
trailing_stop_percent = 0.01  # 1% Trailing stop
tp_levels = [1.5, 2, 3]  # Take Profit at 1.5x, 2x, 3x risk
min_adx = 25  # Minimum ADX value
max_spread = 0.0005  # Maximum allowed spread

# ✅ Active Trades Dictionary
active_trades = {}

# ✅ Fetch Market Data
async def get_data(client, symbol, interval):
    """Fetch historical OHLCV data with retry logic"""
    for _ in range(3):
        try:
            klines = await client.get_klines(symbol=symbol, interval=interval, limit=100)
            return klines
        except BinanceAPIException as e:
            logging.error(f"Binance API Error: {e}")
            await asyncio.sleep(2)
    return None

# ✅ Trend Identification Function
def get_market_trend(df):
    df['ema200'] = talib.EMA(df['close'], timeperiod=200)
    df['ema50'] = talib.EMA(df['close'], timeperiod=50)
    df['ema21'] = talib.EMA(df['close'], timeperiod=21)

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
    latest_atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14).iloc[-1]
    return latest_atr * 1.5, latest_atr * 3  # SL = 1.5x ATR, TP = 3x ATR

# ✅ Trade Execution with SMC Strategy
async def apply_smc_strategy(symbol):
    df = await get_data(symbol)
    if df is None:
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
            print(f"✅ BUY Entry for {symbol} at {latest_sweep['entry']} (SMC Confirmation)")
            order_id = await place_order(symbol, "buy", latest_sweep["entry"], sl)

        elif latest_structure["direction"] == "bearish":
            print(f"❌ SELL Entry for {symbol} at {latest_sweep['entry']} (SMC Confirmation)")
            order_id = await place_order(symbol, "sell", latest_sweep["entry"], sl)

    # ✅ Trailing Stop Monitoring
    while True:
        current_price = await get_current_price(symbol)
        await update_trailing_stop(order_id, current_price, sl)
        await asyncio.sleep(5)  # Adjust every 5 seconds

# ✅ Position & Order Sizing
async def calculate_trade_size(symbol, risk_per_trade):
    balance = await exchange.fetch_balance()
    usdt_balance = balance['total']['USDT']
    risk_amount = (risk_percent / 100) * usdt_balance
    trade_size = risk_amount / risk_per_trade
    return trade_size

# ✅ Place Order with TP Levels
async def place_order(symbol, side, entry_price, atr):
    try:
        stop_loss = entry_price - (atr * 2) if side == "buy" else entry_price + (atr * 2)
        tp_targets = [entry_price + (abs(entry_price - stop_loss) * tp) if side == "buy" else entry_price - (abs(entry_price - stop_loss) * tp) for tp in tp_levels]
        position_size = await calculate_trade_size(symbol, abs(entry_price - stop_loss))

        order = await exchange.create_market_order(symbol, side, position_size)
        print(f"🚀 {side.upper()} order placed for {symbol} at {entry_price}, Size: {position_size:.4f}")

        # Store trade details
        active_trades[symbol] = {
            "side": side,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "tp_targets": tp_targets,
            "tp_hit": [False, False, False]  # Track TP levels
        }

    except Exception as e:
        print(f"⚠️ Error placing order for {symbol}: {e}")

# ✅ Manage Trade (Break-Even & TP Handling)
async def manage_trade(symbol, current_price):
    if symbol not in active_trades:
        return

    trade = active_trades[symbol]
    side = trade["side"]
    tp_targets = trade["tp_targets"]
    old_stop_loss = trade["stop_loss"]

    # ✅ Move SL to Entry at TP1
    if not trade["tp_hit"][0] and ((side == "buy" and current_price >= tp_targets[0]) or (side == "sell" and current_price <= tp_targets[0])):
        trade["stop_loss"] = trade["entry_price"]
        trade["tp_hit"][0] = True
        print(f"🔄 {symbol} - TP1 HIT! Moving SL to ENTRY.")

    # ✅ Partial TP at TP2
    if not trade["tp_hit"][1] and ((side == "buy" and current_price >= tp_targets[1]) or (side == "sell" and current_price <= tp_targets[1])):
        trade["tp_hit"][1] = True
        print(f"💰 {symbol} - TP2 HIT! Securing more profits.")

    # ✅ Close Position at TP3
    if not trade["tp_hit"][2] and ((side == "buy" and current_price >= tp_targets[2]) or (side == "sell" and current_price <= tp_targets[2])):
        trade["tp_hit"][2] = True
        print(f"🏆 {symbol} - TP3 HIT! Closing trade for maximum profits.")
        del active_trades[symbol]  # Remove trade after full TP hit

    # ✅ Trailing Stop-Loss
    if side == "buy" and current_price > trade["entry_price"]:
        new_stop_loss = max(old_stop_loss, current_price * (1 - trailing_stop_percent))
        if new_stop_loss != old_stop_loss:
            print(f"🔄 Adjusting STOP-LOSS for {symbol}: {old_stop_loss:.4f} → {new_stop_loss:.4f}")
            trade["stop_loss"] = new_stop_loss

# ✅ WebSocket for Live Prices
async def binance_websocket():
    uri = "wss://stream.binance.com:9443/ws"
    streams = "/".join([symbol.lower().replace("/", "") + "@ticker" for symbol in symbols])
    async with websockets.connect(f"{uri}/{streams}") as websocket:
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                symbol = data["s"]
                price = float(data["c"])

                # Update TP and SL
                if symbol in active_trades:
                    await manage_trade(symbol, price)
                    
            except Exception as e:
                print(f"WebSocket error: {e}")

# ✅ Run Bot
async def main():
    asyncio.create_task(binance_websocket())  # Start WebSocket
    while True:
        await asyncio.gather(*[apply_strategy(symbol) for symbol in symbols])
        await asyncio.sleep(60)

asyncio.run(main())
