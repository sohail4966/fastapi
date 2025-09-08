from datetime import date, datetime, timezone
import ccxt.async_support as ccxt
from fastapi import HTTPException
from clickhouse_connect.driver.client import Client
import uuid


import pandas as pd

class AdminService():

    async def add_new_symbols(self,client: Client):
        """
        Asynchronously fetch symbols from Binance using a provided client, compare them against existing symbols in the database, and insert only the new trading pairs.
        @param client - The client used to interact with Binance.
        @return A message indicating the success or failure of the operation.
        """
        # 1. Fetch all existing symbol_api values from the database first.
        # This prevents re-inserting duplicates and makes the operation idempotent.
        try:
            existing_symbols_data = client.query('SELECT symbol_api FROM trading_pairs').result_rows
            existing_symbols = {row[0] for row in existing_symbols_data}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to query existing symbols from ClickHouse: {e}")

        exchange = ccxt.binance()
        try:
            markets = await exchange.load_markets()
        except Exception as e:
            await exchange.close()
            raise HTTPException(status_code=500, detail=f"Failed to load markets from exchange: {e}")

        try:
            data_to_insert = []
            for symbol, market in markets.items():
                # 2. Skip symbols that are inactive, not spot, or already in our database.
                if (not market.get('active', False) or
                        market.get('type') != 'spot' or
                        market['id'] in existing_symbols):
                    continue

                # --- ID GENERATION ---
                unique_key = f"Binance:{market['id']}"
                pair_id = uuid.uuid5(uuid.NAMESPACE_DNS, unique_key).int >> 64
                
                data_to_insert.append([
                    pair_id,
                    market['base'],
                    market['base'],
                    market['quote'],
                    market['quote'],
                    'Binance',
                    market['symbol'],
                    market['id'],
                    1,
                ])
            # 3. If there's nothing new to add, report that and exit.
            if not data_to_insert:
                return {"message": "Database is already up-to-date. No new trading pairs to insert."}
                
            try:
                # 4. Insert only the new symbols found.
                column_names = [
                    'id', 'base_symbol', 'base_name', 'quote_symbol', 'quote_name',
                    'exchange', 'symbol_display', 'symbol_api', 'active'
                ]
                client.insert('trading_pairs', data_to_insert, column_names=column_names)
                return {"message": f"{len(data_to_insert)} new trading pairs inserted successfully."}
            except Exception as e:
                # Provide more context in the error message if possible
                raise HTTPException(status_code=500, detail=f"Failed to insert data into ClickHouse: {e}")

        finally:
            # Ensure the exchange session is always closed
            print('closing websocket')
            await exchange.close()


    async def add_data_for_symbol(self, client : Client, symbols : list[str], start_date: date, end_date : date):
        """
        Add data for a given symbol within a specified date range.
        @param client - The client object for the database connection.
        @param symbols - List of symbols for which data needs to be added.
        @param start_date - The start date for the data retrieval.
        @param end_date - The end date for the data retrieval.
        @return A dictionary containing the status of the operation and the symbols processed.
        """
        if not symbols:
                raise HTTPException(status_code=400 ,detail='please provide atleast one symbol')
        failed = {'symbol' : []}
        for symbol in symbols:
            if await self.validate_symbol(client, symbol):
                is_success = await self.fetch_and_store_ohlcv(symbol ,start_date , end_date, client)
                if not is_success:
                    failed['symbol'].append(symbol)
            else:
                failed['symbol'].append(symbol)
        return {"status": "success", "symbols": symbols}


    async def validate_symbol(self, client:Client, symbol:str):
        """
        Validate if a symbol is available in the trading_pairs table.
        @param self - the class instance
        @param client - the client used to query the database
        @param symbol - the symbol to validate
        @return True if the symbol is available, False otherwise
        """
        """check if all pairs are avialable in traing_pairs table"""
        symbol_str = f"'{symbol}'"
        query = f"SELECT COUNT(*) FROM trading_pairs WHERE symbol_display IN {symbol_str};"

        result = client.query(query=query)
        count = result.result_rows[0][0]
        return True if count == 1 else False
    

    async def fetch_and_store_ohlcv(self, symbol: str, start_date: str, end_date: str, client: Client, timeframe : str = '1m'):
        """
        Fetch OHLCV data from Binance (via ccxt) and insert into ClickHouse crypto_ohlcv table.
        
        Args:
            symbol (str): Trading pair (e.g., "BTC/USDT")
            timeframe (str): e.g., "1h", "1d", "5m"
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            client (clickhouse_connect.Client): ClickHouse client connection
        """

        query = f"SELECT timestamp FROM crypto_ohlcv WHERE symbol = '{symbol}' ORDER BY timestamp DESC LIMIT 1"
        recent_timestamp_present  = client.query(query)
        # Initialize ccxt Binance
        binance = ccxt.binance()

        since = int(pd.to_datetime(start_date).timestamp() * 1000)
        end_time = int(pd.to_datetime(end_date).timestamp() * 1000)
        if recent_timestamp_present.result_rows :
            print(recent_timestamp_present.result_rows)
            since = int(pd.to_datetime(recent_timestamp_present.result_rows[0][0]).timestamp() * 1000)
            print(f'found recent data exist with timestamp {since}')
        
        try: 
            while since < end_time:
                i=0
                all_data = []
                while i<20:
                    try:
                        ohlcv = await binance.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=720)
                        if not ohlcv:
                            break

                        for row in ohlcv:
                            ts = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc)
                            all_data.append((
                                symbol,
                                ts,
                                timeframe,
                                row[1],  # open
                                row[2],  # high
                                row[3],  # low
                                row[4],  # close
                                row[5],  # volume
                            ))
                        i+=1
                        since = ohlcv[-1][0] + binance.parse_timeframe(timeframe) * 1000

                    except Exception as e:
                        print(f"Error fetching {symbol} OHLCV: {e}")
                        break

                if not all_data:
                    print("No data fetched.")
                    return

                # Insert into ClickHouse
                client.insert(
                    "crypto_ohlcv",
                    all_data,
                    column_names=[
                        "symbol",
                        "timestamp",
                        "timeframe",
                        "open_price",
                        "high_price",
                        "low_price",
                        "close_price",
                        "volume"
                    ]
                )
                print(f"Inserted {len(all_data)} rows into crypto_ohlcv for {symbol} with timeframe ({timeframe}) till {since}")
            return True
        except Exception as e: 
            print(f'failed to download ohlcv data for symbol {symbol},{e}')
            return False
        finally:
            await binance.close()

    async def get_close_for_symbol(self , symbol:str,client:Client):
        """
        Retrieve close prices for a specific symbol from a database table containing cryptocurrency OHLCV data.
        @param symbol - The symbol for which close prices are to be retrieved.
        @param client - The client object for database connection.
        @return A dictionary containing close prices for the specified symbol.
        """
        query = f"select close_price from crypto_ohlcv where symbol='{symbol}' order by timestamp"
        if await self.validate_symbol(client=client , symbol=symbol):
            query_result = client.query(query)
            close_prices = [row[0] for row in query_result.result_rows]
            return {"close_price" : close_prices }
