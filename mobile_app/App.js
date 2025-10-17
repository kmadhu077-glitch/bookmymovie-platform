/**
 * BookMyMovie Mobile App
 * Enterprise React Native Application
 * @format
 */

import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Provider as PaperProvider } from 'react-native-paper';
import { QueryClient, QueryClientProvider } from 'react-query';
import { StatusBar, Platform, PermissionsAndroid } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import messaging from '@react-native-firebase/messaging';
import { AuthProvider } from './src/contexts/AuthContext';
import { ThemeProvider } from './src/contexts/ThemeContext';
import { NotificationService } from './src/services/NotificationService';

// Screens
import SplashScreen from './src/screens/SplashScreen';
import LoginScreen from './src/screens/auth/LoginScreen';
import RegisterScreen from './src/screens/auth/RegisterScreen';
import HomeScreen from './src/screens/home/HomeScreen';
import MoviesScreen from './src/screens/movies/MoviesScreen';
import MovieDetailsScreen from './src/screens/movies/MovieDetailsScreen';
import TheatersScreen from './src/screens/theaters/TheatersScreen';
import BookingScreen from './src/screens/booking/BookingScreen';
import BookingConfirmationScreen from './src/screens/booking/BookingConfirmationScreen';
import ProfileScreen from './src/screens/profile/ProfileScreen';
import MyBookingsScreen from './src/screens/profile/MyBookingsScreen';
import SettingsScreen from './src/screens/settings/SettingsScreen';
import NotificationsScreen from './src/screens/notifications/NotificationsScreen';

// Theme
import { theme } from './src/theme/AppTheme';

// Create navigation instances
const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

// Create QueryClient for API state management
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

// Bottom Tab Navigator
const MainTabs = () => {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;
          switch (route.name) {
            case 'Home':
              iconName = 'home';
              break;
            case 'Movies':
              iconName = 'movie';
              break;
            case 'Theaters':
              iconName = 'place';
              break;
            case 'Profile':
              iconName = 'person';
              break;
            default:
              iconName = 'home';
          }
          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.text,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.outline,
          paddingBottom: Platform.OS === 'ios' ? 20 : 5,
          height: Platform.OS === 'ios' ? 85 : 60,
        },
        headerShown: false,
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Movies" component={MoviesScreen} />
      <Tab.Screen name="Theaters" component={TheatersScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
};

// Main App Component
const App = () => {
  useEffect(() => {
    // Request permissions for Android
    if (Platform.OS === 'android') {
      requestPermissions();
    }

    // Initialize notification service
    NotificationService.initialize();

    // Handle background messages
    messaging().setBackgroundMessageHandler(async remoteMessage => {
      console.log('Message handled in the background!', remoteMessage);
    });
  }, []);

  const requestPermissions = async () => {
    try {
      const permissions = [
        PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
        PermissionsAndroid.PERMISSIONS.ACCESS_COARSE_LOCATION,
        PermissionsAndroid.PERMISSIONS.CAMERA,
      ];

      const granted = await PermissionsAndroid.requestMultiple(permissions);
      console.log('Permissions granted:', granted);
    } catch (err) {
      console.warn('Permission request error:', err);
    }
  };

  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider theme={theme}>
        <ThemeProvider>
          <AuthProvider>
            <StatusBar
              barStyle={theme.dark ? 'light-content' : 'dark-content'}
              backgroundColor={theme.colors.surface}
            />
            <NavigationContainer theme={theme}>
              <Stack.Navigator
                screenOptions={{
                  headerShown: false,
                  cardStyleInterpolator: ({ current }) => ({
                    cardStyle: {
                      opacity: current.progress,
                    },
                  }),
                }}
              >
                <Stack.Screen name="Splash" component={SplashScreen} />
                <Stack.Screen name="Login" component={LoginScreen} />
                <Stack.Screen name="Register" component={RegisterScreen} />
                <Stack.Screen name="MainTabs" component={MainTabs} />
                <Stack.Screen
                  name="MovieDetails"
                  component={MovieDetailsScreen}
                  options={{
                    headerShown: true,
                    title: 'Movie Details',
                    headerStyle: {
                      backgroundColor: theme.colors.surface,
                    },
                    headerTintColor: theme.colors.onSurface,
                  }}
                />
                <Stack.Screen
                  name="Booking"
                  component={BookingScreen}
                  options={{
                    headerShown: true,
                    title: 'Book Tickets',
                    headerStyle: {
                      backgroundColor: theme.colors.surface,
                    },
                    headerTintColor: theme.colors.onSurface,
                  }}
                />
                <Stack.Screen
                  name="BookingConfirmation"
                  component={BookingConfirmationScreen}
                  options={{
                    headerShown: true,
                    title: 'Booking Confirmed',
                    headerStyle: {
                      backgroundColor: theme.colors.surface,
                    },
                    headerTintColor: theme.colors.onSurface,
                  }}
                />
                <Stack.Screen
                  name="MyBookings"
                  component={MyBookingsScreen}
                  options={{
                    headerShown: true,
                    title: 'My Bookings',
                    headerStyle: {
                      backgroundColor: theme.colors.surface,
                    },
                    headerTintColor: theme.colors.onSurface,
                  }}
                />
                <Stack.Screen
                  name="Settings"
                  component={SettingsScreen}
                  options={{
                    headerShown: true,
                    title: 'Settings',
                    headerStyle: {
                      backgroundColor: theme.colors.surface,
                    },
                    headerTintColor: theme.colors.onSurface,
                  }}
                />
                <Stack.Screen
                  name="Notifications"
                  component={NotificationsScreen}
                  options={{
                    headerShown: true,
                    title: 'Notifications',
                    headerStyle: {
                      backgroundColor: theme.colors.surface,
                    },
                    headerTintColor: theme.colors.onSurface,
                  }}
                />
              </Stack.Navigator>
            </NavigationContainer>
          </AuthProvider>
        </ThemeProvider>
      </PaperProvider>
    </QueryClientProvider>
  );
};

export default App;