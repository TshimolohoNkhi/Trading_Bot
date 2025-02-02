# Fetches market data

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/tradingview-alert', methods=['POST'])
def tradingview_alert():
    data = request.json
    print("🔔 New Alert Received:", data)
    
    # Process trade logic here
    if data["type"] == "BUY":
        print(f"📈 Entering LONG position on {data['symbol']} at {data['price']}")
    elif data["type"] == "SELL":
        print(f"📉 Entering SHORT position on {data['symbol']} at {data['price']}")

    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

