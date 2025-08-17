# Cryptocurrency Data System with FastAPI and ClickHouse

A comprehensive, high-performance cryptocurrency data system capable of storing 5 years of historical data with 1-minute granularity, real-time data ingestion, and dynamic technical indicator calculations.

## 🏗️ Architecture Overview

The system follows a modern microservices architecture with clearly separated concerns:

- **Data Sources Layer**: Connects to major cryptocurrency exchanges (Binance, CoinGecko, CoinMarketCap)
- **Ingestion Layer**: FastAPI-based real-time and batch data processing
- **Storage Layer**: ClickHouse time-series database with optimized schemas
- **API Layer**: REST endpoints and WebSocket connections for real-time data delivery
- **Background Processing**: Celery workers for technical indicator calculations

## 🚀 Key Features

- **Real-time Data Ingestion**: WebSocket connections to multiple exchanges
- **High Performance**: ClickHouse database optimized for time-series data
- **Technical Indicators**: 130+ indicators including SMA, EMA, RSI, MACD, Bollinger Bands
- **Scalable Architecture**: Horizontal scaling with Docker containers
- **Comprehensive Monitoring**: Prometheus + Grafana dashboard integration
- **Production Ready**: Complete DevOps setup with backup/restore utilities

## 📋 Prerequisites

- Docker (>= 20.10)
- Docker Compose (>= 2.0)
- Python 3.11+ (for development)
- 8GB+ RAM recommended
- 100GB+ storage for historical data

## 🛠️ Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd cryptocurrency-data-system

# Copy environment configuration
cp .env.example .env

# Update .env with your API keys and configuration
nano .env
```

### 2. Deploy with Docker

```bash
# Make scripts executable
chmod +x deploy.sh

# Run full deployment
./scripts/deploy.sh
```

### 3. Verify Installation

The deployment script will automatically:
- Build and start all services
- Initialize ClickHouse database schema
- Create materialized views
- Run health checks

Access the services:
- **FastAPI Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Flower (Celery Monitor)**: http://localhost:5555
- **Prometheus**: http://localhost:9090

## 📊 Database Schema

### Core Tables

#### `crypto_ohlcv`
Primary market data table with 1-minute granularity:
```sql
CREATE TABLE crypto_ohlcv (
    symbol LowCardinality(String),
    timestamp DateTime64(3, 'UTC'),
    timeframe LowCardinality(String),
    open_price Float64,
    high_price Float64,
    low_price Float64,
    close_price Float64,
    volume Float64,
    quote_volume Float64,
    trade_count UInt64,
    taker_buy_base_volume Float64,
    taker_buy_quote_volume Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (symbol, timeframe, timestamp)
TTL timestamp + INTERVAL 5 YEAR
```

#### `technical_indicators`
Technical indicator calculations:
```sql
CREATE TABLE technical_indicators (
    symbol LowCardinality(String),
    timestamp DateTime64(3, 'UTC'),
    timeframe LowCardinality(String),
    indicator_name LowCardinality(String),
    indicator_value Float64,
    parameters Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (symbol, timeframe, indicator_name, timestamp)
```

#### `crypto_metadata`
Cryptocurrency reference data:
```sql
CREATE TABLE crypto_metadata (
    symbol LowCardinality(String),
    name String,
    market_cap Nullable(Float64),
    circulating_supply Nullable(Float64),
    total_supply Nullable(Float64),
    last_updated DateTime64(3, 'UTC')
) ENGINE = ReplacingMergeTree(last_updated)
ORDER BY symbol
```

### Materialized Views

- **`ohlcv_hourly_mv`**: Pre-computed hourly aggregations
- **`ohlcv_daily_mv`**: Pre-computed daily aggregations  
- **`latest_prices_mv`**: Real-time latest prices with 24h changes
- **`volume_analysis_mv`**: Volume analysis and statistics

## 🔌 API Endpoints

### Market Data

#### Get OHLCV Data
```http
GET /api/v1/ohlcv/{symbol}?timeframe=1m&limit=1000&start_date=2024-01-01&end_date=2024-01-02
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1m",
  "data": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "open": 50000.0,
      "high": 50100.0,
      "low": 49900.0,
      "close": 50050.0,
      "volume": 100.5
    }
  ]
}
```

#### Get Latest Prices
```http
GET /api/v1/latest-prices
```

**Response:**
```json
{
  "prices": [
    {
      "symbol": "BTCUSDT",
      "price": 50000.0,
      "timestamp": "2024-01-01T00:00:00Z",
      "volume": 1000000.0
    }
  ]
}
```

### Technical Indicators

#### Get Technical Indicators
```http
GET /api/v1/indicators/{symbol}?indicator_name=RSI
```

#### Calculate Indicators
```http
POST /api/v1/calculate-indicators/{symbol}
```

### WebSocket

#### Real-time Price Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/prices');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Price update:', data);
};
```

## 🔧 Configuration

### Environment Variables

Create `.env` file with the following configuration:

```env
# Database Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=crypto_user
CLICKHOUSE_PASSWORD=crypto_password
CLICKHOUSE_DATABASE=crypto_data

# Redis Configuration
REDIS_URL=redis://localhost:6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# API Keys
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
COINGECKO_API_KEY=your_coingecko_api_key
COINMARKETCAP_API_KEY=your_coinmarketcap_api_key

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Monitoring
PROMETHEUS_METRICS_ENABLED=true
LOG_LEVEL=INFO
```

## 🚀 Development Setup

### Local Development

1. **Setup Python Environment**
```bash
python3 -m venv crypto_env
source crypto_env/bin/activate
pip install -r requirements.txt
```

2. **Start Infrastructure Services**
```bash
docker-compose -f docker-compose.dev.yml up -d clickhouse redis
```

3. **Initialize Database**
```bash
python -c "
from app.database.init_db import DatabaseInitializer
db = DatabaseInitializer('localhost', 8123, 'default', '', 'crypto_data')
db.run_initialization()
"
```

4. **Start Development Server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. **Start Celery Worker**
```bash
celery -A main.celery_app worker --loglevel=info
```

### Adding New Indicators

1. **Create Indicator Function**
```python
# In app/indicators/custom_indicators.py
import pandas as pd
import pandas_ta as ta

def custom_rsi_divergence(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Custom RSI divergence indicator"""
    rsi = ta.rsi(df['close'], length=period)
    # Your custom logic here
    return rsi
```

2. **Register in Engine**
```python
# In app/indicators/engine.py
from .custom_indicators import custom_rsi_divergence

class TechnicalIndicatorsEngine:
    def calculate_custom_indicators(self, df: pd.DataFrame):
        indicators = {}
        indicators['custom_rsi_div'] = custom_rsi_divergence(df)
        return indicators
```

## 📈 Performance Optimization

### ClickHouse Optimizations

1. **Partitioning Strategy**
   - Monthly partitioning for main tables
   - Daily partitioning for high-frequency data

2. **Materialized Views**
   - Pre-computed aggregations reduce query time by 10-100x
   - Automatic incremental updates

3. **Compression**
   - ZSTD compression reduces storage by 60-80%
   - LZ4 for faster access patterns

4. **Query Optimization**
```sql
-- Efficient price range query
SELECT * FROM crypto_ohlcv 
WHERE symbol = 'BTCUSDT' 
AND timestamp >= '2024-01-01' 
AND timestamp < '2024-01-02'
ORDER BY timestamp
LIMIT 1000
```

### Scaling Guidelines

#### Horizontal Scaling

1. **ClickHouse Cluster**
```xml
<clickhouse>
    <remote_servers>
        <crypto_cluster>
            <shard>
                <replica>
                    <host>clickhouse-1</host>
                    <port>9000</port>
                </replica>
                <replica>
                    <host>clickhouse-2</host>
                    <port>9000</port>
                </replica>
            </shard>
        </crypto_cluster>
    </remote_servers>
</clickhouse>
```

2. **FastAPI Load Balancing**
```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  api:
    build: .
    deploy:
      replicas: 3
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - api
```

3. **Redis Cluster**
```yaml
redis-cluster:
  image: redis:7-alpine
  deploy:
    replicas: 6
  command: redis-server --cluster-enabled yes
```

## 🔍 Monitoring and Observability

### Prometheus Metrics

The system exposes metrics at `/metrics`:

- **Application Metrics**
  - Request duration and count
  - Database query performance
  - Background task execution time
  - WebSocket connection count

- **Business Metrics**
  - Data ingestion rate
  - Indicator calculation time
  - Market data freshness
  - Error rates per exchange

### Grafana Dashboards

Pre-configured dashboards for:

1. **System Overview**
   - Resource utilization
   - Service health status
   - Response times

2. **Data Pipeline**
   - Ingestion rates
   - Processing delays
   - Error tracking

3. **Market Data**
   - Price movements
   - Volume analysis
   - Technical indicators

### Alerting Rules

```yaml
# prometheus/alerts.yml
groups:
  - name: crypto-system
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: DataIngestionStalled
        expr: increase(data_ingestion_total[10m]) == 0
        for: 10m
        annotations:
          summary: "Data ingestion has stalled"
```

## 🛡️ Security

### API Security

1. **JWT Authentication**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.get("/api/v1/protected")
async def protected_route(token: str = Depends(security)):
    # Validate JWT token
    pass
```

2. **Rate Limiting**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/data")
@limiter.limit("100/minute")
async def get_data(request: Request):
    pass
```

3. **Input Validation**
```python
from pydantic import BaseModel, validator

class OHLCVRequest(BaseModel):
    symbol: str
    limit: int = 1000
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalnum():
            raise ValueError('Invalid symbol format')
        return v.upper()
```

### Infrastructure Security

1. **Network Security**
   - Docker network isolation
   - Firewall rules for production
   - SSL/TLS encryption

2. **Data Security**
   - Encrypted environment variables
   - Secure API key management
   - Audit logging

## 🗄️ Backup and Recovery

### Automated Backups

```bash
# Schedule daily backups
crontab -e
0 2 * * * /path/to/scripts/backup.sh
```

### Manual Backup

```bash
# Create backup
./scripts/backup.sh

# List backups
ls -la ./backups/

# Restore from backup
./scripts/restore.sh crypto_backup_20241201_020000
```

### Disaster Recovery

1. **Database Replication**
   - ClickHouse replica setup
   - Redis persistence configuration

2. **Data Center Failover**
   - Multi-region deployment
   - DNS failover configuration

## 🚨 Troubleshooting

### Common Issues

#### ClickHouse Connection Issues
```bash
# Check ClickHouse logs
docker-compose logs clickhouse

# Test connection
docker-compose exec clickhouse clickhouse-client --query "SELECT version()"
```

#### Memory Issues
```bash
# Check memory usage
docker stats

# Increase ClickHouse memory limits
# Edit docker-compose.yml:
clickhouse:
  deploy:
    resources:
      limits:
        memory: 8G
```

#### Data Ingestion Problems
```bash
# Check Celery worker logs
docker-compose logs celery_worker

# Monitor Redis queues
docker-compose exec redis redis-cli monitor
```

### Performance Issues

#### Slow Queries
```sql
-- Check query log
SELECT * FROM system.query_log 
WHERE type = 'QueryFinish' 
ORDER BY query_duration_ms DESC 
LIMIT 10;

-- Analyze table statistics
SELECT * FROM system.parts 
WHERE table = 'crypto_ohlcv' 
AND active = 1;
```

#### High CPU Usage
```bash
# Check system resources
./scripts/monitor.sh status

# Scale services
docker-compose up -d --scale api=3 --scale celery_worker=5
```

## 📚 Additional Resources

- [ClickHouse Documentation](https://clickhouse.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Pandas-TA Documentation](https://github.com/twopirllc/pandas-ta)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

### Development Guidelines

- Follow PEP 8 coding standards
- Add comprehensive docstrings
- Write unit and integration tests
- Update documentation for API changes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

- Create an issue on GitHub
- Check existing documentation
- Review troubleshooting section

---

**Built with ❤️ for the cryptocurrency trading community**