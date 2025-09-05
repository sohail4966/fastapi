import asyncio
import logging
from fastapi import FastAPI, WebSocket, BackgroundTasks, HTTPException,APIRouter
from fastapi.middleware.cors import CORSMiddleware
import redis
import uvicorn
from contextlib import asynccontextmanager
from app.database.init_db import DatabaseInitializer
from app.utils.websocket_manager import WebSocketManager
from app.core.config import settings
from app.celery import celery_init
from app.admin.api import router as admin_router

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
    try:
        # Initialize components
        db_manager = DatabaseInitializer(
            host = settings.CLICKHOUSE_HOST,
            port = settings.CLICKHOUSE_PORT,
            user = settings.CLICKHOUSE_USER,
            password = settings.CLICKHOUSE_PASSWORD,
            database = settings.CLICKHOUSE_DATABASE
            
        )
        app.state.db_manager = db_manager
        redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        ws_manager = WebSocketManager(db_manager, redis_client)
        
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

app.include_router(admin_router, prefix="/api/v1")

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )