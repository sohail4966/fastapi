from datetime import date
from pydantic import BaseModel

class SymbolRequest(BaseModel):
    symbols: list[str] 
    start_date : date
    end_date : date
