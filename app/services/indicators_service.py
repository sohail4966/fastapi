import pandas as pd
import pandas_ta as ta
import logging
from datetime import datetime
from typing import List
from app.database.init_db import DatabaseInitializer
from app.models import TechnicalIndicator


class TechnicalIndicatorsEngine:
    def __init__(self, clickhouse_manager: DatabaseInitializer):
        self.db = clickhouse_manager
    
    async def calculate_indicators(self, symbol: str, period_days: int = 30) -> List[TechnicalIndicator]:
        """Calculate technical indicators for a symbol"""
        
        # Fetch historical data
        query = """
        SELECT timestamp, open_price, high_price, low_price, close_price, volume
        FROM crypto_ohlcv
        WHERE symbol = %(symbol)s 
        AND timeframe = '1m'
        AND timestamp >= now() - INTERVAL %(days)s DAY
        ORDER BY timestamp
        """
        
        result = self.db.client.query(query, {'symbol': symbol, 'days': period_days})
        
        if not result.result_rows:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame(result.result_rows, 
                         columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.set_index('timestamp', inplace=True)
        
        indicators = []
        current_time = datetime.now()
        
        # Calculate various indicators
        try:
            # Simple Moving Averages
            for period in [20, 50, 200]:
                sma = ta.sma(df['close'], length=period)
                if not sma.empty and not pd.isna(sma.iloc[-1]):
                    indicators.append(TechnicalIndicator(
                        symbol=symbol,
                        timestamp=current_time,
                        indicator_name=f"SMA_{period}",
                        indicator_value=float(sma.iloc[-1]),
                        parameters={"period": str(period)}
                    ))
            
            # Exponential Moving Averages
            for period in [12, 26, 50]:
                ema = ta.ema(df['close'], length=period)
                if not ema.empty and not pd.isna(ema.iloc[-1]):
                    indicators.append(TechnicalIndicator(
                        symbol=symbol,
                        timestamp=current_time,
                        indicator_name=f"EMA_{period}",
                        indicator_value=float(ema.iloc[-1]),
                        parameters={"period": str(period)}
                    ))
            
            # RSI
            rsi = ta.rsi(df['close'], length=14)
            if not rsi.empty and not pd.isna(rsi.iloc[-1]):
                indicators.append(TechnicalIndicator(
                    symbol=symbol,
                    timestamp=current_time,
                    indicator_name="RSI",
                    indicator_value=float(rsi.iloc[-1]),
                    parameters={"period": "14"}
                ))
            
            # MACD
            macd_data = ta.macd(df['close'])
            if macd_data is not None and not macd_data.empty:
                macd_cols = ['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9']
                for col in macd_cols:
                    if col in macd_data.columns and not pd.isna(macd_data[col].iloc[-1]):
                        indicators.append(TechnicalIndicator(
                            symbol=symbol,
                            timestamp=current_time,
                            indicator_name=col,
                            indicator_value=float(macd_data[col].iloc[-1]),
                            parameters={"fast": "12", "slow": "26", "signal": "9"}
                        ))
            
            # Bollinger Bands
            bbands = ta.bbands(df['close'], length=20, std=2)
            if bbands is not None and not bbands.empty:
                bb_cols = ['BBL_20_2.0', 'BBM_20_2.0', 'BBU_20_2.0']
                for col in bb_cols:
                    if col in bbands.columns and not pd.isna(bbands[col].iloc[-1]):
                        indicators.append(TechnicalIndicator(
                            symbol=symbol,
                            timestamp=current_time,
                            indicator_name=col.replace('_20_2.0', ''),
                            indicator_value=float(bbands[col].iloc[-1]),
                            parameters={"period": "20", "std": "2"}
                        ))
            
        except Exception as e:
            logging.error(f"Error calculating indicators for {symbol}: {e}")
        
        return indicators
