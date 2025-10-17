# Docker Installation Guide for Windows

## Option 1: Install Docker Desktop (Recommended)

### Automatic Installation Script
Run this PowerShell script as Administrator:

```powershell
# Install Docker Desktop via Chocolatey (if you have Chocolatey)
Set-ExecutionPolicy Bypass -Scope Process -Force
if (Get-Command choco -ErrorAction SilentlyContinue) {
    choco install docker-desktop -y
} else {
    Write-Host "Installing Chocolatey first..."
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    choco install docker-desktop -y
}
```

### Manual Installation
1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Run the installer and follow the setup wizard
3. Restart your computer when prompted
4. Start Docker Desktop from the Start menu
5. Wait for Docker to initialize (you'll see the whale icon in the system tray)

## Option 2: Use Windows Subsystem for Linux (WSL2)

If you prefer using WSL2:

```powershell
# Enable WSL2
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# Restart and then install Ubuntu
wsl --install -d Ubuntu
wsl --set-default-version 2
```

## Option 3: Run Without Docker (Current Setup)

Since Docker setup can take time, you can run the platform immediately using the provided PowerShell script:

```powershell
# Navigate to your project directory
cd C:\Bookmymovie_Project

# Run the startup script
.\start_services.ps1
```

## Docker Commands (After Installation)

Once Docker is installed, you can use these commands:

```powershell
# Build and start all services
docker-compose up --build -d

# View service status
docker-compose ps

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Run with fresh database
docker-compose down -v
docker-compose up --build -d
```

## Verification Steps

After installation, verify Docker is working:

```powershell
# Check Docker version
docker --version
docker-compose --version

# Test with hello-world
docker run hello-world

# Check if Docker daemon is running
docker info
```