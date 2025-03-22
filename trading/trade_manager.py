from config.config import CONFIG
from utils.logging import logger

def manage_trade(symbol, current_price, trade, balance, trade_history, entry_index, current_index):
    if trade is None:
        return balance, trade, trade_history
    entry_price = trade["entry_price"]
    stop_loss = trade["stop_loss"]
    tp_targets = trade["tp_targets"]
    position_size = trade["position_size"]
    timestamp = trade["timestamp"]
    candles_elapsed = current_index - entry_index
    if candles_elapsed >= CONFIG["trade_timeout_candles"]:
        profit_loss = (entry_price - current_price) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee
        if balance + net_profit < 0:
            net_profit = -balance
        trade_history.append({"type": "timeout", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
        balance += net_profit
        return balance, None, trade_history
    if current_price >= stop_loss:
        profit_loss = (entry_price - stop_loss) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee
        if balance + net_profit < 0:
            net_profit = -balance
        trade_history.append({"type": "loss", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
        balance += net_profit
        return balance, None, trade_history
    for i, tp in enumerate(tp_targets):
        if not trade["tp_hit"][i] and current_price <= tp:
            profit_loss = (entry_price - tp) * position_size
            fee = position_size * current_price * CONFIG["fee"]
            net_profit = profit_loss - fee
            trade_history.append({"type": "win", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
            balance += net_profit
            return balance, None, trade_history
    if current_price < entry_price:
        new_stop_loss = min(stop_loss, current_price * (1 + CONFIG["trailing_stop_percent"]))
        if new_stop_loss != stop_loss:
            trade["stop_loss"] = new_stop_loss
    return balance, trade, trade_history