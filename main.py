from config.config import CONFIG, INITIAL_BALANCE, SYMBOLS
from data.data_fetcher import load_historical_data
from research.coin_researcher import research_profitable_coins
from trading.trader import apply_smc_strategy
from utils.logging import setup_logging
from utils.plotting import plot_equity_curve
import pandas as pd
from datetime import datetime, timedelta

def run_daily_backtest(days=14):
    logger = setup_logging()
    end_date = datetime.now(tz=datetime.UTC)  # Fix deprecation warning
    start_date = end_date - timedelta(days=days)
    logger.info(f"Starting backtest from {start_date.date()} to {end_date.date()}...")
    historical_data = {coin: load_historical_data(coin, limit=4032) for coin in SYMBOLS}  # 14 days
    balance = INITIAL_BALANCE
    daily_results = {}
    all_trades = []
    equity_curves = {coin: [balance] for coin in SYMBOLS}

    # Initialize all days
    for day_offset in range(days + 1):
        day = (start_date + timedelta(days=day_offset)).date()
        daily_results[day] = {"profit": 0, "trades": 0, "wins": 0, "losses": 0, "timeouts": 0, 
                             "coin_trades": {}, "coin_profits": {}, "trade_details": []}

    # Trade loop with per-candle research
    max_len = max(len(historical_data[symbol]) for symbol in SYMBOLS)
    for i in range(max(14, 200), max_len):
        if balance < CONFIG["min_balance"]:
            logger.info(f"Stopped: Balance {balance:.2f} below minimum {CONFIG['min_balance']}")
            break
        current_data = {symbol: df.iloc[:i + 1] for symbol, df in historical_data.items()}
        top_symbols = research_profitable_coins(current_data)  # Research each step
        for symbol in top_symbols[:1]:  # Trade top 1 coin per candle
            final_balance, trade_history, equity_curve = apply_smc_strategy(
                current_data[symbol], symbol, balance
            )
            if trade_history:
                latest_trade = trade_history[-1]
                all_trades.append(latest_trade)
                balance = final_balance
                equity_curves[symbol].append(balance)
                day = pd.to_datetime(latest_trade["timestamp"], unit='ms').date()
                daily_results[day]["profit"] += latest_trade["profit_loss"]
                daily_results[day]["trades"] += 1
                daily_results[day]["coin_trades"][symbol] = daily_results[day]["coin_trades"].get(symbol, 0) + 1
                daily_results[day]["coin_profits"][symbol] = daily_results[day]["coin_profits"].get(symbol, 0) + latest_trade["profit_loss"]
                daily_results[day]["trade_details"].append(latest_trade)
                if latest_trade["type"] == "win":
                    daily_results[day]["wins"] += 1
                elif latest_trade["type"] == "loss":
                    daily_results[day]["losses"] += 1
                elif latest_trade["type"] == "timeout":
                    daily_results[day]["timeouts"] += 1
            else:
                equity_curves[symbol].append(balance)

    # Print Daily Results
    for day in sorted(daily_results.keys()):
        print(f"Day ({day}):")
        print(f"  Total Profit: {daily_results[day]['profit']:.2f} USDT")
        print(f"  Total Trades: {daily_results[day]['trades']} (Wins: {daily_results[day]['wins']}, Losses: {daily_results[day]['losses']}, Timeouts: {daily_results[day]['timeouts']})")
        print(f"  Coins Traded: {daily_results[day]['coin_trades']}")
        print(f"  Coin Profits: {daily_results[day]['coin_profits']}")
        if daily_results[day]["trades"] > 0:
            max_profit_trade = max(daily_results[day]["trade_details"], key=lambda x: x["profit_loss"])
            min_profit_trade = min(daily_results[day]["trade_details"], key=lambda x: x["profit_loss"])
            print(f"  Most Profitable: {max_profit_trade['symbol']} ({max_profit_trade['profit_loss']:.2f} USDT, {max_profit_trade['type']})")
            print(f"  Least Profitable: {min_profit_trade['symbol']} ({min_profit_trade['profit_loss']:.2f} USDT, {min_profit_trade['type']})")
        print("-" * 50)

    # Summary
    total_profit = sum(dr["profit"] for dr in daily_results.values())
    total_trades = sum(dr["trades"] for dr in daily_results.values())
    total_wins = sum(dr["wins"] for dr in daily_results.values())
    total_losses = sum(dr["losses"] for dr in daily_results.values())
    total_timeouts = sum(dr["timeouts"] for dr in daily_results.values())
    win_profit = sum(t["profit_loss"] for t in all_trades if t["type"] == "win")
    loss_profit = sum(t["profit_loss"] for t in all_trades if t["type"] in ["loss", "timeout"])
    print(f"Summary ({start_date.date()} to {end_date.date()}):")
    print(f"  Total Profit: {total_profit:.2f} USDT")
    print(f"  Trader Balance: {balance:.2f} USDT")
    print(f"  Total Trades: {total_trades}")
    print(f"  Wins: {total_wins} ({win_profit:.2f} USDT)")
    print(f"  Losses: {total_losses} ({loss_profit:.2f} USDT)")
    print(f"  Timeouts: {total_timeouts} ({loss_profit:.2f} USDT)")
    print(f"  Win Rate: {(total_wins / total_trades * 100) if total_trades > 0 else 0:.2f}%")
    plot_equity_curve(equity_curves)

if __name__ == "__main__":
    run_daily_backtest(days=14)