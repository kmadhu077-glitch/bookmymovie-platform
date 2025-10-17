/**
 * React Native Development Setup Script
 * Sets up the complete React Native environment and dependencies
 */

# Install Node.js dependencies
Write-Host "📱 Setting up BookMyMovie Mobile App..." -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Navigate to mobile app directory
Set-Location "C:\Bookmymovie_Project\mobile_app"

# Install dependencies
Write-Host "`n📦 Installing React Native dependencies..." -ForegroundColor Yellow
npm install

# Install additional mobile-specific packages
Write-Host "`n🔧 Installing mobile-specific packages..." -ForegroundColor Yellow
npm install --save @react-native-firebase/app @react-native-firebase/messaging
npm install --save @react-native-community/geolocation @react-native-community/netinfo
npm install --save react-native-biometrics react-native-encrypted-storage
npm install --save react-native-fast-image react-native-gesture-handler
npm install --save react-native-keychain react-native-maps
npm install --save react-native-modal react-native-push-notification
npm install --save react-native-qrcode-generator react-native-qrcode-scanner
npm install --save react-native-reanimated react-native-sound
npm install --save react-native-svg react-native-webview
npm install --save react-query styled-components
npm install --save react-native-mmkv react-native-dotenv

# Development dependencies
Write-Host "`n🛠️ Installing development dependencies..." -ForegroundColor Yellow
npm install --save-dev react-native-flipper @flipper/client

# Create necessary directories
Write-Host "`n📁 Creating directory structure..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "android"
New-Item -ItemType Directory -Force -Path "ios"
New-Item -ItemType Directory -Force -Path "src\assets\images"
New-Item -ItemType Directory -Force -Path "src\assets\fonts"
New-Item -ItemType Directory -Force -Path "src\utils"
New-Item -ItemType Directory -Force -Path "src\hooks"
New-Item -ItemType Directory -Force -Path "src\navigation"

Write-Host "`n✅ Mobile app setup completed!" -ForegroundColor Green
Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Configure Firebase for push notifications" -ForegroundColor White
Write-Host "2. Set up Android Studio for Android development" -ForegroundColor White
Write-Host "3. Set up Xcode for iOS development (macOS only)" -ForegroundColor White
Write-Host "4. Run 'npx react-native run-android' or 'npx react-native run-ios'" -ForegroundColor White

Write-Host "`n🎬 BookMyMovie Mobile App is ready for development!" -ForegroundColor Green