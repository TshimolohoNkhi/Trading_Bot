from config.config import CONFIG, INITIAL_BALANCE, SYMBOLS
from data.data_fetcher import load_historical_data
from research.coin_researcher import research_profitable_coins
from trading.trader import apply_smc_strategy
from utils.logging import setup_logging
from utils.plotting import plot_equity_curve
import pandas as pd

def run_backtest():
    logger = setup_logging()
    logger.info(f"Starting backtest with initial balance {INITIAL_BALANCE:.2f} USDT...")
    
    # Load data for all 20 coins
    historical_data = {coin: load_historical_data(coin) for coin in SYMBOLS}
    historical_data = {k: v for k, v in historical_data.items() if not v.empty}
    if not historical_data:
        logger.error("No data loaded. Exiting.")
        return
    
    balance = INITIAL_BALANCE
    all_trades = []
    equity_curve = [balance]
    
    # Simulate real-time trading across all coins
    max_length = max(len(df) for df in historical_data.values())
    for i in range(max(14, 200), max_length):
        if balance < CONFIG["min_balance"]:
            logger.info(f"Stopped at step {i}: Balance too low ({balance:.2f})")
            break
        
        # Get current data slice for all coins
        current_data = {symbol: df.iloc[:i + 1] for symbol, df in historical_data.items() if len(df) > i}
        if not current_data:
            continue
        
        # Rank coins and pick top 4 for this trade
        top_symbols = research_profitable_coins(current_data)[:4]
        logger.debug(f"Step {i}: Top coins - {top_symbols}")
        
        # Check each top coin for trade conditions
        for symbol in top_symbols:
            df = current_data[symbol]
            final_balance, trade_history, trade_equity = apply_smc_strategy(df, symbol, balance)
            if trade_history:  # Trade occurred
                all_trades.extend(trade_history)
                balance = final_balance
                equity_curve.extend(trade_equity[1:])
                break  # Move to next step after one trade

    # 20% carryover at end
    total_profit = balance - INITIAL_BALANCE
    trading_balance = balance * CONFIG["carryover_percent"]
    reserve_balance = balance * (1 - CONFIG["carryover_percent"])

    # Summary
    total_trades = len(all_trades)
    total_wins = len([t for t in all_trades if t["type"] == "win"])
    total_losses = len([t for t in all_trades if t["type"] == "loss"])
    total_timeouts = len([t for t in all_trades if t["type"] == "timeout"])
    win_profit = sum(t["profit_loss"] for t in all_trades if t["type"] == "win")
    loss_profit = sum(t["profit_loss"] for t in all_trades if t["type"] in ["loss", "timeout"])
    print(f"Summary (14-day backtest):")
    print(f"  Total Profit: {total_profit:.2f} USDT")
    print(f"  Trading Balance: {trading_balance:.2f} USDT")
    print(f"  Reserve Balance: {reserve_balance:.2f} USDT")
    print(f"  Final Balance: {balance:.2f} USDT")
    print(f"  Total Trades: {total_trades}")
    print(f"  Wins: {total_wins} ({win_profit:.2f} USDT)")
    print(f"  Losses: {total_losses} ({loss_profit:.2f} USDT)")
    print(f"  Timeouts: {total_timeouts}")
    print(f"  Win Rate: {(total_wins / total_trades * 100) if total_trades > 0 else 0:.2f}%")
    plot_equity_curve({'Overall': equity_curve})

if __name__ == "__main__":
    run_backtest()