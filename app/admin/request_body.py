from datetime import date
from pydantic import BaseModel

class SymbolRequest(BaseModel):
    """
    Define a class for symbol requests that includes the symbols list, start date, and end date.
    @param symbols: list[str] - A list of symbols for which data is requested.
    @param start_date: date - The start date for the data request.
    @param end_date: date - The end date for the data request.
    """
    symbols: list[str] 
    start_date : date
    end_date : date
