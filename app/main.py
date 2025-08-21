import asyncio
import logging
from typing import Optional,List
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException
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
from app.celery import celery_init

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = celery_init.create_celery_app()

db_manager = None
redis_client = None
ws_manager = None
indicators_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_manager, redis_client, ws_manager, indicators_engine
    logger.info(f'from settings {settings.CLICKHOUSE_USER} , {settings.CLICKHOUSE_PASSWORD}')
    try:
        # Initialize components
        db_manager = DatabaseInitializer(
            host = settings.CLICKHOUSE_HOST,
            port = settings.CLICKHOUSE_PORT,
            user = settings.CLICKHOUSE_USER,
            password = settings.CLICKHOUSE_PASSWORD,
            database = settings.CLICKHOUSE_DATABASE
            
        )
        logger.info(f'user: {db_manager.user} ,password :{db_manager.password}')
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