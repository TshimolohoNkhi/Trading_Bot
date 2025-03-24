import matplotlib.pyplot as plt

def plot_equity_curve(equity_curves):
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