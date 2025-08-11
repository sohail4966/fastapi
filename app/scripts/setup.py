
# app/scripts/setup.py
# Setup script to initialize the entire system

import asyncio
import logging
from datetime import datetime, timedelta
from ..database.init_db import DatabaseInitializer
from .data_migration import DataMigration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_system():
    """Setup the entire cryptocurrency data system"""
    logger.info("Starting system setup...")
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'port': 8123,
        'user': 'default',
        'password': '',
        'database': 'crypto_data'
    }
    
    # Initialize database
    db_initializer = DatabaseInitializer(**db_config)
    db_initializer.run_initialization()
    
    # Run data migration for sample symbols
    migration = DataMigration(db_initializer)
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)  # Last 7 days
    
    for symbol in symbols:
        await migration.migrate_historical_data(symbol, start_date, end_date)
    
    logger.info("System setup completed successfully!")

if __name__ == "__main__":
    asyncio.run(setup_system())