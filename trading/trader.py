from config.config import CONFIG, INITIAL_BALANCE
from utils.indicators import detect_liquidity_sweep, calculate_dynamic_sl_tp
from utils.logging import logger
import pandas_ta as ta

"Finds favourable short-selling opportunities to enter a trade as well as manages active trades and performs calculations"
def apply_smc_strategy(current_data_dict, top_symbols, symbol, initial_balance, active_trade=None):
    balance = initial_balance
    trade_history = []
    equity_curve = [balance]

    "Checks if a trade is active manage_trade function is called to manage stop-loss take profit level hits then returns the balance and equity curve"
    if active_trade:
        current_data = current_data_dict[symbol]
        current_price = current_data['close'].iloc[-1]
        timestamp = current_data['timestamp'].iloc[-1]
        balance, active_trade, trade_history = manage_trade(
            symbol, current_price, active_trade, balance, trade_history,
            active_trade["entry_index"], len(current_data) - 1, timestamp
        )
        equity_curve.append(balance)
        return balance, active_trade, trade_history, equity_curve, symbol

    "Checks if there are funds to trade before entering a trade, if not, it skips the trade and logs a warning"
    if balance < CONFIG["min_balance"]:
        logger.warning(f"Balance too low ({balance:.2f}) to trade")
        return balance, None, trade_history, equity_curve, None

    "Performs risk calculation (how much money can be lost during a trade, which is $1.40)"
    risk_amount = INITIAL_BALANCE * (CONFIG["risk_percent"] / 100)
    if balance < risk_amount:
        logger.warning(f"Insufficient balance ({balance:.2f}) to trade")
        return balance, None, trade_history, equity_curve, None

    "Loops through top 4 coins and checks if coins has a bearish momentum and liquidity sweeps"
    for watch_symbol in top_symbols:
        current_data = current_data_dict[watch_symbol]
        current_price = current_data['close'].iloc[-1]
        timestamp = current_data['timestamp'].iloc[-1]

        "If not skip current coin and proceed with the next coin"
        if not is_bearish_momentum(current_data):
            continue

        "Checks for liquidity sweeps, if not skip current coin and proceed with the next coin"
        sweeps = detect_liquidity_sweep(current_data)
        latest_sweep = sweeps[-1] if sweeps else None
        if not latest_sweep:
            continue

        "If bearish momentum and liquidity sweep exist, stop loss and take profit levels are calculated by calling calculate_dynamic_sl_tp"
        sl, tp = calculate_dynamic_sl_tp(current_data)
        entry_price = latest_sweep["entry"] * (1 + CONFIG["slippage"])
        stop_loss_distance = abs(entry_price - (entry_price + sl))
        if stop_loss_distance == 0:
            logger.warning(f"{watch_symbol}: Zero stop loss distance at entry {entry_price:.2f}")
            continue

        "Performs position size calculation"
        position_size = risk_amount / stop_loss_distance
        logger.debug(f"{watch_symbol}: Balance={balance:.2f}, Risk={risk_amount:.2f}, ATR={sl:.2f}, SL_Dist={stop_loss_distance:.2f}, Pos_Size={position_size:.4f}, Entry_Price={entry_price:.2f}")

        "Ensures that the balance suffices to pay for trading fees, if it does, proceed"
        entry_fee = position_size * entry_price * CONFIG["fee"]
        if balance - entry_fee < 0:
            continue
        
        "Enters trade based on previous conditions and calculations and logs outcome"
        active_trade = {
            "side": "sell",
            "entry_price": entry_price,
            "stop_loss": entry_price + sl,
            "position_size": position_size,
            "tp_targets": [entry_price - sl * level for level in CONFIG["tp_levels"]],
            "tp_hit": [False] * len(CONFIG["tp_levels"]),
            "entry_index": len(current_data) - 1,
            "entry_fee": entry_fee
        }
        logger.info(f"📈 {watch_symbol}: Entry={entry_price:.2f}, SL={active_trade['stop_loss']:.2f}, TP={active_trade['tp_targets'][0]:.2f}, Size={position_size:.4f}, Fee={entry_fee:.4f}")
        balance -= entry_fee
        equity_curve.append(balance)
        return balance, active_trade, trade_history, equity_curve, watch_symbol

    "If none of the top 4 coins met the conditions, balance is returned"
    return balance, None, trade_history, equity_curve, None

"Checks if the last price is lower than the average price, if so is_bearish_momentim is true"
def is_bearish_momentum(df):
    df = df.copy()
    df.loc[:, 'ema5'] = ta.ema(df['close'], length=5)
    return df['close'].iloc[-1] < df['ema5'].iloc[-1]

"Manages trades after they have been opened, ensures values are updated after timeouts, stop-losses and take profits"
def manage_trade(symbol, current_price, trade, balance, trade_history, entry_index, current_index, timestamp):
    if trade is None:
        return balance, None, trade_history

    entry_price = trade["entry_price"]
    stop_loss = trade["stop_loss"]
    tp_targets = trade["tp_targets"]
    position_size = trade["position_size"]
    entry_fee = trade.get("entry_fee", 0)

    "If trade has been open for too long, close trade and return updated balance and trading history"
    candles_elapsed = current_index - entry_index
    if candles_elapsed >= CONFIG["trade_timeout_candles"]:
        profit_loss = (entry_price - current_price) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee - entry_fee
        if balance + net_profit < 0:
            net_profit = -balance
        logger.info(f"⏳ {symbol} - Expired at {current_price:.4f}, P/L: {profit_loss:.4f}, Fee: {fee:.4f}, Net: {net_profit:.4f}, Size: {position_size:.4f}")
        balance += net_profit
        trade_history.append({"type": "timeout", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
        return balance, trade, trade_history

    "If trade hit stop loss, close trade as a loss, return updated balance and trading history"
    if current_price >= stop_loss:
        profit_loss = (entry_price - stop_loss) * position_size
        fee = position_size * current_price * CONFIG["fee"]
        net_profit = profit_loss - fee - entry_fee
        if balance + net_profit < 0:
            net_profit = -balance
        logger.info(f"❌ {symbol} - SL HIT at {current_price:.4f}, P/L: {profit_loss:.4f}, Fee: {fee:.4f}, Net: {net_profit:.4f}, Size: {position_size:.4f}")
        balance += net_profit
        trade_history.append({"type": "loss", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
        return balance, None, trade_history

    "If trade hit a take profit level that has not been hit before, close trade at a profit, return updated. balance and trading history"
    for i, tp in enumerate(tp_targets):
        if not trade["tp_hit"][i] and current_price <= tp:
            profit_loss = (entry_price - tp) * position_size
            fee = position_size * current_price * CONFIG["fee"]
            net_profit = profit_loss - fee - entry_fee
            logger.info(f"🏆 {symbol} - TP{i+1} HIT at {current_price:.4f}, P/L: {profit_loss:.4f}, Fee: {fee:.4f}, Net: {net_profit:.4f}, Size: {position_size:.4f}")
            balance += net_profit
            trade_history.append({"type": "win", "profit_loss": net_profit, "symbol": symbol, "timestamp": timestamp})
            return balance, None, trade_history

    "If trade moves favourably adjust stop-loss to lock in profits"
    if current_price < entry_price:
        new_stop_loss = min(stop_loss, current_price * (1 + CONFIG["trailing_stop_percent"]))
        if new_stop_loss != stop_loss:
            logger.debug(f"🔄 {symbol} - Adjusting SL: {stop_loss:.4f} → {new_stop_loss:.4f}")
            trade["stop_loss"] = new_stop_loss

    "If none of the above are met, return balance and trade information and try again"
    return balance, trade, trade_history