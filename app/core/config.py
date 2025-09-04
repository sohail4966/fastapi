import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST")
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT"))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE")
    
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    BINANCE_WS_URL = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/stream")
    COINGECKO_API_URL = os.getenv("COINGECKO_API_URL", "https://api.coingecko.com/api/v3")

settings = Settings()
print(f'db from settings : {settings.CLICKHOUSE_DATABASE}')
