from config.config import CONFIG, INITIAL_BALANCE
from utils.indicators import detect_liquidity_sweep, calculate_dynamic_sl_tp
from utils.logging import logger
import pandas as pd
import pandas_ta as ta

def is_bearish_momentum(df):
    df = df.copy()
    df['ema5'] = ta.ema(df['close'], length=5)
    return df['close'].iloc[-1] < df['ema5'].iloc[-1]

def manage_trade(symbol, current_price, trade, balance, trade_history, entry_index, current_index, timestamp):
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
        balance += net_profit
        trade_history.append({"type": "timeout", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
        return balance, None, trade_history
    if current_price >= stop_loss:
        profit_loss = (entry_price - stop_loss) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee
        if balance + net_profit < 0:
            net_profit = -balance
        balance += net_profit
        trade_history.append({"type": "loss", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
        return balance, None, trade_history
    for i, tp in enumerate(tp_targets):
        if not trade["tp_hit"][i] and current_price <= tp:
            profit_loss = (entry_price - tp) * position_size
            fee = position_size * current_price * CONFIG["fee"]
            net_profit = profit_loss - fee
            balance += net_profit
            trade_history.append({"type": "win", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
            return balance, None, trade_history
    if current_price < entry_price:
        new_stop_loss = min(stop_loss, current_price * (1 + CONFIG["trailing_stop_percent"]))
        if new_stop_loss != stop_loss:
            trade["stop_loss"] = new_stop_loss
    return balance, trade, trade_history

def apply_smc_strategy(df, symbol, initial_balance):
    balance = initial_balance
    active_trade = None
    trade_history = []
    equity_curve = [balance]
    for i in range(max(14, 200), len(df)):
        if balance < CONFIG["min_balance"]:
            break
        current_data = df.iloc[:i + 1]
        current_price = current_data['close'].iloc[-1]
        if active_trade:
            balance, active_trade, trade_history = manage_trade(
                symbol, current_price, active_trade, balance, trade_history, 
                active_trade["entry_index"], i, current_data['timestamp'].iloc[-1]
            )
            equity_curve.append(balance)
            continue
        risk_amount = INITIAL_BALANCE * (CONFIG["risk_percent"] / 100)
        if balance < risk_amount:
            break
        if not is_bearish_momentum(current_data):
            continue
        sweeps = detect_liquidity_sweep(current_data)
        latest_sweep = sweeps[-1] if sweeps else None
        if not latest_sweep:
            continue
        sl, tp, _ = calculate_dynamic_sl_tp(current_data)
        entry_price = latest_sweep["entry"] * (1 + CONFIG["slippage"])
        stop_loss_distance = abs(entry_price - (entry_price + sl))
        if stop_loss_distance == 0:
            continue
        position_size = risk_amount / stop_loss_distance
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
        balance -= entry_fee
        equity_curve.append(balance)
    return balance, trade_history, equity_curve