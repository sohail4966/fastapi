from fastapi import Request, HTTPException
from clickhouse_connect.driver.client import Client

def get_db_client(request: Request) -> Client:
    """
    Dependency function to get the ClickHouse database client from app.state.
    """
    db_manager = request.app.state.db_manager
    if db_manager and db_manager.client:
        return db_manager.client
    
    raise HTTPException(
        status_code=503, 
        detail="Database client is not available."
    )