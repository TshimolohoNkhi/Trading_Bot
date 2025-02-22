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