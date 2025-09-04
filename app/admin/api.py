from datetime import date
from fastapi import APIRouter, Depends
from clickhouse_connect.driver.client import Client
from app.admin import request_body
from .service import AdminService
from app.dependency import get_db_client

router = APIRouter()
admin_service = AdminService()

@router.post("/add_symbols")
async def add_symbols(client: Client = Depends(get_db_client)):
    """
    Fetches trading pairs from Binance and inserts them into the 'trading_pairs' table.
    """
    # 👈 Await the async service function and pass the client to it
    return await admin_service.add_new_symbols(client)


@router.post('/download_historic_data')
async def add_historic_data(request: request_body.SymbolRequest, client: Client = Depends(get_db_client)):
    symbols = request.symbols  
    start_date = request.start_date or '01/01/2020'
    end_date = request.end_date or date.today.strftime("%d/%m/%Y")

    
    return await admin_service.add_data_for_symbol(client, symbols, start_date, end_date)
    
@router.get('/get_close')
async def get_close(symbol : str , client : Client = Depends(get_db_client)):

    return await admin_service.get_close_for_symbol(symbol,client)