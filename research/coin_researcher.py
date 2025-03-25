from utils.logging import logger
import pandas as pd
import pandas_ta as ta
import requests
from textblob import TextBlob  # For sentiment analysis
from config.config import SYMBOLS, CONFIG

"Fetches sentiment from the news, X and Reddit and returns a combined sentiment score"
def fetch_sentiment(symbol):
    try:
        # Mock APIs - replace with real ones (NewsAPI, Tweepy, PRAW) for live use
        news_response = {"data": [{"title": f"{symbol.split('/')[0]} dips"}] * 5}  # Mock bearish news
        news_text = " ".join([item["title"] for item in news_response["data"]])

        x_response = {"data": [{"text": f"{symbol.split('/')[0]} sell-off"}] * 10}  # Mock X posts
        x_text = " ".join([post["text"] for post in x_response["data"]])

        reddit_response = {"data": [{"title": f"{symbol.split('/')[0]} crashing"}] * 5}  # Mock Reddit
        reddit_text = " ".join([post["title"] for post in reddit_response["data"]])

        combined_text = f"{news_text} {x_text} {reddit_text}".strip()
        if not combined_text:
            return 0.0

        sentiment = TextBlob(combined_text).sentiment.polarity
        logger.debug(f"{symbol}: Sentiment score = {sentiment:.2f}")
        return sentiment
    except Exception as e:
        logger.error(f"Sentiment fetch failed for {symbol}: {e}")
        return 0.0

"Checks if coin is volatile and is bearish and returns a score for market favourability"
def is_favorable_market(current_data):
    if not current_data:
        return False

    volatilities = []
    momentum_scores = []
    for symbol, df in current_data.items():
        if len(df) < 14:
            continue
        atr = ta.atr(df['high'], df['low'], df['close'], length=14).iloc[-1]
        volatility = atr / df['close'].iloc[-1]
        volatilities.append(volatility)

        df_copy = df.copy()
        df_copy['ema5'] = ta.ema(df_copy['close'], length=5)
        momentum = df_copy['close'].iloc[-1] < df_copy['ema5'].iloc[-1]
        momentum_scores.append(1 if momentum else 0)

    if not volatilities or not momentum_scores:
        return False

    avg_volatility = sum(volatilities) / len(volatilities)
    bearish_ratio = sum(momentum_scores) / len(momentum_scores)

    favorable = avg_volatility > 0.005 and bearish_ratio > 0.6
    logger.debug(f"Market check: Avg Volatility = {avg_volatility:.4f}, Bearish Ratio = {bearish_ratio:.2f}, Favorable = {favorable}")
    return favorable

"Ranks profitable coins based on volatility, bearish momentum and bearish media sentiment"
def research_profitable_coins(current_data):
    if not is_favorable_market(current_data):
        logger.info("Market conditions unfavorable - no coins selected")
        return []

    profitability = {}
    for symbol, df in current_data.items():
        if len(df) < 14:
            continue
        
        # Volatility check
        price_change = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
        volatility = df['close'].pct_change().std() 

        # Bearish momentum check
        df['ema5'] = ta.ema(df['close'], length=5)
        is_bearish = df['close'].iloc[-1] < df['ema5'].iloc[-1]

        # Sentiment check
        sentiment = fetch_sentiment(symbol)
        sentiment_factor = 1 - (sentiment * 0.5)

        # Score: Volatile, bearish coins with bearish sentiment
        score = abs(price_change) * volatility * sentiment_factor if is_bearish else 0
        profitability[symbol] = score
        logger.debug(f"{symbol}: Price Change = {price_change:.4f}, Volatility = {volatility:.4f}, Bearish = {is_bearish}, Sentiment = {sentiment:.2f}, Score = {score:.4f}")

    ranked_symbols = sorted(profitability.keys(), key=lambda x: profitability[x], reverse=True)
    top_symbols = ranked_symbols[:4] if ranked_symbols else []
    logger.info(f"Top coins selected: {top_symbols}")
    return top_symbols