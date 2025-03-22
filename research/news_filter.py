import requests
import datetime
import talib

# ✅ Fetch News Data (High-Impact Events Only)
def get_high_impact_news():
    url = "https://economic-news-api.com/high-impact-events"
    response = requests.get(url)
    news_data = response.json()
    
    high_impact_news = []
    for event in news_data:
        impact = event["impact"]  # "High", "Medium", "Low"
        event_time = datetime.datetime.strptime(event["time"], "%Y-%m-%d %H:%M:%S")
        
        if impact == "High":
            high_impact_news.append({"time": event_time, "event": event["title"]})

    return high_impact_news

# ✅ Check if Trading Should Be Paused
def is_news_nearby():
    news_events = get_high_impact_news()
    current_time = datetime.datetime.utcnow()

    for news in news_events:
        event_time = news["time"]
        if event_time - datetime.timedelta(minutes=15) <= current_time <= event_time + datetime.timedelta(minutes=30):
            logger.info(f"🚨 HIGH-IMPACT NEWS: {news['event']} at {event_time}. Pausing trades.")
            return True  # Avoid trading

    return False

# ✅ Modify Stop-Loss Based on News Volatility
def adjust_stop_loss(df):
    latest_atr = ta.atr(df['high'], df['low'], df['close'], timeperiod=14).iloc[-1]
    
    if is_news_nearby():
        return latest_atr * 3  # Increase stop-loss buffer
    return latest_atr * 1.5  # Normal stop-loss

# ✅ Integrate News Filter into Trading Strategy
async def apply_smc_strategy(symbol):
    df = await get_data(symbol)
    if df is None:
        return

    if is_news_nearby():
        logger.info(f"🚨 {symbol}: Pausing trading due to upcoming news.")
        return

    structure = detect_market_structure(df)
    fvg_zones = detect_fvg(df)
    sweeps = detect_liquidity_sweep(df)

    latest_structure = structure[-1] if structure else None
    latest_fvg = fvg_zones[-1] if fvg_zones else None
    latest_sweep = sweeps[-1] if sweeps else None

    if not latest_structure or not latest_fvg or not latest_sweep:
        return  # No valid signals

    sl = adjust_stop_loss(df)  # Get dynamic stop-loss

    # ✅ Confirm Entry with SMC + News Filter
    if latest_structure["type"] == "BOS" and latest_fvg["type"] == latest_sweep["type"]:
        if latest_structure["direction"] == "bullish":
            logger.info(f"✅ BUY Entry for {symbol} at {latest_sweep['entry']} (SMC Confirmation)")
            order_id = await place_order(symbol, "buy", latest_sweep["entry"], sl)

        elif latest_structure["direction"] == "bearish":
            logger.info(f"❌ SELL Entry for {symbol} at {latest_sweep['entry']} (SMC Confirmation)")
            order_id = await place_order(symbol, "sell", latest_sweep["entry"], sl)

    # ✅ Trailing Stop Monitoring
    while True:
        current_price = await get_current_price(symbol)
        await update_trailing_stop(order_id, current_price, sl)
        await asyncio.sleep(5)
