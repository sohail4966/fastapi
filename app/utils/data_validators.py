
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates cryptocurrency data for integrity and consistency"""
    
    @staticmethod
    def validate_ohlcv(data: Dict[str, Any]) -> bool:
        """Validate OHLCV data structure and values"""
        required_fields = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
        
        # Check required fields
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Validate price relationships
        if not (data['low_price'] <= data['open_price'] <= data['high_price']):
            logger.error("Invalid price relationship: low <= open <= high")
            return False
        
        if not (data['low_price'] <= data['close_price'] <= data['high_price']):
            logger.error("Invalid price relationship: low <= close <= high")
            return False
        
        # Validate positive values
        for field in required_fields:
            if data[field] < 0:
                logger.error(f"Negative value not allowed for {field}")
                return False
        
        # Validate reasonable price ranges (basic sanity check)
        if data['high_price'] / data['low_price'] > 10:  # 1000% change in single candle
            logger.warning("Extreme price movement detected")
        
        return True
    
    @staticmethod
    def validate_indicator(data: Dict[str, Any]) -> bool:
        """Validate technical indicator data"""
        required_fields = ['indicator_name', 'indicator_value']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return False
        
        # Check for NaN values
        if pd.isna(data['indicator_value']) or np.isinf(data['indicator_value']):
            logger.error("Invalid indicator value: NaN or Infinity")
            return False
        
        return True
    
    @staticmethod
    def validate_batch_data(data_list: List[Dict[str, Any]], data_type: str) -> List[Dict[str, Any]]:
        """Validate and filter a batch of data"""
        valid_data = []
        
        for item in data_list:
            if data_type == 'ohlcv' and DataValidator.validate_ohlcv(item):
                valid_data.append(item)
            elif data_type == 'indicator' and DataValidator.validate_indicator(item):
                valid_data.append(item)
        
        if len(valid_data) != len(data_list):
            logger.warning(f"Filtered {len(data_list) - len(valid_data)} invalid records")
        
        return valid_data
