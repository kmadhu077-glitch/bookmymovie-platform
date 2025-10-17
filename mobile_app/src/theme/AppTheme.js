/**
 * BookMyMovie App Theme Configuration
 * Consistent design system for mobile application
 */

import { DefaultTheme } from 'react-native-paper';
import { Platform } from 'react-native';

// Color palette
const colors = {
  primary: '#E50914', // Netflix red
  primaryVariant: '#B20710',
  secondary: '#FFD700', // Gold accent
  secondaryVariant: '#FFC107',
  background: '#0F0F23', // Dark blue background
  surface: '#1A1A2E', // Slightly lighter dark blue
  error: '#CF6679',
  success: '#4CAF50',
  warning: '#FF9800',
  info: '#2196F3',
  
  // Text colors
  onPrimary: '#FFFFFF',
  onSecondary: '#000000',
  onBackground: '#FFFFFF',
  onSurface: '#FFFFFF',
  onError: '#000000',
  
  // Additional colors
  text: '#FFFFFF',
  textSecondary: '#B3B3B3',
  disabled: '#666666',
  placeholder: '#888888',
  backdrop: 'rgba(0, 0, 0, 0.5)',
  outline: '#333333',
  
  // Gradient colors
  gradientStart: '#0F0F23',
  gradientEnd: '#1A1A2E',
  
  // Movie rating colors
  ratingExcellent: '#4CAF50',
  ratingGood: '#8BC34A',
  ratingAverage: '#FF9800',
  ratingPoor: '#F44336',
  
  // Seat selection colors
  seatAvailable: '#4CAF50',
  seatSelected: '#E50914',
  seatBooked: '#666666',
  seatPremium: '#FFD700',
};

// Typography
const fonts = {
  regular: {
    fontFamily: Platform.OS === 'ios' ? 'System' : 'Roboto',
    fontWeight: '400',
  },
  medium: {
    fontFamily: Platform.OS === 'ios' ? 'System' : 'Roboto-Medium',
    fontWeight: '500',
  },
  bold: {
    fontFamily: Platform.OS === 'ios' ? 'System' : 'Roboto-Bold',
    fontWeight: '700',
  },
  light: {
    fontFamily: Platform.OS === 'ios' ? 'System' : 'Roboto-Light',
    fontWeight: '300',
  },
};

// Spacing system
const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
};

// Border radius system
const borderRadius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  round: 50,
};

// Shadow system
const shadows = {
  small: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  medium: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.30,
    shadowRadius: 4.65,
    elevation: 8,
  },
  large: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 6,
    },
    shadowOpacity: 0.37,
    shadowRadius: 7.49,
    elevation: 12,
  },
};

// Animation durations
const animations = {
  fast: 200,
  normal: 300,
  slow: 500,
};

// Create the main theme object
export const theme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    ...colors,
  },
  fonts,
  spacing,
  borderRadius,
  shadows,
  animations,
  
  // Component specific styles
  components: {
    button: {
      height: 48,
      borderRadius: borderRadius.md,
      paddingHorizontal: spacing.lg,
    },
    card: {
      borderRadius: borderRadius.lg,
      backgroundColor: colors.surface,
      ...shadows.medium,
    },
    input: {
      height: 56,
      borderRadius: borderRadius.md,
      paddingHorizontal: spacing.md,
      backgroundColor: colors.surface,
      borderColor: colors.outline,
    },
    movieCard: {
      width: 150,
      height: 225,
      borderRadius: borderRadius.md,
      ...shadows.small,
    },
    theaterCard: {
      borderRadius: borderRadius.lg,
      backgroundColor: colors.surface,
      padding: spacing.md,
      marginVertical: spacing.sm,
      ...shadows.small,
    },
  },
  
  // Screen specific styles
  screens: {
    padding: spacing.md,
    headerHeight: 60,
    tabBarHeight: Platform.OS === 'ios' ? 85 : 60,
  },
};

// Light theme variant (for future use)
export const lightTheme = {
  ...theme,
  dark: false,
  colors: {
    ...theme.colors,
    primary: '#E50914',
    background: '#FFFFFF',
    surface: '#F5F5F5',
    onBackground: '#000000',
    onSurface: '#000000',
    text: '#000000',
    textSecondary: '#666666',
    outline: '#E0E0E0',
  },
};

export default theme;