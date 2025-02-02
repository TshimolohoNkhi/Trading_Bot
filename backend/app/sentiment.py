import os
import tweepy
import requests
import praw
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
TRADINGVIEW_NEWS_URL = "https://www.tradingview.com/api/news/crypto/"

# Define watchlist (coins to track)
watchlist = ["PYTHUSDT", "POPCATUSDT", "MNTUSDT", "XRPUSDT", "LTCUSDT",
             "SOLUSDT", "LINKUSDT", "ALTUSDT", "MATICUSDT", "JUPUSDT",
             "SHIBUSDT", "FARTCOINUSDT", "TRUMPUSDT", "FETUSDT", "UNIUSDT"]

# Initialize sentiment analyzer
vader = SentimentIntensityAnalyzer()

def get_twitter_sentiment(coin, count=10):
    """Fetches recent tweets related to a specific coin and analyzes sentiment."""
    client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN)
    query = f"#{coin.replace('USDT', '')}"  # Example: "#Bitcoin"
    
    tweets = client.search_recent_tweets(query=query, max_results=count, tweet_fields=["text"])
    sentiments = []

    if tweets.data:
        for tweet in tweets.data:
            sentiment_score = vader.polarity_scores(tweet.text)["compound"]
            sentiment = "bullish" if sentiment_score > 0.2 else "bearish" if sentiment_score < -0.2 else "neutral"
            sentiments.append((tweet.text, sentiment))
    
    return sentiments

def get_reddit_sentiment(coin, subreddit="cryptocurrency", count=10):
    """Fetches Reddit posts related to a specific coin and analyzes sentiment."""
    reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID, client_secret=REDDIT_SECRET, user_agent="crypto_sentiment")
    posts = reddit.subreddit(subreddit).search(coin.replace("USDT", ""), limit=count)  # Search for the coin
    
    sentiments = []
    for post in posts:
        analysis = TextBlob(post.title + " " + post.selftext)
        sentiment_score = analysis.sentiment.polarity
        sentiment = "bullish" if sentiment_score > 0.2 else "bearish" if sentiment_score < -0.2 else "neutral"
        sentiments.append((post.title, sentiment))
    
    return sentiments

def get_tradingview_news_sentiment(coin):
    """Fetches TradingView news related to a specific coin and analyzes sentiment."""
    response = requests.get(f"{TRADINGVIEW_NEWS_URL}?symbol={coin}")
    if response.status_code != 200:
        return []
    
    news_articles = response.json()
    sentiments = []
    for article in news_articles:
        analysis = TextBlob(article["title"] + " " + article.get("content", ""))
        sentiment_score = analysis.sentiment.polarity
        sentiment = "bullish" if sentiment_score > 0.2 else "bearish" if sentiment_score < -0.2 else "neutral"
        sentiments.append((article["title"], sentiment))
    
    return sentiments

def analyze_watchlist():
    """Runs sentiment analysis on all coins in the watchlist."""
    sentiment_data = {}

    for coin in watchlist:
        print(f"\nAnalyzing {coin} sentiment...")
        
        twitter_sentiment = get_twitter_sentiment(coin, count=5)
        reddit_sentiment = get_reddit_sentiment(coin, count=5)
        tradingview_sentiment = get_tradingview_news_sentiment(coin)

        sentiment_data[coin] = {
            "Twitter": twitter_sentiment,
            "Reddit": reddit_sentiment,
            "TradingView": tradingview_sentiment
        }
    
    return sentiment_data

if __name__ == "__main__":
    results = analyze_watchlist()
    
    # Print summarized results
    for coin, sentiment in results.items():
        print(f"\n--- {coin} Sentiment Summary ---")
        print(f"Twitter: {len(sentiment['Twitter'])} mentions")
        print(f"Reddit: {len(sentiment['Reddit'])} mentions")
        print(f"TradingView: {len(sentiment['TradingView'])} mentions")
