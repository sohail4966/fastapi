import asyncio
import logging
from typing import List, Dict, Any
import clickhouse_connect
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DatabaseInitializer:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.client = None
    
    def connect(self):
        """Initialize ClickHouse connection"""
        self.client = clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password
        )
    
    def create_database(self):
        """Create the main database"""
        create_db_sql = f"CREATE DATABASE IF NOT EXISTS {self.database}"
        self.client.command(create_db_sql)
        logger.info(f"Database {self.database} created or already exists")
        
        # Switch to the created database
        self.client = clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.database
        )
    
    def create_tables(self):
        """Create all required tables"""
        
        # Main OHLCV table with optimized structure
        ohlcv_table_sql = """
        CREATE TABLE IF NOT EXISTS crypto_ohlcv (
            symbol LowCardinality(String),
            timestamp DateTime64(3, 'UTC'),
            timeframe LowCardinality(String),
            open_price Float64,
            high_price Float64,
            low_price Float64,
            close_price Float64,
            volume Float64,
            quote_volume Float64 DEFAULT 0,
            trade_count UInt64 DEFAULT 0,
            taker_buy_base_volume Float64 DEFAULT 0,
            taker_buy_quote_volume Float64 DEFAULT 0
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timeframe, timestamp)
        SETTINGS index_granularity = 8192,
                 ttl_only_drop_parts = 1
        TTL timestamp + INTERVAL 5 YEAR
        """
        
        # Technical indicators table
        indicators_table_sql = """
        CREATE TABLE IF NOT EXISTS technical_indicators (
            symbol LowCardinality(String),
            timestamp DateTime64(3, 'UTC'),
            timeframe LowCardinality(String),
            indicator_name LowCardinality(String),
            indicator_value Float64,
            parameters Map(String, String),
            calculation_timestamp DateTime64(3, 'UTC') DEFAULT now64()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (symbol, timeframe, indicator_name, timestamp)
        SETTINGS index_granularity = 8192
        TTL timestamp + INTERVAL 2 YEAR
        """
        
        # Crypto metadata table
        metadata_table_sql = """
        CREATE TABLE IF NOT EXISTS crypto_metadata (
            symbol LowCardinality(String),
            name String,
            full_name String,
            market_cap Nullable(Float64),
            market_cap_rank Nullable(UInt32),
            circulating_supply Nullable(Float64),
            total_supply Nullable(Float64),
            max_supply Nullable(Float64),
            price_change_24h Nullable(Float64),
            price_change_percentage_24h Nullable(Float64),
            market_cap_change_24h Nullable(Float64),
            market_cap_change_percentage_24h Nullable(Float64),
            last_updated DateTime64(3, 'UTC'),
            created_at DateTime64(3, 'UTC') DEFAULT now64()
        ) ENGINE = ReplacingMergeTree(last_updated)
        ORDER BY symbol
        """
        
        # Order book data table
        orderbook_table_sql = """
        CREATE TABLE IF NOT EXISTS order_book (
            symbol LowCardinality(String),
            timestamp DateTime64(3, 'UTC'),
            side Enum8('bid' = 1, 'ask' = 2),
            price Float64,
            quantity Float64,
            level UInt8
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMMDD(timestamp)
        ORDER BY (symbol, timestamp, side, level)
        SETTINGS index_granularity = 8192
        TTL timestamp + INTERVAL 7 DAY
        """
        
        # Trade data table
        trades_table_sql = """
        CREATE TABLE IF NOT EXISTS trades (
            symbol LowCardinality(String),
            timestamp DateTime64(3, 'UTC'),
            trade_id UInt64,
            price Float64,
            quantity Float64,
            quote_quantity Float64,
            is_buyer_maker Bool,
            trade_time DateTime64(3, 'UTC')
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMMDD(timestamp)
        ORDER BY (symbol, timestamp, trade_id)
        SETTINGS index_granularity = 8192
        TTL timestamp + INTERVAL 30 DAY
        """
        
        tables = [
            ohlcv_table_sql,
            indicators_table_sql, 
            metadata_table_sql,
            orderbook_table_sql,
            trades_table_sql
        ]
        
        for table_sql in tables:
            self.client.command(table_sql)
            logger.info("Created table successfully")
    
    def create_materialized_views(self):
        """Create materialized views for performance optimization"""
        
        # Hourly OHLCV aggregation
        hourly_view_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_hourly_mv
        ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(hour_timestamp)
        ORDER BY (symbol, hour_timestamp)
        POPULATE
        AS SELECT
            symbol,
            toStartOfHour(timestamp) as hour_timestamp,
            argMinState(open_price, timestamp) as open_price,
            maxState(high_price) as high_price,
            minState(low_price) as low_price,
            argMaxState(close_price, timestamp) as close_price,
            sumState(volume) as volume,
            sumState(quote_volume) as quote_volume,
            sumState(trade_count) as trade_count
        FROM crypto_ohlcv
        WHERE timeframe = '1m'
        GROUP BY symbol, toStartOfHour(timestamp)
        """
        
        # Daily OHLCV aggregation
        daily_view_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS ohlcv_daily_mv
        ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMM(day_timestamp)
        ORDER BY (symbol, day_timestamp)
        POPULATE
        AS SELECT
            symbol,
            toStartOfDay(timestamp) as day_timestamp,
            argMinState(open_price, timestamp) as open_price,
            maxState(high_price) as high_price,
            minState(low_price) as low_price,
            argMaxState(close_price, timestamp) as close_price,
            sumState(volume) as volume,
            sumState(quote_volume) as quote_volume,
            sumState(trade_count) as trade_count
        FROM crypto_ohlcv
        WHERE timeframe = '1m'
        GROUP BY symbol, toStartOfDay(timestamp)
        """
        
        # Latest prices view
        latest_prices_view_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS latest_prices_mv
        ENGINE = ReplacingMergeTree(timestamp)
        ORDER BY symbol
        AS SELECT
            symbol,
            timestamp,
            close_price as price,
            volume,
            price_change_24h,
            price_change_percentage_24h
        FROM (
            SELECT 
                symbol,
                timestamp,
                close_price,
                volume,
                close_price - lagInFrame(close_price, 1) 
                    OVER (PARTITION BY symbol ORDER BY timestamp 
                          ROWS BETWEEN 1440 PRECEDING AND 1440 PRECEDING) as price_change_24h,
                (close_price - lagInFrame(close_price, 1) 
                    OVER (PARTITION BY symbol ORDER BY timestamp 
                          ROWS BETWEEN 1440 PRECEDING AND 1440 PRECEDING)) / 
                lagInFrame(close_price, 1) 
                    OVER (PARTITION BY symbol ORDER BY timestamp 
                          ROWS BETWEEN 1440 PRECEDING AND 1440 PRECEDING) * 100 as price_change_percentage_24h
            FROM crypto_ohlcv
            WHERE timeframe = '1m'
        )
        """
        
        # Volume analysis view
        volume_analysis_view_sql = """
        CREATE MATERIALIZED VIEW IF NOT EXISTS volume_analysis_mv
        ENGINE = AggregatingMergeTree()
        PARTITION BY toYYYYMMDD(timestamp)
        ORDER BY (symbol, timestamp)
        AS SELECT
            symbol,
            toStartOfHour(timestamp) as timestamp,
            sumState(volume) as total_volume,
            avgState(volume) as avg_volume,
            maxState(volume) as max_volume,
            minState(volume) as min_volume,
            countState(*) as candle_count
        FROM crypto_ohlcv
        WHERE timeframe = '1m'
        GROUP BY symbol, toStartOfHour(timestamp)
        """
        
        views = [
            hourly_view_sql,
            daily_view_sql,
            latest_prices_view_sql,
            volume_analysis_view_sql
        ]
        
        for view_sql in views:
            try:
                self.client.command(view_sql)
                logger.info("Created materialized view successfully")
            except Exception as e:
                logger.error(f"Error creating materialized view: {e}")
    
    def create_indexes(self):
        """Create additional indexes for performance"""
        
        indexes = [
            # Skip indexes for better filtering performance
            "ALTER TABLE crypto_ohlcv ADD INDEX IF NOT EXISTS symbol_idx symbol TYPE bloom_filter GRANULARITY 1",
            "ALTER TABLE crypto_ohlcv ADD INDEX IF NOT EXISTS timeframe_idx timeframe TYPE bloom_filter GRANULARITY 1",
            "ALTER TABLE technical_indicators ADD INDEX IF NOT EXISTS indicator_idx indicator_name TYPE bloom_filter GRANULARITY 1",
        ]
        
        for index_sql in indexes:
            try:
                self.client.command(index_sql)
                logger.info("Created index successfully")
            except Exception as e:
                logger.warning(f"Index creation warning (may already exist): {e}")

    
    def run_initialization(self):
        """Run complete database initialization"""
        logger.info("Starting database initialization...")
        
        try:
            self.connect()
            self.create_database()
            self.create_tables()
            self.create_materialized_views()
            self.create_indexes()
            
            logger.info("Database initialization completed successfully!")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
        finally:
            if self.client:
                self.client.close()
                