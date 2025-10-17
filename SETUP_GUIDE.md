# 🎬 BookMyMovie - Complete Setup Guide

## 📋 Project Overview

**BookMyMovie** is a full-stack movie booking platform with:
- **Backend**: 9 FastAPI microservices (Python)
- **Frontend**: Responsive web interface (HTML/CSS/JS)
- **Mobile App**: React Native application (iOS/Android)

## 🏗️ Architecture

```
BookMyMovie Project
├── backend/                 # 9 Microservices
│   ├── catalog_service.py           # Port 8005 - Movie Catalog
│   ├── auth_service.py              # Port 8006 - Authentication
│   ├── booking_service.py           # Port 8007 - Booking Management
│   ├── payment_service.py           # Port 8008 - Basic Payments
│   ├── notification_service.py      # Port 8009 - Notifications
│   ├── admin_service.py             # Port 8010 - Admin Panel
│   ├── enhanced_payment_service.py  # Port 8011 - Multi-Payment
│   ├── enhanced_user_service.py     # Port 8012 - User Management
│   └── mobile_auth_service.py       # Port 8013 - Mobile OTP
├── frontend/                # Web Interface  
│   ├── index.html                   # Main user interface
│   ├── admin.html                   # Admin dashboard
│   └── user-dashboard.html          # Enhanced user portal
└── mobile_app/              # React Native App
    ├── src/screens/                 # Mobile screens
    ├── src/context/                 # State management
    └── package.json                 # Dependencies
```

## 🚀 Quick Start (5 Minutes)

### 1. Start All Backend Services
```powershell
# Open 9 separate PowerShell terminals in C:\Bookmymovie_Project

# Terminal 1 - Catalog Service
uvicorn backend.catalog_service:app --port 8005 --reload

# Terminal 2 - Auth Service  
uvicorn backend.auth_service:app --port 8006 --reload

# Terminal 3 - Booking Service
uvicorn backend.booking_service:app --port 8007 --reload

# Terminal 4 - Payment Service
uvicorn backend.payment_service:app --port 8008 --reload

# Terminal 5 - Notification Service
uvicorn backend.notification_service:app --port 8009 --reload

# Terminal 6 - Admin Service
uvicorn backend.admin_service:app --port 8010 --reload

# Terminal 7 - Enhanced Payment Service
uvicorn backend.enhanced_payment_service:app --port 8011 --reload

# Terminal 8 - Enhanced User Service  
uvicorn backend.enhanced_user_service:app --port 8012 --reload

# Terminal 9 - Mobile Auth Service
uvicorn backend.mobile_auth_service:app --port 8013 --reload
```

### 2. Access Web Interfaces
- **Main Site**: Open `frontend/index.html` in browser
- **Admin Panel**: Open `frontend/admin.html` in browser  
- **User Dashboard**: Open `frontend/user-dashboard.html` in browser

### 3. Start Mobile App (Optional)
```bash
cd mobile_app
npm install
npx react-native start
npx react-native run-android  # or run-ios
```

## ✅ Service Health Check

Run this PowerShell command to verify all services:

```powershell
$services = @{8005="Catalog"; 8006="Auth"; 8007="Booking"; 8008="Payment"; 8009="Notification"; 8010="Admin"; 8011="Enhanced Payment"; 8012="Enhanced User"; 8013="Mobile Auth"}; foreach($port in $services.Keys) { try { Invoke-WebRequest "http://127.0.0.1:$port/health" -UseBasicParsing -TimeoutSec 3 | Out-Null; Write-Host "✅ $($services[$port]) (Port $port): RUNNING" } catch { Write-Host "❌ $($services[$port]) (Port $port): DOWN" } }
```

Expected output:
```
✅ Catalog (Port 8005): RUNNING
✅ Auth (Port 8006): RUNNING  
✅ Booking (Port 8007): RUNNING
✅ Payment (Port 8008): RUNNING
✅ Notification (Port 8009): RUNNING
✅ Admin (Port 8010): RUNNING
✅ Enhanced Payment (Port 8011): RUNNING
✅ Enhanced User (Port 8012): RUNNING
✅ Mobile Auth (Port 8013): RUNNING
```

## 🎯 Features Demonstration

### 1. User Registration & Login
- **Web**: Use `frontend/index.html` registration form
- **Mobile**: Email/password or mobile OTP authentication
- **Test Credentials**: Any email/password combination

### 2. Movie Booking Flow
1. Browse movies in catalog
2. Select movie and view details  
3. Choose theater and showtime
4. Select seats interactively
5. Choose payment method (Credit/Debit/UPI)
6. Complete booking and get confirmation

### 3. Admin Panel Features
- **Dashboard**: Analytics and system overview
- **Movie Management**: Add, edit, delete movies
- **User Management**: View and manage users
- **Booking Reports**: Comprehensive reporting
- **Theater Management**: Configure venues

### 4. Payment Methods
- **Credit Cards**: Visa, MasterCard, American Express
- **Debit Cards**: All major banks supported  
- **UPI**: PhonePe, GooglePay, Paytm
- **Net Banking**: Secure bank transfers

### 5. Mobile Features
- **Cross-Platform**: iOS and Android support
- **Offline Support**: Basic functionality without internet
- **Push Notifications**: Booking confirmations and updates
- **Biometric Login**: Fingerprint/Face ID support

## 🛠️ Technical Stack

### Backend Services
- **Framework**: FastAPI (Python 3.9+)
- **Server**: Uvicorn ASGI server
- **Validation**: Pydantic models
- **HTTP Client**: httpx for service communication
- **CORS**: Cross-origin resource sharing enabled

### Frontend Web
- **Framework**: Vanilla HTML5/CSS3/JavaScript
- **Styling**: Tailwind CSS utility framework
- **Icons**: Font Awesome 6
- **Charts**: Chart.js for analytics
- **Responsive**: Mobile-first design

### Mobile App
- **Framework**: React Native 0.72.10
- **Navigation**: React Navigation v6
- **State**: Context API with AsyncStorage
- **Icons**: React Native Vector Icons
- **Styling**: StyleSheet with responsive design

## 📊 API Documentation

### Authentication Endpoints
```http
POST /v1/auth/register     # User registration
POST /v1/auth/login        # User login
POST /v1/mobile/request-otp # Mobile OTP request
POST /v1/mobile/verify-otp  # Mobile OTP verification
```

### Movie & Booking Endpoints  
```http
GET /v1/catalog/movies     # Fetch movie catalog
GET /v1/catalog/theaters   # Get theaters for movie
GET /v1/booking/seats      # Available seats
POST /v1/booking/book      # Create booking
GET /v1/booking/history    # Booking history
```

### Payment Endpoints
```http
POST /v1/payment/process   # Process payment
POST /v1/payment/validate  # Validate card details  
GET /v1/payment/methods    # Saved payment methods
```

### Admin Endpoints
```http
GET /v1/admin/dashboard    # Admin analytics
POST /v1/admin/movies      # Add movie
PUT /v1/admin/movies/{id}  # Update movie
DELETE /v1/admin/movies/{id} # Delete movie
```

## 🔧 Configuration

### Environment Setup
```powershell
# Clone or navigate to project
cd C:\Bookmymovie_Project

# Activate Python virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already done)
pip install fastapi uvicorn pydantic httpx python-multipart
```

### CORS Configuration
All services include CORS middleware for frontend integration:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
```

### Mobile App Configuration
Update API URLs in context files for your environment:
```javascript
const API_BASE_URL = 'http://127.0.0.1'; // Change for production
```

## 🚨 Troubleshooting

### Common Issues

**Services won't start:**
```powershell
# Check if ports are in use
netstat -an | findstr :8005
# Kill processes if needed
taskkill /f /im python.exe
```

**Import errors:**
```powershell
# Reinstall dependencies
pip install --upgrade fastapi uvicorn pydantic httpx
```

**Frontend not connecting:**
- Verify all services are running on correct ports
- Check browser console for CORS errors
- Ensure backend services have CORS enabled

**Mobile app build issues:**
```bash
# Clear React Native cache
npx react-native start --reset-cache
# Clean Android build
cd android && ./gradlew clean && cd ..
```

### Performance Optimization

**Backend:**
- Services run independently for scalability
- In-memory storage for demo (use Redis/PostgreSQL for production)
- Connection pooling for service-to-service communication

**Frontend:**
- CDN-hosted libraries (Tailwind, Font Awesome)
- Optimized image loading and caching
- Responsive design for all screen sizes

**Mobile:**
- Lazy loading for screens and components  
- Efficient state management with Context API
- Optimized bundle size with Metro bundler

## 📱 Mobile App Deep Dive

### Screen Flow
```
Splash → Login/Register → Main Tabs (Home/Movies/Bookings/Profile)
                           ↓
Movie Details → Seat Selection → Payment → Confirmation
```

### Key Features
- **Biometric Authentication**: TouchID/FaceID support
- **Offline Mode**: View cached movies and bookings
- **Push Notifications**: Real-time booking updates  
- **Deep Linking**: Direct navigation to specific screens
- **Analytics**: User behavior tracking and insights

## 🌐 Production Deployment

### Backend Deployment
- **Docker**: Containerize each microservice
- **Kubernetes**: Orchestration and scaling
- **Load Balancer**: Distribute traffic across instances
- **Database**: PostgreSQL with Redis caching
- **Monitoring**: Prometheus + Grafana

### Frontend Deployment  
- **CDN**: Static file distribution
- **SSL**: HTTPS certificate configuration
- **Caching**: Browser and CDN caching strategies
- **Minification**: CSS/JS optimization

### Mobile Deployment
- **App Stores**: Google Play Store and Apple App Store
- **Code Push**: Over-the-air updates
- **Analytics**: Crashlytics and performance monitoring
- **Beta Testing**: TestFlight (iOS) and Play Console (Android)

## 🤝 Contributing

### Development Workflow
1. **Fork**: Create personal copy of repository
2. **Branch**: Create feature branch (`feature/new-feature`)
3. **Code**: Implement changes with tests
4. **Test**: Verify all services and features work
5. **PR**: Submit pull request with detailed description

### Code Standards
- **Backend**: Follow PEP 8 Python style guide
- **Frontend**: ESLint configuration for consistency
- **Mobile**: React Native best practices
- **Documentation**: Clear comments and README updates

---

**🎬 BookMyMovie Platform** - Your complete cinema booking solution! 🍿

*Ready to book your next movie? Start all services and enjoy the experience!*