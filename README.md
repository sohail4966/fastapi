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


### Local Development

1. **Setup Python Environment**
```bash
python3 -m venv crypto_env
source crypto_env/bin/activate
pip install -r requirements.txt
```

2. **Start Infrastructure Services**
```bash
docker-compose -f docker-compose.yml up -d clickhouse redis
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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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