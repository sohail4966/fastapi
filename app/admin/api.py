from datetime import date
from fastapi import APIRouter, Depends
from clickhouse_connect.driver.client import Client
from app.admin import request_body
from .service import AdminService
from app.dependency import get_db_client

admin_router = APIRouter()
admin_service = AdminService()

@admin_router.post("/add_symbols")
async def add_symbols(client: Client = Depends(get_db_client)):
    """
    Define an asynchronous function that adds symbols using a client obtained from the `get_db_client` dependency.
    @param client - The client obtained from `get_db_client`.
    @return A coroutine that adds new symbols using the `admin_service`.
    """
    return await admin_service.add_new_symbols(client)


@admin_router.post('/download_historic_data')
async def add_historic_data(request: request_body.SymbolRequest, client: Client = Depends(get_db_client)):
    """
    Add historic data for a list of symbols within a specified date range.
    @param request - SymbolRequest object containing symbols, start_date, and end_date
    @param client - Database client to retrieve data
    @return None
    """
    symbols = request.symbols  
    start_date = request.start_date or '01/01/2020'
    end_date = request.end_date or date.today().strftime("%d/%m/%Y")

    
    return await admin_service.add_data_for_symbol(client, symbols, start_date, end_date)
    
@admin_router.get('/get_close')
async def get_close(symbol : str , client : Client = Depends(get_db_client)):
    """
    Retrieve the closing price for a given symbol asynchronously.
    @param symbol - The symbol for which the closing price is needed.
    @param client - The database client to use.
    @return The closing price for the specified symbol.
    """
    return await admin_service.get_close_for_symbol(symbol,client)