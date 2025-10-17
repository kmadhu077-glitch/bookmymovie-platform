# BookMyMovie Platform - Docker Compose Setup Guide

## Current Status: ✅ Running Successfully Without Docker

Your BookMyMovie platform is currently running successfully using the local Python environment:

- **Frontend**: http://localhost:8080
- **Auth API**: http://localhost:8013/docs  
- **Catalog API**: http://localhost:8012/docs
- **Booking API**: http://localhost:8014/docs
- **Payment API**: http://localhost:8015/docs
- **Real-time API**: http://localhost:8016/docs

## Docker Compose Benefits

When you're ready to move to Docker, you'll get these benefits:

### ✅ **Isolation & Consistency**
- Each service runs in its own container
- Consistent environment across different machines
- No dependency conflicts between services

### ✅ **Production-Like Environment**
- Uses PostgreSQL database (instead of SQLite)
- Redis caching for better performance
- Load balancing with Nginx

### ✅ **Easy Scaling**
- Scale individual services independently
- Add/remove service instances as needed
- Better resource management

### ✅ **Simplified Deployment**
- One command to start everything: `docker-compose up`
- Easy to deploy to cloud platforms
- Consistent across development, staging, and production

## Docker Installation Options

### Option 1: Docker Desktop (Easiest)
1. Download from: https://www.docker.com/products/docker-desktop
2. Install and restart your computer
3. Start Docker Desktop
4. Run: `docker-compose up --build`

### Option 2: Using Windows Package Manager
```powershell
# Install using winget (Windows 10/11)
winget install Docker.DockerDesktop

# Or using Chocolatey
choco install docker-desktop
```

## Docker Compose Configuration Overview

Your `docker-compose.yml` includes:

### **Core Services**
```yaml
services:
  auth-service:     # Authentication & JWT handling
  catalog-service:  # Movie catalog & showtimes  
  booking-service:  # Ticket booking & seats
  payment-service:  # Payment processing
  realtime-service: # WebSocket notifications
```

### **Infrastructure Services**
```yaml
  db:              # PostgreSQL database
  redis:           # Caching & session storage
  nginx:           # Load balancer & API gateway
  prometheus:      # Monitoring & metrics
  grafana:         # Monitoring dashboard
```

### **Key Features**
- **Health Checks**: Automatic service health monitoring
- **Auto-Restart**: Services restart if they crash
- **Persistent Storage**: Database data survives container restarts
- **Network Isolation**: Secure inter-service communication
- **Resource Limits**: CPU and memory constraints

## Migration Path (When Ready)

### Step 1: Install Docker
Follow the installation guide above.

### Step 2: Stop Current Services
```powershell
# Stop all Python processes
taskkill /F /IM python.exe
```

### Step 3: Start with Docker
```powershell
# Navigate to project directory
cd C:\Bookmymovie_Project

# Build and start all services
docker-compose up --build -d

# Check status
docker-compose ps
```

### Step 4: Access Services
The same URLs will work:
- Frontend: http://localhost:8080
- APIs: http://localhost:8012-8016/docs

### Step 5: Additional Services
With Docker, you also get:
- Prometheus: http://localhost:9090 (monitoring)
- Grafana: http://localhost:3000 (dashboards)

## Useful Docker Commands

### **Basic Operations**
```powershell
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services  
docker-compose down

# Rebuild and restart
docker-compose up --build -d

# View service status
docker-compose ps
```

### **Database Management**
```powershell
# Access database
docker-compose exec db psql -U bookmymovie bookmymovie

# Backup database
docker-compose exec db pg_dump -U bookmymovie bookmymovie > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T db psql -U bookmymovie bookmymovie
```

### **Monitoring**
```powershell
# View resource usage
docker stats

# View service logs
docker-compose logs auth-service
docker-compose logs catalog-service

# Execute command in container
docker-compose exec auth-service python --version
```

## Environment Configuration

### Development (.env.development)
```env
DATABASE_URL=postgresql://bookmymovie:SecurePass123!@db:5432/bookmymovie
REDIS_URL=redis://redis:6379/0
ENVIRONMENT=development
```

### Production (.env.production)
```env
DATABASE_URL=postgresql://user:pass@production-db:5432/bookmymovie
REDIS_URL=redis://production-redis:6379/0
ENVIRONMENT=production
JWT_SECRET_KEY=production-secret-key
```

## Troubleshooting Docker Issues

### Port Conflicts
If you get port conflicts:
```powershell
# Find what's using the port
netstat -ano | findstr :8080

# Kill the process
taskkill /F /PID <process-id>
```

### Container Issues
```powershell
# View detailed logs
docker-compose logs --tail=100 service-name

# Restart specific service
docker-compose restart service-name

# Remove all containers and start fresh
docker-compose down -v
docker-compose up --build -d
```

### Database Connection Issues
```powershell
# Check database status
docker-compose exec db pg_isready -U bookmymovie

# Reset database
docker-compose down -v
docker volume rm bookmymovie-project_postgres_data
docker-compose up -d
```

## Performance Comparison

| Feature | Current Setup | Docker Setup |
|---------|---------------|--------------|
| Startup Time | ~10 seconds | ~30 seconds (first time) |
| Memory Usage | ~200MB | ~500MB |
| Isolation | Shared Python env | Full isolation |
| Database | SQLite | PostgreSQL |
| Caching | In-memory | Redis |
| Monitoring | Basic | Prometheus+Grafana |
| Production Ready | Development | Production |

## Next Steps

1. **Current**: Continue using the current setup for development
2. **When Ready**: Install Docker Desktop
3. **Migration**: Follow the migration steps above
4. **Production**: Use Docker for production deployment

Your platform is working perfectly as-is. Docker adds production-grade features when you need them!

## Quick Reference

### Current Commands (No Docker)
```powershell
# Start services
.\start_services.ps1

# Stop services
taskkill /F /IM python.exe
```

### Future Commands (With Docker)
```powershell
# Start services
docker-compose up -d

# Stop services
docker-compose down
```

Both approaches give you the same BookMyMovie platform functionality!