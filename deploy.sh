#!/bin/bash

# Production Deployment Script for BookMyMovie Platform
# This script automates the deployment process for cloud environments

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

# Configuration
DEPLOYMENT_ENV=${1:-production}
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="bookmymovie"
DOCKER_REGISTRY=${DOCKER_REGISTRY:-"your-registry.amazonaws.com"}

# Validate environment
validate_environment() {
    log "Validating deployment environment..."
    
    # Check required environment variables
    required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "JWT_SECRET_KEY"
        "STRIPE_SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    log "Environment validation passed"
}

# Build Docker images
build_images() {
    log "Building Docker images..."
    
    # Build main application image
    docker build -t ${PROJECT_NAME}:latest .
    docker build -t ${PROJECT_NAME}:${DEPLOYMENT_ENV} .
    
    # Tag for registry
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        docker tag ${PROJECT_NAME}:latest ${DOCKER_REGISTRY}/${PROJECT_NAME}:latest
        docker tag ${PROJECT_NAME}:${DEPLOYMENT_ENV} ${DOCKER_REGISTRY}/${PROJECT_NAME}:${DEPLOYMENT_ENV}
    fi
    
    log "Docker images built successfully"
}

# Push images to registry
push_images() {
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        log "Pushing images to registry..."
        
        docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:latest
        docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:${DEPLOYMENT_ENV}
        
        log "Images pushed to registry successfully"
    else
        warn "No registry specified, skipping image push"
    fi
}

# Setup database
setup_database() {
    log "Setting up database..."
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    until docker-compose exec -T db pg_isready -U bookmymovie -d bookmymovie; do
        sleep 2
    done
    
    # Run migrations
    log "Running database migrations..."
    docker-compose exec -T auth-service python backend/database_optimizer.py
    
    # Generate sample data (only for development)
    if [[ "$DEPLOYMENT_ENV" == "development" ]]; then
        log "Generating sample data..."
        docker-compose exec -T auth-service python backend/generate_sample_data.py
    fi
    
    log "Database setup completed"
}

# Setup SSL certificates (for production)
setup_ssl() {
    if [[ "$DEPLOYMENT_ENV" == "production" ]]; then
        log "Setting up SSL certificates..."
        
        # Create SSL directory
        mkdir -p nginx/ssl
        
        # Generate self-signed certificates (replace with real certificates in production)
        if [[ ! -f "nginx/ssl/server.crt" ]]; then
            warn "Generating self-signed SSL certificates (replace with real certificates)"
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout nginx/ssl/server.key \
                -out nginx/ssl/server.crt \
                -subj "/C=US/ST=State/L=City/O=Organization/CN=bookmymovie.com"
        fi
        
        log "SSL certificates ready"
    fi
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring directories
    mkdir -p monitoring/{prometheus,grafana/dashboards,grafana/datasources}
    
    # Create Prometheus configuration
    cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bookmymovie-services'
    static_configs:
      - targets: 
        - 'auth-service:8013'
        - 'catalog-service:8012'
        - 'booking-service:8014'
        - 'payment-service:8015'
        - 'realtime-service:8016'
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

    # Create Grafana datasource
    cat > monitoring/grafana/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
    
    log "Monitoring configuration created"
}

# Deploy application
deploy() {
    log "Deploying BookMyMovie platform..."
    
    # Pull latest images (if using registry)
    if [[ -n "$DOCKER_REGISTRY" ]]; then
        docker-compose pull
    fi
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    services=("auth-service" "catalog-service" "booking-service" "payment-service" "realtime-service")
    for service in "${services[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            log "$service is running"
        else
            error "$service failed to start"
            exit 1
        fi
    done
    
    log "Deployment completed successfully"
}

# Run health checks
health_check() {
    log "Running health checks..."
    
    # Check API endpoints
    endpoints=(
        "http://localhost:8013/docs"
        "http://localhost:8012/docs"
        "http://localhost:8014/docs"
        "http://localhost:8015/docs"
        "http://localhost:8016/docs"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$endpoint" > /dev/null; then
            log "✓ $endpoint is healthy"
        else
            warn "✗ $endpoint is not responding"
        fi
    done
    
    # Check database connection
    if docker-compose exec -T db pg_isready -U bookmymovie -d bookmymovie > /dev/null; then
        log "✓ Database is healthy"
    else
        warn "✗ Database connection failed"
    fi
    
    # Check Redis connection
    if docker-compose exec -T redis redis-cli ping > /dev/null; then
        log "✓ Redis is healthy"
    else
        warn "✗ Redis connection failed"
    fi
    
    log "Health checks completed"
}

# Backup data
backup_data() {
    log "Creating data backup..."
    
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    docker-compose exec -T db pg_dump -U bookmymovie bookmymovie > "$BACKUP_DIR/database.sql"
    
    # Backup Redis data
    docker-compose exec -T redis redis-cli --rdb - > "$BACKUP_DIR/redis.rdb"
    
    log "Backup created in $BACKUP_DIR"
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo
    docker-compose ps
    echo
    log "Service URLs:"
    echo "  Frontend: http://localhost (https://localhost for SSL)"
    echo "  Auth Service: http://localhost:8013/docs"
    echo "  Catalog Service: http://localhost:8012/docs"
    echo "  Booking Service: http://localhost:8014/docs"
    echo "  Payment Service: http://localhost:8015/docs"
    echo "  Real-time Service: http://localhost:8016/docs"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana: http://localhost:3000 (admin/SecureGrafanaPass123!)"
    echo
}

# Main deployment process
main() {
    log "Starting BookMyMovie deployment process..."
    log "Environment: $DEPLOYMENT_ENV"
    
    case "${2:-all}" in
        "build")
            validate_environment
            build_images
            ;;
        "push")
            push_images
            ;;
        "deploy")
            setup_ssl
            setup_monitoring
            deploy
            setup_database
            ;;
        "health")
            health_check
            ;;
        "backup")
            backup_data
            ;;
        "status")
            show_status
            ;;
        "all")
            validate_environment
            build_images
            push_images
            setup_ssl
            setup_monitoring
            deploy
            setup_database
            health_check
            show_status
            ;;
        *)
            echo "Usage: $0 [environment] [action]"
            echo "Environment: production|staging|development (default: production)"
            echo "Actions: build|push|deploy|health|backup|status|all (default: all)"
            exit 1
            ;;
    esac
    
    log "Deployment process completed successfully!"
}

# Run main function
main "$@"