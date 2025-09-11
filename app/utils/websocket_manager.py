
from ..database.init_db import DatabaseInitializer
import asyncio
import json
import logging
from datetime import datetime
import websockets
from app.models import OHLCVData
from ..core.config import settings

class WebSocketManager:
    def __init__(self, clickhouse_manager: DatabaseInitializer, redis_client):
        self.db = clickhouse_manager
        self.redis = redis_client
        self.connections = {}
        self.subscriptions = set()
    
    async def connect_to_binance(self):
        """Connect to Binance WebSocket stream"""
        symbols = ["btcusdt", "ethusdt", "adausdt", "dotusdt", "linkusdt"]
        streams = [f"{symbol}@ticker" for symbol in symbols]
        
        subscribe_message = {
            "method": "SUBSCRIBE",
            "parameters": streams,
            "id": 1
        }
        
        while True:
            try:
                async with websockets.connect(settings.BINANCE_WS_URL) as websocket:
                    await websocket.send(json.dumps(subscribe_message))
                    
                    async for message in websocket:
                        data = json.loads(message)
                        await self.process_binance_message(data)
                        
            except Exception as e:
                logging.error(f"Binance WebSocket error: {e}")
                await asyncio.sleep(5)  # Reconnect after 5 seconds
    
    async def process_binance_message(self, data: dict):
        """Process incoming Binance WebSocket message"""
        if 'stream' in data and 'data' in data:
            ticker_data = data['data']
            
            if ticker_data.get('e') == '24hrTicker':
                ohlcv_data = OHLCVData(
                    symbol=ticker_data['s'],
                    timestamp=datetime.fromtimestamp(ticker_data['E'] / 1000),
                    timeframe="1m",
                    open_price=float(ticker_data['o']),
                    high_price=float(ticker_data['h']),
                    low_price=float(ticker_data['l']),
                    close_price=float(ticker_data['c']),
                    volume=float(ticker_data['v'])
                )
                
                # Store in ClickHouse
                await self.db.insert_ohlcv_batch([ohlcv_data])
                
                # Cache latest price in Redis
                await self.redis.hset(
                    f"latest_price:{ohlcv_data.symbol}",
                    mapping={
                        "price": ohlcv_data.close_price,
                        "timestamp": ohlcv_data.timestamp.isoformat(),
                        "volume": ohlcv_data.volume
                    }
                )
                
                # Broadcast to WebSocket clients
                await self.broadcast_price_update(ohlcv_data)
    
    async def broadcast_price_update(self, ohlcv_data: OHLCVData):
        """Broadcast price updates to connected WebSocket clients"""
        message = {
            "type": "price_update",
            "data": {
                "symbol": ohlcv_data.symbol,
                "price": ohlcv_data.close_price,
                "timestamp": ohlcv_data.timestamp.isoformat(),
                "volume": ohlcv_data.volume
            }
        }
        
        # Store message for broadcasting (in real implementation, use WebSocket manager)
        await self.redis.publish("price_updates", json.dumps(message))
