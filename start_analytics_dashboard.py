"""
Analytics Dashboard Startup Script
Automated deployment and testing for the complete analytics platform
"""

import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

def install_requirements():
    """Install required Python packages"""
    requirements = [
        "fastapi==0.104.1",
        "uvicorn==0.24.0",
        "pandas==2.1.3", 
        "numpy==1.24.3",
        "scikit-learn==1.3.2",
        "plotly==5.17.0",
        "websockets==12.0",
        "reportlab==4.0.7",
        "python-multipart==0.0.6"
    ]
    
    print("📦 Installing required packages...")
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"✅ Installed: {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install: {package}")
            return False
    
    print("✅ All packages installed successfully!")
    return True

def create_static_directory():
    """Create static directory for assets"""
    static_dir = Path("analytics_dashboard/static")
    static_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created static directory: {static_dir}")

def validate_files():
    """Validate that all required files exist"""
    required_files = [
        "analytics_dashboard/advanced_analytics_service.py",
        "analytics_dashboard/executive_bi_service.py", 
        "analytics_dashboard/realtime_analytics_engine.py",
        "analytics_dashboard/main_analytics_app.py"
    ]
    
    print("🔍 Validating analytics files...")
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ Found: {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present!")
    return True

def start_analytics_server():
    """Start the main analytics server"""
    print("🚀 Starting BookMyMovie Analytics Dashboard...")
    print("=" * 60)
    
    # Change to analytics directory
    os.chdir("analytics_dashboard")
    
    try:
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "main_analytics_app:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Analytics Dashboard stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False
    
    return True

def open_dashboard():
    """Open the dashboard in default browser"""
    time.sleep(3)  # Wait for server to start
    try:
        webbrowser.open("http://localhost:8000")
        print("🌐 Dashboard opened in browser")
    except Exception as e:
        print(f"⚠️ Could not open browser automatically: {e}")
        print("📍 Please visit: http://localhost:8000")

def display_startup_info():
    """Display startup information"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                BookMyMovie Analytics Dashboard                ║
║                     🚀 Enterprise Edition                     ║
╚══════════════════════════════════════════════════════════════╝

🎯 ANALYTICS FEATURES:
────────────────────────────────────────────────────────────────
📊 Advanced Analytics    → ML-powered forecasting & insights
👔 Executive BI          → Strategic dashboards & PDF reports  
⚡ Real-time Engine      → Live WebSocket analytics
🤖 AI Insights          → Predictive analytics & anomaly detection

🌐 ACCESS POINTS:
────────────────────────────────────────────────────────────────
🏠 Main Dashboard        → http://localhost:8000
📈 Analytics Dashboard   → http://localhost:8000/metrics/dashboard
👔 Executive BI          → http://localhost:8000/executive/dashboard
⚡ Real-time Analytics   → http://localhost:8000/realtime/client
📚 API Documentation     → http://localhost:8000/docs

🔧 TECHNICAL STACK:
────────────────────────────────────────────────────────────────
• FastAPI + Uvicorn      • Pandas + NumPy         • Scikit-learn
• Plotly Visualizations  • WebSocket Real-time    • SQLite Database
• ReportLab PDF Reports  • ML Forecasting Models  • Executive KPIs

🚨 SYSTEM STATUS:
────────────────────────────────────────────────────────────────""")

def main():
    """Main startup function"""
    display_startup_info()
    
    # Step 1: Install requirements
    if not install_requirements():
        print("❌ Failed to install requirements. Exiting...")
        sys.exit(1)
    
    # Step 2: Create directories
    create_static_directory()
    
    # Step 3: Validate files
    if not validate_files():
        print("❌ File validation failed. Exiting...")
        sys.exit(1)
    
    print("\n✅ All systems ready! Starting analytics platform...")
    print("🔄 Real-time WebSocket server will start automatically on port 8765")
    print("📍 Dashboard will be available at: http://localhost:8000")
    print("\n" + "─" * 60)
    
    # Step 4: Start server (this will block)
    start_analytics_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Analytics Dashboard shutdown complete")
        print("Thank you for using BookMyMovie Analytics! 👋")
    except Exception as e:
        print(f"\n❌ Startup error: {e}")
        print("Please check the error details and try again.")
        sys.exit(1)