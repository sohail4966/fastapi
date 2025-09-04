import ccxt

# Initialize exchange
exchange = ccxt.binance()   # you can also use ccxt.coinbase(), ccxt.kucoin(), etc.
print(exchange.id)
# Load markets
markets = exchange.load_markets()

# Get list of symbols
symbols = list(markets.keys())

print(f"Total markets: {len(symbols)}")
print(symbols[:20])  # print first 20
