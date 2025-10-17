/**
 * Authentication Context
 * Manages user authentication state and operations
 */

import React, { createContext, useContext, useReducer, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import { AuthService } from '../services/AuthService';
import { BiometricService } from '../services/BiometricService';

// Initial state
const initialState = {
  isLoading: true,
  isAuthenticated: false,
  user: null,
  token: null,
  biometricEnabled: false,
  error: null,
};

// Action types
const AuthActionTypes = {
  SET_LOADING: 'SET_LOADING',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_FAILURE: 'LOGIN_FAILURE',
  LOGOUT: 'LOGOUT',
  SET_USER: 'SET_USER',
  SET_BIOMETRIC: 'SET_BIOMETRIC',
  CLEAR_ERROR: 'CLEAR_ERROR',
};

// Reducer function
const authReducer = (state, action) => {
  switch (action.type) {
    case AuthActionTypes.SET_LOADING:
      return {
        ...state,
        isLoading: action.payload,
      };
    case AuthActionTypes.LOGIN_SUCCESS:
      return {
        ...state,
        isLoading: false,
        isAuthenticated: true,
        user: action.payload.user,
        token: action.payload.token,
        error: null,
      };
    case AuthActionTypes.LOGIN_FAILURE:
      return {
        ...state,
        isLoading: false,
        isAuthenticated: false,
        user: null,
        token: null,
        error: action.payload,
      };
    case AuthActionTypes.LOGOUT:
      return {
        ...initialState,
        isLoading: false,
      };
    case AuthActionTypes.SET_USER:
      return {
        ...state,
        user: action.payload,
      };
    case AuthActionTypes.SET_BIOMETRIC:
      return {
        ...state,
        biometricEnabled: action.payload,
      };
    case AuthActionTypes.CLEAR_ERROR:
      return {
        ...state,
        error: null,
      };
    default:
      return state;
  }
};

// Create context
const AuthContext = createContext(null);

// Auth Provider component
export const AuthProvider = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize auth state on app start
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      dispatch({ type: AuthActionTypes.SET_LOADING, payload: true });

      // Check for stored token
      const token = await AsyncStorage.getItem('userToken');
      const userStr = await AsyncStorage.getItem('userData');
      const biometricEnabled = await AsyncStorage.getItem('biometricEnabled');

      if (token && userStr) {
        const user = JSON.parse(userStr);
        
        // Verify token validity
        const isValid = await AuthService.verifyToken(token);
        
        if (isValid) {
          dispatch({
            type: AuthActionTypes.LOGIN_SUCCESS,
            payload: { user, token },
          });
          
          dispatch({
            type: AuthActionTypes.SET_BIOMETRIC,
            payload: biometricEnabled === 'true',
          });
        } else {
          await logout();
        }
      }
    } catch (error) {
      console.error('Auth initialization error:', error);
      await logout();
    } finally {
      dispatch({ type: AuthActionTypes.SET_LOADING, payload: false });
    }
  };

  const login = async (email, password, rememberMe = false) => {
    try {
      dispatch({ type: AuthActionTypes.SET_LOADING, payload: true });
      dispatch({ type: AuthActionTypes.CLEAR_ERROR });

      const response = await AuthService.login(email, password);
      
      if (response.success) {
        const { user, token } = response.data;

        // Store credentials
        await AsyncStorage.setItem('userToken', token);
        await AsyncStorage.setItem('userData', JSON.stringify(user));
        
        if (rememberMe) {
          await AsyncStorage.setItem('rememberUser', 'true');
        }

        dispatch({
          type: AuthActionTypes.LOGIN_SUCCESS,
          payload: { user, token },
        });

        return { success: true };
      } else {
        dispatch({
          type: AuthActionTypes.LOGIN_FAILURE,
          payload: response.error || 'Login failed',
        });
        return { success: false, error: response.error };
      }
    } catch (error) {
      const errorMessage = error.message || 'Network error';
      dispatch({
        type: AuthActionTypes.LOGIN_FAILURE,
        payload: errorMessage,
      });
      return { success: false, error: errorMessage };
    }
  };

  const loginWithBiometric = async () => {
    try {
      const isAvailable = await BiometricService.isAvailable();
      
      if (!isAvailable) {
        Alert.alert('Biometric Not Available', 'Biometric authentication is not available on this device.');
        return { success: false };
      }

      const biometricResult = await BiometricService.authenticate();
      
      if (biometricResult.success) {
        // Retrieve stored credentials
        const token = await AsyncStorage.getItem('userToken');
        const userStr = await AsyncStorage.getItem('userData');
        
        if (token && userStr) {
          const user = JSON.parse(userStr);
          
          dispatch({
            type: AuthActionTypes.LOGIN_SUCCESS,
            payload: { user, token },
          });
          
          return { success: true };
        }
      }
      
      return { success: false, error: 'Biometric authentication failed' };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const register = async (userData) => {
    try {
      dispatch({ type: AuthActionTypes.SET_LOADING, payload: true });
      dispatch({ type: AuthActionTypes.CLEAR_ERROR });

      const response = await AuthService.register(userData);
      
      if (response.success) {
        const { user, token } = response.data;

        // Store credentials
        await AsyncStorage.setItem('userToken', token);
        await AsyncStorage.setItem('userData', JSON.stringify(user));

        dispatch({
          type: AuthActionTypes.LOGIN_SUCCESS,
          payload: { user, token },
        });

        return { success: true };
      } else {
        dispatch({
          type: AuthActionTypes.LOGIN_FAILURE,
          payload: response.error || 'Registration failed',
        });
        return { success: false, error: response.error };
      }
    } catch (error) {
      const errorMessage = error.message || 'Network error';
      dispatch({
        type: AuthActionTypes.LOGIN_FAILURE,
        payload: errorMessage,
      });
      return { success: false, error: errorMessage };
    }
  };

  const logout = async () => {
    try {
      // Clear stored data
      await AsyncStorage.multiRemove([
        'userToken',
        'userData',
        'rememberUser',
      ]);

      // Call logout API
      if (state.token) {
        await AuthService.logout(state.token);
      }

      dispatch({ type: AuthActionTypes.LOGOUT });
    } catch (error) {
      console.error('Logout error:', error);
      dispatch({ type: AuthActionTypes.LOGOUT });
    }
  };

  const updateProfile = async (profileData) => {
    try {
      const response = await AuthService.updateProfile(state.token, profileData);
      
      if (response.success) {
        const updatedUser = { ...state.user, ...response.data };
        await AsyncStorage.setItem('userData', JSON.stringify(updatedUser));
        
        dispatch({
          type: AuthActionTypes.SET_USER,
          payload: updatedUser,
        });
        
        return { success: true };
      }
      
      return { success: false, error: response.error };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const enableBiometric = async () => {
    try {
      const isAvailable = await BiometricService.isAvailable();
      
      if (!isAvailable) {
        Alert.alert('Biometric Not Available', 'Biometric authentication is not available on this device.');
        return { success: false };
      }

      const result = await BiometricService.authenticate();
      
      if (result.success) {
        await AsyncStorage.setItem('biometricEnabled', 'true');
        dispatch({ type: AuthActionTypes.SET_BIOMETRIC, payload: true });
        return { success: true };
      }
      
      return { success: false, error: 'Biometric setup failed' };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const disableBiometric = async () => {
    try {
      await AsyncStorage.setItem('biometricEnabled', 'false');
      dispatch({ type: AuthActionTypes.SET_BIOMETRIC, payload: false });
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  // Context value
  const value = {
    ...state,
    login,
    loginWithBiometric,
    register,
    logout,
    updateProfile,
    enableBiometric,
    disableBiometric,
    clearError: () => dispatch({ type: AuthActionTypes.CLEAR_ERROR }),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;