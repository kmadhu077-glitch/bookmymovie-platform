# BookMyMovie Mobile App 📱

A React Native mobile application for booking movie tickets with seamless integration to the BookMyMovie backend services.

## Features ✨

### Authentication
- 🔐 Email/Password login
- 📱 Mobile OTP authentication
- 👤 User registration
- 🔄 Auto-login with stored tokens

### Movie Browsing
- 🎬 Browse featured movies
- 🔍 Search and filter by genre
- ⭐ Movie ratings and details
- 🎭 Genre-based categorization

### Booking System
- 🎫 Seat selection interface
- 💳 Multiple payment methods
- 📧 Booking confirmations
- 📱 Mobile-optimized experience

### User Management
- 👤 Profile management
- 📋 Booking history
- 🔔 Notifications
- ⚙️ Preferences settings

## Tech Stack 🛠

- **React Native 0.72.10** - Mobile framework
- **React Navigation 6** - Navigation system
- **React Native Vector Icons** - Icon library
- **Linear Gradient** - UI enhancements
- **AsyncStorage** - Local data persistence
- **Axios** - HTTP client for API calls

## Project Structure 📁

```
mobile_app/
├── src/
│   ├── screens/           # App screens
│   │   ├── SplashScreen.js
│   │   ├── LoginScreen.js
│   │   ├── RegisterScreen.js
│   │   ├── HomeScreen.js
│   │   ├── MoviesScreen.js
│   │   └── MovieDetailsScreen.js
│   ├── context/           # Context providers
│   │   ├── AuthContext.js
│   │   └── BookingContext.js
│   └── App.js            # Main app component
├── package.json
├── babel.config.js
├── metro.config.js
└── index.js
```

## Installation & Setup 🚀

### Prerequisites
- Node.js >= 16
- React Native CLI
- Android Studio (for Android)
- Xcode (for iOS - macOS only)

### Installation Steps

1. **Navigate to mobile app directory**
   ```bash
   cd mobile_app
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **iOS Setup** (macOS only)
   ```bash
   cd ios && pod install && cd ..
   ```

4. **Start Metro bundler**
   ```bash
   npx react-native start
   ```

5. **Run on Android**
   ```bash
   npx react-native run-android
   ```

6. **Run on iOS** (macOS only)
   ```bash
   npx react-native run-ios
   ```

## API Integration 🔗

The mobile app integrates with the following backend services:

- **Auth Service** (Port 8006) - User authentication
- **Catalog Service** (Port 8005) - Movie listings
- **Booking Service** (Port 8007) - Seat booking
- **Payment Service** (Port 8011) - Payment processing
- **Mobile Auth Service** (Port 8013) - OTP authentication

### API Configuration

Update the API base URLs in the context files:

```javascript
// AuthContext.js
const AUTH_API_BASE = 'http://127.0.0.1:8006/v1/auth';
const MOBILE_API_BASE = 'http://127.0.0.1:8013/v1/mobile';

// BookingContext.js  
const CATALOG_API_BASE = 'http://127.0.0.1:8005/v1/catalog';
const BOOKING_API_BASE = 'http://127.0.0.1:8007/v1/booking';
```

## Features Walkthrough 🎯

### Authentication Flow
1. **Splash Screen** - App initialization and branding
2. **Login Options** - Email/password or mobile OTP
3. **Registration** - New user account creation
4. **Auto-login** - Persistent authentication

### Main Navigation
- **Home Tab** - Featured movies and quick actions
- **Movies Tab** - Browse and search all movies
- **Bookings Tab** - View booking history
- **Profile Tab** - User account management

### Booking Process
1. **Movie Selection** - Browse and select movie
2. **Theater & Showtime** - Choose venue and time
3. **Seat Selection** - Pick preferred seats
4. **Payment** - Complete transaction
5. **Confirmation** - Booking success

## Customization 🎨

### Color Scheme
The app uses a modern indigo-based color palette:
- Primary: `#4f46e5` (Indigo 600)
- Secondary: `#7c3aed` (Purple 600)
- Accent: `#db2777` (Pink 600)

### Typography
- Font Family: Inter (Google Fonts)
- Headings: Bold weights (600-700)
- Body: Regular weight (400-500)

## Development 👨‍💻

### Key Components

**AuthContext**: Manages user authentication state and API calls
**BookingContext**: Handles movie data and booking operations
**Navigation**: Stack and tab navigation setup
**Screens**: Individual screen components with UI logic

### State Management
- Context API for global state
- AsyncStorage for data persistence
- Real-time updates via API polling

## Troubleshooting 🐛

### Common Issues

1. **Metro bundler issues**
   ```bash
   npx react-native clean-project
   npx react-native start --reset-cache
   ```

2. **Android build errors**
   ```bash
   cd android && ./gradlew clean && cd ..
   ```

3. **iOS build errors**
   ```bash
   cd ios && rm -rf Pods && pod install && cd ..
   ```

### API Connection Issues
- Ensure backend services are running
- Check IP addresses in API configurations
- Verify CORS settings on backend

## Future Enhancements 🚀

- [ ] Push notifications
- [ ] Offline support
- [ ] Social media integration
- [ ] Advanced seat selection animations
- [ ] Loyalty points system
- [ ] Movie trailers and reviews
- [ ] Location-based theater suggestions

## Contributing 🤝

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**BookMyMovie Mobile App** - Bringing cinema to your fingertips! 🍿🎬