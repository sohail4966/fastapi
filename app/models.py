from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Optional

class OHLCVData(BaseModel):
    symbol: str
    timestamp: datetime
    timeframe: str = "1m"
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float

class TechnicalIndicator(BaseModel):
    symbol: str
    timestamp: datetime
    indicator_name: str
    indicator_value: float
    parameters: Dict[str, str] = {}

class CryptoMetadata(BaseModel):
    symbol: str
    name: str
    market_cap: Optional[float] = None
    circulating_supply: Optional[float] = None
    total_supply: Optional[float] = None
    last_updated: datetime


