import asyncio
import logging
from typing import List, Dict, Any
import clickhouse_connect
from datetime import datetime, timedelta
import os
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, host: str, port: int, user: str,password:str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.client = None
        logger.info(f'host:{self.host} \n port:{self.port} \n user:{self.user} \n password:{password} \n database:{self.database}')
    
    def connect(self):
        """Initialize ClickHouse connection to the specific database."""
        # This method now assumes the database already exists.
        if self.client:
            self.client.close()
            
        self.client = clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.database
        )
        logger.info(f"Successfully connected to database '{self.database}'")
    
    def create_database(self):
        """Create the main database"""

        with clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password
        ) as client:
            logger.info(f"Ensuring database '{self.database}' exists...")
            client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            logger.info(f"Database '{self.database}' created or already exists.")
        
        # Switch to the created database
        self.client = clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.database
        )
 
    def run_initialization(self):
        """Run complete database initialization"""
        logger.info("Starting database initialization...")
        logger.info(f"user : {self.user} ,password : {self.password}")
        
        try:
            self.create_database()
            self.connect()
            
            logger.info("Database initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
        finally:
            if self.client:
                self.client.close()
                