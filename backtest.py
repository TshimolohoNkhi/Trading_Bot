import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("backtest.log"), logging.StreamHandler()]
)
logger = logging.getLogger()

CONFIG = {
    "risk_percent": 5,  # 5% of $28 = $1.40/trade
    "trailing_stop_percent": 0.01,
    "tp_levels": [2],
    "max_spread": 0.0005,
    "trade_timeout_candles": 48,
    "slippage": 0.001,
    "fee": 0.00075,
    "min_atr_factor": 0.0001,
    "min_balance": 5
}

INITIAL_BALANCE = 28
CARRYOVER_PERCENT = 0.2  # 20% of final balance
SYMBOLS = ["BTC/USDT", "ETH/USDT", "DOGE/USDT", "XRP/USDT"]
INTERVAL = '5m'

def load_historical_data(symbol, interval=INTERVAL, limit=1000):  # Match your 1000 rows
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=interval, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
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

def detect_liquidity_sweep(df):
    sweeps = []
    for i in range(2, len(df)):
        prev_high = df['high'].iloc[i - 1]
        curr_high = df['high'].iloc[i]
        curr_close = df['close'].iloc[i]
        if curr_high > prev_high and curr_close < prev_high:
            sweeps.append({"type": "bearish", "level": prev_high, "entry": curr_close})
    return sweeps

def calculate_dynamic_sl_tp(df):
    latest_atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
    if pd.isna(latest_atr) or latest_atr <= 0:
        latest_atr = df['close'].iloc[-1] * CONFIG["min_atr_factor"]
    sl = max(latest_atr * 1.0, df['close'].iloc[-1] * CONFIG["min_atr_factor"])
    tp = max(latest_atr * 2.0, df['close'].iloc[-1] * CONFIG["min_atr_factor"] * 2)
    return sl, tp

def is_bearish_momentum(df):
    df = df.copy()
    df.loc[:, 'ema5'] = ta.ema(df['close'], length=5)
    return df['close'].iloc[-1] < df['ema5'].iloc[-1]  # Fixed typo!

def manage_trade(symbol, current_price, trade, balance, trade_history, entry_index, current_index):
    if trade is None:
        return balance, trade, trade_history

    entry_price = trade["entry_price"]
    stop_loss = trade["stop_loss"]
    tp_targets = trade["tp_targets"]
    position_size = trade["position_size"]

    candles_elapsed = current_index - entry_index
    if candles_elapsed >= CONFIG["trade_timeout_candles"]:
        profit_loss = (entry_price - current_price) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee
        if balance + net_profit < 0:
            net_profit = -balance
        logger.info(f"⏳ {symbol} - Expired at {current_price:.2f}, P/L: {profit_loss:.4f}, Fee: {fee:.4f}, Net: {net_profit:.4f}, Size: {position_size:.4f}")
        balance += net_profit
        trade_history.append({"type": "timeout", "profit_loss": net_profit, "symbol": symbol, "entry_price": entry_price, "exit_price": current_price})
        return balance, None, trade_history

    if current_price >= stop_loss:
        profit_loss = (entry_price - stop_loss) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee
        if balance + net_profit < 0:
            net_profit = -balance
        logger.info(f"❌ {symbol} - SL HIT at {current_price:.2f}, P/L: {profit_loss:.4f}, Fee: {fee:.4f}, Net: {net_profit:.4f}, Size: {position_size:.4f}")
        balance += net_profit
        trade_history.append({"type": "loss", "profit_loss": net_profit, "symbol": symbol, "entry_price": entry_price, "exit_price": stop_loss})
        return balance, None, trade_history

    for i, tp in enumerate(tp_targets):
        if not trade["tp_hit"][i] and current_price <= tp:
            profit_loss = (entry_price - tp) * position_size
            fee = position_size * current_price * CONFIG["fee"]
            net_profit = profit_loss - fee
            logger.info(f"🏆 {symbol} - TP{i+1} HIT at {current_price:.2f}, P/L: {profit_loss:.4f}, Fee: {fee:.4f}, Net: {net_profit:.4f}, Size: {position_size:.4f}")
            balance += net_profit
            trade_history.append({"type": "win", "profit_loss": net_profit, "symbol": symbol, "entry_price": entry_price, "exit_price": tp})
            return balance, None, trade_history

    if current_price < entry_price:
        new_stop_loss = min(stop_loss, current_price * (1 + CONFIG["trailing_stop_percent"]))
        if new_stop_loss != stop_loss:
            logger.info(f"🔄 {symbol} - Adjusting SL: {stop_loss:.2f} → {new_stop_loss:.2f}")
            trade["stop_loss"] = new_stop_loss

    return balance, trade, trade_history

def apply_smc_strategy(df, symbol, initial_balance):
    balance = initial_balance
    active_trade = None
    trade_history = []
    equity_curve = [balance]

    for i in range(max(14, 200), len(df)):
        if balance < CONFIG["min_balance"]:
            logger.warning(f"{symbol}: Balance too low ({balance:.2f}) to continue")
            break

        current_data = df.iloc[:i + 1]
        current_price = current_data['close'].iloc[-1]

        if active_trade:
            balance, active_trade, trade_history = manage_trade(
                symbol, current_price, active_trade, balance, trade_history, active_trade["entry_index"], i
            )
            equity_curve.append(balance)
            continue

        risk_amount = INITIAL_BALANCE * (CONFIG["risk_percent"] / 100)  # Fixed $1.40/trade
        if balance < risk_amount:
            logger.warning(f"{symbol}: Insufficient balance ({balance:.2f}) to trade")
            break

        if not is_bearish_momentum(current_data):
            continue

        sweeps = detect_liquidity_sweep(current_data)
        latest_sweep = sweeps[-1] if sweeps else None
        if not latest_sweep:
            continue

        sl, tp = calculate_dynamic_sl_tp(current_data)
        entry_price = latest_sweep["entry"] * (1 + CONFIG["slippage"])
        stop_loss_distance = abs(entry_price - (entry_price + sl))
        if stop_loss_distance == 0:
            logger.warning(f"{symbol}: Zero stop loss distance at entry {entry_price:.2f}")
            continue

        position_size = risk_amount / stop_loss_distance
        logger.debug(f"{symbol}: Balance={balance:.2f}, Risk={risk_amount:.2f}, ATR={sl/1.0:.2f}, SL_Dist={stop_loss_distance:.2f}, Pos_Size={position_size:.4f}, Entry_Price={entry_price:.2f}")

        active_trade = {
            "side": "sell",
            "entry_price": entry_price,
            "stop_loss": entry_price + sl,
            "position_size": position_size,
            "tp_targets": [entry_price - sl * level for level in CONFIG["tp_levels"]],
            "tp_hit": [False],
            "entry_index": i
        }

        entry_fee = position_size * entry_price * CONFIG["fee"]
        logger.info(f"📈 {symbol}: Entry={entry_price:.2f}, SL={active_trade['stop_loss']:.2f}, TP={active_trade['tp_targets'][0]:.2f}, Size={position_size:.4f}, Fee={entry_fee:.4f}")
        balance -= entry_fee
        equity_curve.append(balance)

    return balance, trade_history, equity_curve

results = {}
equity_curves = {}
balance = INITIAL_BALANCE

try:
    for symbol in SYMBOLS:
        logger.info(f"Running backtest for {symbol} with starting balance {balance:.2f}")
        final_balance, trade_history, equity_curve = apply_smc_strategy(historical_data[symbol], symbol, balance)
        wins = len([t for t in trade_history if t['type'] == 'win'])
        losses = len([t for t in trade_history if t['type'] == 'loss'])
        timeouts = len([t for t in trade_history if t['type'] == 'timeout'])
        total_trades = len(trade_history)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        profit = final_balance - balance
        avg_profit_loss = profit / total_trades if total_trades > 0 else 0
        max_drawdown = min(0, min(equity_curve) - balance)

        results[symbol] = {
            "initial_balance": balance,
            "final_balance": final_balance,
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "timeouts": timeouts,
            "win_rate": win_rate,
            "profit": profit,
            "avg_profit_loss": avg_profit_loss,
            "max_drawdown": max_drawdown
        }
        equity_curves[symbol] = equity_curve
        balance = final_balance  # Carry forward within cycle

    # 20% carryover to next cycle
    final_cycle_balance = balance
    balance = final_cycle_balance * CARRYOVER_PERCENT
    banked_amount = final_cycle_balance * (1 - CARRYOVER_PERCENT)

    if not results:
        print("No backtesting results generated.")
    else:
        total_profit = sum(result["profit"] for result in results.values())
        print(f"Total profit over 4-week cycle: {total_profit:.2f} USDT")
        print(f"Average weekly profit: {total_profit / 4:.2f} USDT/week")
        print(f"Next cycle starting balance: {balance:.2f} USDT")
        print(f"Banked amount: {banked_amount:.2f} USDT")
        for symbol, result in results.items():
            print(f"Backtest results for {symbol}:")
            print(f"Initial Balance: {result['initial_balance']:.2f} USDT")
            print(f"Final Balance: {result['final_balance']:.2f} USDT")
            print(f"Profit: {result['profit']:.2f} USDT")
            print(f"Total Trades: {result['total_trades']}")
            print(f"Wins: {result['wins']}")
            print(f"Losses: {result['losses']}")
            print(f"Timeouts: {result['timeouts']}")
            print(f"Win Rate: {result['win_rate']:.2f}%")
            print(f"Average Profit/Loss per Trade: {result['avg_profit_loss']:.2f} USDT")
            print(f"Max Drawdown: {result['max_drawdown']:.2f} USDT")
            print("-" * 50)

    if equity_curves:
        plt.figure(figsize=(10, 6))
        combined_curve = []
        for symbol in SYMBOLS:
            combined_curve.extend(equity_curves[symbol])
        plt.plot(combined_curve, label="Combined Equity")
        plt.title("Equity Curve (4 Coins, 20% Carryover)")
        plt.xlabel("Trade Step")
        plt.ylabel("Balance (USDT)")
        plt.legend()
        plt.grid()
        plt.show()

except Exception as e:
    logger.error(f"Error during backtesting: {e}")
    print(f"An error occurred: {e}")



