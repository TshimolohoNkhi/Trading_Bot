# Starts Python backend

# Begin with the Tradingview file, if the sentiment is stable
# Call the Tradingview script to execute the technical analysis
# Once the technical analysis has been excuted, send order to email
# Google sheet script pulls that email with the order and populates the table
# Sends data to Rust 
# Rust connects to Binance
# Rust executes the trade
# Initialises trailing stop losses and take profit
# Once the trade is done, log everything on Notion

# ✅ Run Bot
async def main():
    """Main function to run the bot."""
    # Start WebSocket for real-time price updates
    asyncio.create_task(binance_websocket())

    # Rank symbols based on volatility and liquidity
    ranked_symbols = await rank_symbols(config["symbols"])
    top_symbols = [s['symbol'] for s in ranked_symbols[:3]]
    logger.info(f"Top symbols for trading: {top_symbols}")

    # Apply the strategy to top symbols
    while True:
        await asyncio.gather(*[apply_smc_strategy(symbol) for symbol in top_symbols])
        await asyncio.sleep(60)  # Wait before the next iteration

asyncio.run(main())