import pandas_ta as ta
import pandas as pd

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
        latest_atr = df['close'].iloc[-1] * 0.0001
    sl = max(latest_atr * 1.0, df['close'].iloc[-1] * 0.0001)
    tp = max(latest_atr * 2.0, df['close'].iloc[-1] * 0.0001 * 2)  # TP 1:2
    return sl, tp, latest_atr