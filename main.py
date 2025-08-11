# Cryptocurrency Data System with FastAPI and ClickHouse
# Complete implementation based on the architectural blueprint

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import clickhouse_connect
import redis
from celery import Celery
import websockets
import aiohttp
import pandas_ta as ta
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
from app.database.init_db import DatabaseInitializer
from app.utils.websocket_manager import WebSocketManager
from app.services.indicators_service import TechnicalIndicatorsEngine
from app.services.celery_tasks import calculate_indicators_task
load_dotenv() 

class Settings:
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", 8123))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "crypto_data")
    
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    
    BINANCE_WS_URL = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/stream")
    COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")


settings = Settings()


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Global instances
db_manager = None
redis_client = None
ws_manager = None
indicators_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db_manager, redis_client, ws_manager, indicators_engine
    
    # Initialize connections
    db_manager = DatabaseInitializer()
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    ws_manager = WebSocketManager(db_manager, redis_client)
    indicators_engine = TechnicalIndicatorsEngine(db_manager)
    
    # Initialize database schema
    await db_manager.initialize_schema()
    
    # Start WebSocket connections
    asyncio.create_task(ws_manager.connect_to_binance())
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()

app = FastAPI(
    title="Cryptocurrency Data System",
    description="High-performance crypto data system with FastAPI and ClickHouse",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Cryptocurrency Data System API"}

@app.get("/api/v1/ohlcv/{symbol}")
async def get_ohlcv_data(
    symbol: str,
    timeframe: str = "1m",
    limit: int = 1000,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get OHLCV data for a symbol"""
    
    query = """
    SELECT timestamp, open_price, high_price, low_price, close_price, volume
    FROM crypto_ohlcv
    WHERE symbol = %(symbol)s AND timeframe = %(timeframe)s
    """
    
    params = {"symbol": symbol.upper(), "timeframe": timeframe}
    
    if start_date:
        query += " AND timestamp >= %(start_date)s"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND timestamp <= %(end_date)s"
        params["end_date"] = end_date
    
    query += " ORDER BY timestamp DESC LIMIT %(limit)s"
    params["limit"] = limit
    
    try:
        result = db_manager.client.query(query, params)
        
        data = [
            {
                "timestamp": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5]
            }
            for row in result.result_rows
        ]
        
        return {"symbol": symbol, "timeframe": timeframe, "data": data}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/indicators/{symbol}")
async def get_technical_indicators(symbol: str, indicator_name: Optional[str] = None):
    """Get technical indicators for a symbol"""
    
    query = """
    SELECT timestamp, indicator_name, indicator_value, parameters
    FROM technical_indicators
    WHERE symbol = %(symbol)s
    """
    
    params = {"symbol": symbol.upper()}
    
    if indicator_name:
        query += " AND indicator_name = %(indicator_name)s"
        params["indicator_name"] = indicator_name
    
    query += " ORDER BY timestamp DESC LIMIT 100"
    
    try:
        result = db_manager.client.query(query, params)
        
        indicators = [
            {
                "timestamp": row[0],
                "indicator_name": row[1],
                "value": row[2],
                "parameters": row[3]
            }
            for row in result.result_rows
        ]
        
        return {"symbol": symbol, "indicators": indicators}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/calculate-indicators/{symbol}")
async def trigger_indicator_calculation(symbol: str, background_tasks: BackgroundTasks):
    """Trigger technical indicator calculation for a symbol"""
    
    background_tasks.add_task(calculate_indicators_task, symbol.upper())
    
    return {"message": f"Indicator calculation triggered for {symbol}"}

@app.get("/api/v1/latest-prices")
async def get_latest_prices():
    """Get latest prices for all symbols"""
    
    query = """
    SELECT symbol, latest_price, timestamp, volume
    FROM symbol_latest_prices
    ORDER BY timestamp DESC
    """
    
    try:
        result = db_manager.client.query(query)
        
        prices = [
            {
                "symbol": row[0],
                "price": row[1],
                "timestamp": row[2],
                "volume": row[3]
            }
            for row in result.result_rows
        ]
        
        return {"prices": prices}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# WEBSOCKET ENDPOINTS
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

connection_manager = ConnectionManager()

@app.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates"""
    await connection_manager.connect(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    
    finally:
        connection_manager.disconnect(websocket)

# ============================================================================
# MAIN APPLICATION RUNNER
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )