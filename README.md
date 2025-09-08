# Cryptocurrency Trading Bot - Smart Money Concepts (SMC) Strategy

A cryptocurrency trading bot that implements Smart Money Concepts (SMC) trading strategy with integrated sentiment analysis and dynamic risk management. The bot focuses on identifying short-selling opportunities in volatile, bearish market conditions across multiple cryptocurrency pairs.

## 💼 Portfolio Project

This is a personal portfolio project demonstrating advanced algorithmic trading concepts and Python development skills. The project showcases:

- **Financial Engineering**: Implementation of trading algorithms and risk management systems
- **Data Science**: Real-time data processing, sentiment analysis, and technical indicator calculations
- **Software Architecture**: Modular design with separation of concerns across multiple components
- **API Integration**: Professional integration with cryptocurrency exchange APIs (Binance/CCXT)
- **Quantitative Analysis**: Statistical modeling for position sizing and risk assessment

## 🚀 Key Features

### Trading Strategy
- **Smart Money Concepts (SMC)**: Implements liquidity sweep detection and bearish momentum analysis
- **Short-Selling Focus**: Specializes in identifying profitable short positions during market downturns
- **Multi-Asset Trading**: Monitors and trades 20 different cryptocurrency pairs simultaneously
- **Dynamic Coin Selection**: Automatically selects top 4 most profitable coins based on real-time analysis

### Risk Management
- **Position Sizing**: Calculates optimal position sizes based on risk percentage (5% per trade)
- **Multi-Level Take Profits**: Implements 3-tier take profit system (1.2x, 2.4x, 3.6x ATR)
- **Trailing Stop Loss**: Dynamic stop-loss adjustment to lock in profits
- **Timeout Protection**: Automatically closes trades after 50 candles (4+ hours on 5m timeframe)

### Market Analysis
- **Sentiment Analysis**: Integrates news, Twitter/X, and Reddit sentiment using TextBlob
- **Technical Indicators**: Uses EMA, ATR, and custom liquidity sweep detection
- **Volatility Assessment**: Evaluates market conditions before entering trades
- **Bearish Momentum Detection**: Identifies optimal entry points using EMA crossovers

### Data & Infrastructure
- **Real-Time Data**: Fetches live OHLCV data from Binance via CCXT library
- **Comprehensive Logging**: Detailed trade logging with timestamps and performance metrics
- **Equity Curve Tracking**: Visual performance monitoring and backtesting capabilities
- **Error Handling**: Robust error management for API failures and data issues

## 📊 Trading Specifications

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Starting Balance** | $28 USDT | Initial trading capital |
| **Risk Per Trade** | 5% ($1.40) | Maximum risk exposure per position |
| **Timeframe** | 5 minutes | Primary analysis and trading timeframe |
| **Trailing Stop** | 2% | Dynamic stop-loss adjustment |
| **Max Spread** | 0.05% | Maximum allowable bid-ask spread |
| **Trading Fee** | 0.075% | Binance trading fee consideration |
| **Slippage** | 0.1% | Expected price slippage on execution |

## 🏗️ Project Structure

```
TradingBot/
├── config/
│   └── config.py          # Trading parameters and symbol configuration
├── data/
│   └── data_fetcher.py     # Binance API integration and data retrieval
├── research/
│   └── coin_researcher.py  # Sentiment analysis and coin selection logic
├── trading/
│   └── trader.py          # Core trading strategy and position management
├── utils/
│   ├── indicators.py      # Technical indicators and liquidity sweep detection
│   ├── logging.py         # Logging configuration and setup
│   └── plotting.py        # Equity curve visualization
├── main.py               # Main execution script
└── backtest.py          # Backtesting framework
```

## 💰 Supported Cryptocurrency Pairs

The bot monitors and trades the following 20 cryptocurrency pairs:
- **Major Coins**: BTC/USDT, ETH/USDT, BNB/USDT
- **Altcoins**: DOGE/USDT, XRP/USDT, ADA/USDT, SOL/USDT, DOT/USDT
- **DeFi Tokens**: LINK/USDT, UNI/USDT, AVAX/USDT
- **Meme Coins**: SHIB/USDT
- **Legacy Coins**: LTC/USDT, BCH/USDT, XLM/USDT
- **Others**: ALGO/USDT, VET/USDT, TRX/USDT, EOS/USDT

## 🎯 Trading Logic Flow

1. **Market Assessment**: Evaluates overall market volatility and bearish sentiment
2. **Coin Research**: Ranks coins based on volatility, momentum, and sentiment scores
3. **Signal Detection**: Identifies liquidity sweeps and bearish momentum patterns
4. **Position Entry**: Calculates optimal position size and executes short positions
5. **Trade Management**: Monitors stop-loss, take-profit levels, and trailing stops
6. **Position Exit**: Closes trades based on profit targets, stop-loss, or timeout

## 📈 Performance Monitoring

The bot provides comprehensive performance tracking through:
- **Real-time Logging**: All trades logged with entry/exit prices and P&L
- **Equity Curve**: Visual representation of account balance over time
- **Trade Statistics**: Win rate, average profit/loss, and drawdown metrics
- **Risk Metrics**: Position sizing validation and risk exposure monitoring

## 🛠️ Technical Implementation

### Technologies Used
- **Python 3.7+**: Core programming language
- **CCXT**: Cryptocurrency exchange integration
- **Pandas & Pandas-TA**: Data manipulation and technical analysis
- **TextBlob**: Natural language processing for sentiment analysis
- **Matplotlib**: Data visualization and equity curve plotting

### Key Algorithms
- **Liquidity Sweep Detection**: Custom algorithm for identifying market manipulation patterns
- **Dynamic Position Sizing**: Risk-based calculation using ATR and account balance
- **Multi-Tier Profit Taking**: Systematic profit realization with trailing stops
- **Sentiment Scoring**: Weighted sentiment analysis from multiple data sources

## 📝 Project Notes

This project demonstrates proficiency in:
- **Quantitative Finance**: Risk management, position sizing, and performance metrics
- **Machine Learning**: Sentiment analysis and pattern recognition
- **Software Engineering**: Clean code architecture, error handling, and logging
- **Financial Markets**: Understanding of cryptocurrency trading mechanics and market microstructure

