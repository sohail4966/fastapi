from app.main import app,db_manager
from typing import Optional
from fastapi import HTTPException

@app.get("/api/v1/user/ohlcv/{symbol}")
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
