
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
Database Migrations

We use a lightweight Python runner with .sql files:
Place files in migrations/ named 0001_init.sql, 0002_add_column.sql, etc.
Each file = one atomic DDL (no multi-statement).
Optional: add 0002_add_column.verify.sql for read-only checks.
First -- comment line is saved as description in the ledger.

Run migrations:
```bash
python run_migrations.py
```

Applied migrations are tracked in migration_ledger.
On error, the runner stops and marks it as aborted.

2. **Start Infrastructure Services**
```bash
docker-compose -f docker-compose.yml up -d clickhouse redis
```


4. **Start Development Server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```



## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request



**Built with ❤️ for the cryptocurrency trading community**