# utils/plotting.py
import matplotlib.pyplot as plt

def plot_equity_curve(equity_curves):
    """
    Plot the combined equity curve from trading results.
    
    Args:
        equity_curves (dict): Dictionary of symbol:equity_curve lists
    """
    plt.figure(figsize=(10, 6))
    combined_curve = []
    for symbol in equity_curves.keys():
        combined_curve.extend(equity_curves[symbol])
    plt.plot(combined_curve, label="Trader Equity")
    plt.title("Equity Curve (Dynamic Top 4 Coins)")
    plt.xlabel("Trade Step")
    plt.ylabel("Balance (USDT)")
    plt.legend()
    plt.grid()
    plt.show()