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
from app.core.config import settings

load_dotenv() 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global instances
db_manager = None
redis_client = None
ws_manager = None
indicators_engine = None


# Celery configuration
def create_celery_app() -> Celery:
    celery_app = Celery(
        "crypto_app",
        broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
        # Include your task modules
        include=[
            "app.services.celery_tasks",
        ]
    )
    
    # Celery configuration
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_routes={
            "app.services.celery_tasks.*": {"queue": "crypto_queue"},
        },
        # Add beat schedule if you have periodic tasks
        beat_schedule={
            # Example: 'fetch-crypto-data': {
            #     'task': 'app.services.celery_tasks.fetch_crypto_data',
            #     'schedule': 60.0,  # Run every 60 seconds
            # },
        },
    )
    
    return celery_app

# Create Celery instance
celery_app = create_celery_app()

# Global variables for dependency injection
db_manager = None
redis_client = None
ws_manager = None
indicators_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager, redis_client, ws_manager, indicators_engine
    
    try:
        # Initialize components
        db_manager = DatabaseInitializer(
            settings.CLICKHOUSE_HOST,
            settings.CLICKHOUSE_PORT,
            settings.CLICKHOUSE_USER,
            settings.CLICKHOUSE_PASSWORD,
            settings.CLICKHOUSE_DATABASE
            
        )
        
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        ws_manager = WebSocketManager(db_manager, redis_client)
        indicators_engine = TechnicalIndicatorsEngine(db_manager)
        
        # Initialize database schema
        db_manager.run_initialization()
        
        # Start WebSocket connections
        asyncio.create_task(ws_manager.connect_to_binance())
        
        print("✅ Application startup completed successfully")
        
        yield
        
    except Exception as e:
        print(f"❌ Error during startup: {e}")
        raise
    finally:
        # Shutdown cleanup
        print("🔄 Shutting down application...")
        
        if redis_client:
            try:
                await redis_client.close()
                print("✅ Redis connection closed")
            except Exception as e:
                print(f"⚠️ Error closing Redis: {e}")
        
        if ws_manager:
            try:
                # Add any WebSocket cleanup here
                print("✅ WebSocket manager cleaned up")
            except Exception as e:
                print(f"⚠️ Error cleaning up WebSocket manager: {e}")

# Create FastAPI app
app = FastAPI(
    title="Cryptocurrency Data System",
    description="High-performance crypto data system with FastAPI and ClickHouse",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for container health checks"""
    try:
        # Check if critical components are available
        status = {
            "status": "healthy",
            "database": "connected" if db_manager else "disconnected",
            "redis": "connected" if redis_client else "disconnected",
            "websocket": "active" if ws_manager else "inactive"
        }
        return status
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


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