#!/bin/bash
# deploy.sh - Production deployment script

set -e  # Exit on any error

echo "🚀 Starting Cryptocurrency Data System Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please update .env file with your configuration before running again."
        exit 1
    fi
    
    print_status "Prerequisites check completed ✅"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=(
        "data/clickhouse"
        "data/redis" 
        "data/prometheus"
        "data/grafana"
        "logs"
        "ssl"
        "monitoring/grafana/dashboards"
        "monitoring/grafana/provisioning"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        print_status "Created directory: $dir"
    done
}

# Set up SSL certificates (self-signed for development)
setup_ssl() {
    print_status "Setting up SSL certificates..."
    
    if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
        print_status "Generating self-signed SSL certificates..."
        
        openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem \
            -days 365 -nodes -subj "/CN=localhost"
        
        print_status "SSL certificates generated ✅"
    else
        print_status "SSL certificates already exist ✅"
    fi
}

# Build and start services
deploy_services() {
    print_status "Building and starting services..."
    
    # Pull latest images
    docker-compose -f "$DOCKER_COMPOSE_FILE" pull
    
    # Build services
    docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache
    
    # Start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    print_status "Services started ✅"
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for ClickHouse
    print_status "Waiting for ClickHouse..."
    until docker-compose exec clickhouse clickhouse-client --query "SELECT 1" &>/dev/null; do
        sleep 2
        echo -n "."
    done
    echo ""
    print_status "ClickHouse is ready ✅"
    
    # Wait for Redis
    print_status "Waiting for Redis..."
    until docker-compose exec redis redis-cli ping | grep PONG &>/dev/null; do
        sleep 2
        echo -n "."
    done
    echo ""
    print_status "Redis is ready ✅"
    
    # Wait for API
    print_status "Waiting for FastAPI..."
    until curl -f http://localhost:8000/health &>/dev/null; do
        sleep 2
        echo -n "."
    done
    echo ""
    print_status "FastAPI is ready ✅"
}

# Initialize database
initialize_database() {
    print_status "Initializing database schema..."
    
    docker-compose exec api python -c "
from app.database.init_db import DatabaseInitializer
import os

db_config = {
    'host': os.getenv('CLICKHOUSE_HOST', 'clickhouse'),
    'port': int(os.getenv('CLICKHOUSE_PORT', 8123)),
    'user': os.getenv('CLICKHOUSE_USER', 'default'),
    'password': os.getenv('CLICKHOUSE_PASSWORD', ''),
    'database': os.getenv('CLICKHOUSE_DATABASE', 'crypto_data')
}

db_initializer = DatabaseInitializer(**db_config)
db_initializer.run_initialization()
print('Database initialized successfully!')
"
    
    print_status "Database initialization completed ✅"
}

# Health check
health_check() {
    print_status "Performing health check..."
    
    # Check API health
    api_health=$(curl -s http://localhost:8000/health || echo "failed")
    if [[ "$api_health" == *"ok"* ]]; then
        print_status "API health check passed ✅"
    else
        print_error "API health check failed ❌"
        return 1
    fi
    
    # Check service status
    services=$(docker-compose ps --services)
    for service in $services; do
        status=$(docker-compose ps -q "$service" | xargs docker inspect --format='{{.State.Status}}')
        if [ "$status" = "running" ]; then
            print_status "$service is running ✅"
        else
            print_error "$service is not running ❌"
            return 1
        fi
    done
    
    return 0
}

# Show deployment information
show_deployment_info() {
    print_status "🎉 Deployment completed successfully!"
    echo ""
    echo "📊 Service URLs:"
    echo "  • FastAPI Application: http://localhost:8000"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • Flower (Celery Monitor): http://localhost:5555"
    echo "  • Grafana Dashboard: http://localhost:3000 (admin/admin)"
    echo "  • Prometheus: http://localhost:9090"
    echo ""
    echo "🔧 Management Commands:"
    echo "  • View logs: docker-compose logs -f [service_name]"
    echo "  • Stop services: docker-compose down"
    echo "  • Restart services: docker-compose restart"
    echo ""
    echo "📁 Data Directories:"
    echo "  • ClickHouse data: ./data/clickhouse"
    echo "  • Redis data: ./data/redis"
    echo "  • Application logs: ./logs"
    echo ""
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    docker-compose down
    docker system prune -f
}

# Main deployment function
main() {
    trap cleanup ERR
    
    check_prerequisites
    create_directories
    setup_ssl
    deploy_services
    wait_for_services
    initialize_database
    
    if health_check; then
        show_deployment_info
    else
        print_error "Deployment failed health check"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "cleanup")
        print_status "Cleaning up deployment..."
        docker-compose down -v
        docker system prune -af
        print_status "Cleanup completed"
        ;;
    "logs")
        docker-compose logs -f "${2:-}"
        ;;
    "restart")
        print_status "Restarting services..."
        docker-compose restart "${2:-}"
        print_status "Services restarted"
        ;;
    "status")
        docker-compose ps
        ;;
    *)
        main
        ;;
esac

---

# scripts/development.sh
#!/bin/bash
# Development environment setup

set -e

echo "🛠️  Setting up development environment..."

# Create virtual environment
python3 -m venv crypto_env
source crypto_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Start development services
docker-compose -f docker-compose.dev.yml up -d clickhouse redis

echo "✅ Development environment setup complete!"
echo ""
echo "To start development:"
echo "1. Activate virtual environment: source crypto_env/bin/activate"
echo "2. Start FastAPI: uvicorn main:app --reload"
echo "3. Start Celery worker: celery -A main.celery_app worker --loglevel=info"

---

# scripts/backup.sh
#!/bin/bash
# Backup script for cryptocurrency data system

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="crypto_backup_${TIMESTAMP}"

echo "📦 Creating backup: $BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup ClickHouse data
echo "Backing up ClickHouse data..."
docker-compose exec clickhouse clickhouse-client --query \
    "BACKUP DATABASE crypto_data TO Disk('backups', '$BACKUP_NAME/clickhouse/')"

# Backup Redis data  
echo "Backing up Redis data..."
docker-compose exec redis redis-cli BGSAVE
docker cp $(docker-compose ps -q redis):/data/dump.rdb "$BACKUP_DIR/$BACKUP_NAME/redis/"

# Backup configuration files
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/$BACKUP_NAME/config.tar.gz" \
    .env docker-compose.yml nginx/ monitoring/ clickhouse/

echo "✅ Backup completed: $BACKUP_DIR/$BACKUP_NAME"

---

# scripts/restore.sh
#!/bin/bash
# Restore script for cryptocurrency data system

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_name>"
    echo "Available backups:"
    ls -la ./backups/
    exit 1
fi

BACKUP_NAME="$1"
BACKUP_PATH="./backups/$BACKUP_NAME"

if [ ! -d "$BACKUP_PATH" ]; then
    echo "❌ Backup not found: $BACKUP_PATH"
    exit 1
fi

echo "🔄 Restoring from backup: $BACKUP_NAME"

# Stop services
docker-compose down

# Restore ClickHouse data
if [ -d "$BACKUP_PATH/clickhouse" ]; then
    echo "Restoring ClickHouse data..."
    docker-compose up -d clickhouse
    sleep 10
    docker-compose exec clickhouse clickhouse-client --query \
        "RESTORE DATABASE crypto_data FROM Disk('backups', '$BACKUP_NAME/clickhouse/')"
fi

# Restore Redis data
if [ -f "$BACKUP_PATH/redis/dump.rdb" ]; then
    echo "Restoring Redis data..."
    docker cp "$BACKUP_PATH/redis/dump.rdb" $(docker-compose ps -q redis):/data/
    docker-compose restart redis
fi

# Restore configuration
if [ -f "$BACKUP_PATH/config.tar.gz" ]; then
    echo "Restoring configuration..."
    tar -xzf "$BACKUP_PATH/config.tar.gz"
fi

# Start all services
docker-compose up -d

echo "✅ Restore completed from: $BACKUP_NAME"

---

# scripts/monitor.sh
#!/bin/bash
# System monitoring script

show_system_status() {
    echo "📊 System Status Report"
    echo "======================="
    
    # Docker containers status
    echo ""
    echo "🐳 Docker Containers:"
    docker-compose ps
    
    # System resources
    echo ""
    echo "💻 System Resources:"
    echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1"%"}')"
    echo "Memory Usage: $(free | grep Mem | awk '{printf("%.2f%%"), $3/$2 * 100.0}')"
    echo "Disk Usage: $(df -h / | awk 'NR==2{printf "%s", $5}')"
    
    # Service health checks
    echo ""
    echo "🏥 Service Health:"
    
    # Check API
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "✅ FastAPI: Healthy"
    else
        echo "❌ FastAPI: Unhealthy"
    fi
    
    # Check ClickHouse
    if docker-compose exec clickhouse clickhouse-client --query "SELECT 1" > /dev/null 2>&1; then
        echo "✅ ClickHouse: Healthy"
    else
        echo "❌ ClickHouse: Unhealthy"
    fi
    
    # Check Redis
    if docker-compose exec redis redis-cli ping | grep PONG > /dev/null; then
        echo "✅ Redis: Healthy"
    else
        echo "❌ Redis: Unhealthy"
    fi
}

show_logs() {
    service=${1:-}
    if [ -n "$service" ]; then
        docker-compose logs -f --tail=100 "$service"
    else
        docker-compose logs -f --tail=100
    fi
}

show_metrics() {
    echo "📈 Performance Metrics"
    echo "====================="
    
    # Database metrics
    echo ""
    echo "🗄️  ClickHouse Metrics:"
    docker-compose exec clickhouse clickhouse-client --query \
        "SELECT 
            database,
            count() as tables,
            sum(rows) as total_rows,
            formatReadableSize(sum(bytes_on_disk)) as disk_usage
         FROM system.parts 
         WHERE active = 1 
         GROUP BY database"
    
    # Redis metrics
    echo ""
    echo "🔄 Redis Metrics:"
    docker-compose exec redis redis-cli info memory | grep -E "(used_memory_human|used_memory_peak_human)"
    docker-compose exec redis redis-cli info stats | grep -E "(total_commands_processed|instantaneous_ops_per_sec)"
}

case "${1:-status}" in
    "status")
        show_system_status
        ;;
    "logs")
        show_logs "$2"
        ;;
    "metrics")
        show_metrics
        ;;
    "watch")
        watch -n 5 "$0 status"
        ;;
    *)
        echo "Usage: $0 {status|logs|metrics|watch} [service_name]"
        exit 1
        ;;
esac