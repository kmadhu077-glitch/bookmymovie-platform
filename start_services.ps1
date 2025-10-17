# BookMyMovie Platform - Development Startup Script (PowerShell)
# This script starts all services locally without Docker

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   BookMyMovie Platform - Development Mode" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Set development environment variables
$env:ENVIRONMENT = "development"
$env:DATABASE_URL = "sqlite:///./bookmymovie_dev.db"
$env:REDIS_URL = "memory://localhost"
$env:JWT_SECRET_KEY = "dev-jwt-secret-key-not-for-production"

Write-Host "`nStarting BookMyMovie services..." -ForegroundColor Green

# Function to start a service
function Start-Service {
    param(
        [string]$ServiceName,
        [string]$Script,
        [int]$Port
    )
    
    Write-Host "Starting $ServiceName on port $Port..." -ForegroundColor Yellow
    
    $processArgs = @{
        FilePath = "python"
        ArgumentList = $Script
        WorkingDirectory = "C:\Bookmymovie_Project"
        PassThru = $true
        WindowStyle = "Minimized"
    }
    
    try {
        $process = Start-Process @processArgs
        Start-Sleep -Seconds 2
        
        # Check if service is responding
        $isListening = (netstat -ano | Select-String ":$Port.*LISTENING") -ne $null
        
        if ($isListening) {
            Write-Host "[OK] $ServiceName started successfully" -ForegroundColor Green
        } else {
            Write-Host "[WARN] $ServiceName may have issues" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[ERROR] Failed to start $ServiceName : $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Start all services
Start-Service "Auth Service" "backend\secure_auth_service.py" 8013
Start-Service "Catalog Service" "backend\secure_catalog_service.py" 8012  
Start-Service "Booking Service" "backend\secure_booking_service.py" 8014
Start-Service "Payment Service" "backend\secure_payment_service.py" 8015
Start-Service "Real-time Service" "backend\secure_realtime_service.py" 8016

# Start Frontend
Write-Host "Starting Frontend on port 8080..." -ForegroundColor Yellow
try {
    $frontendArgs = @{
        FilePath = "python"
        ArgumentList = @("-m", "http.server", "8080")
        WorkingDirectory = "C:\Bookmymovie_Project\frontend"
        PassThru = $true
        WindowStyle = "Minimized"
    }
    $frontendProcess = Start-Process @frontendArgs
    Start-Sleep -Seconds 2
    
    $isListening = (netstat -ano | Select-String ":8080.*LISTENING") -ne $null
    if ($isListening) {
        Write-Host "[OK] Frontend started successfully" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Frontend may have issues" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[ERROR] Failed to start Frontend: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "Service Status Check" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Check service status
$services = @(
    @{Name="Auth Service"; Port=8013; URL="http://localhost:8013/docs"},
    @{Name="Catalog Service"; Port=8012; URL="http://localhost:8012/docs"},
    @{Name="Booking Service"; Port=8014; URL="http://localhost:8014/docs"},
    @{Name="Payment Service"; Port=8015; URL="http://localhost:8015/docs"},
    @{Name="Real-time Service"; Port=8016; URL="http://localhost:8016/docs"},
    @{Name="Frontend"; Port=8080; URL="http://localhost:8080"}
)

foreach ($service in $services) {
    $isRunning = (netstat -ano | Select-String ":$($service.Port).*LISTENING") -ne $null
    $status = if ($isRunning) { "[RUNNING]" } else { "[STOPPED]" }
    $color = if ($isRunning) { "Green" } else { "Red" }
    
    Write-Host "$($service.Name): $status - $($service.URL)" -ForegroundColor $color
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "All services setup complete!" -ForegroundColor Green
Write-Host "Main Application: http://localhost:8080" -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan

# Optional: Open browser to main application
$response = Read-Host "`nWould you like to open the application in your browser? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Start-Process "http://localhost:8080"
}