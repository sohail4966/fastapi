
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates cryptocurrency data for integrity and consistency"""
    
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
    
