import React, {createContext, useContext, useState, useEffect} from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({children}) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // API Base URLs
  const AUTH_API_BASE = 'http://127.0.0.1:8006/v1/auth';
  const MOBILE_API_BASE = 'http://127.0.0.1:8013/v1/mobile';

  // Check authentication status on app start
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const storedToken = await AsyncStorage.getItem('userToken');
      const storedUser = await AsyncStorage.getItem('userData');
      
      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Error checking auth status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Login with email/password
  const login = async (email, password) => {
    try {
      const response = await fetch(`${AUTH_API_BASE}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({email, password}),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        const userData = {
          id: data.user_id,
          email: email,
          name: data.name || email.split('@')[0],
        };

        await AsyncStorage.setItem('userToken', data.token);
        await AsyncStorage.setItem('userData', JSON.stringify(userData));
        
        setToken(data.token);
        setUser(userData);
        
        return {success: true};
      } else {
        return {success: false, message: data.message || 'Login failed'};
      }
    } catch (error) {
      console.error('Login error:', error);
      return {success: false, message: 'Network error. Please try again.'};
    }
  };

  // Register new user
  const register = async (email, password, name, phone) => {
    try {
      const response = await fetch(`${AUTH_API_BASE}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
          name,
          phone,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Auto-login after successful registration
        return await login(email, password);
      } else {
        return {success: false, message: data.message || 'Registration failed'};
      }
    } catch (error) {
      console.error('Registration error:', error);
      return {success: false, message: 'Network error. Please try again.'};
    }
  };

  // Login with mobile number and OTP
  const requestMobileOTP = async (mobileNumber, countryCode = '+91') => {
    try {
      const response = await fetch(`${MOBILE_API_BASE}/request-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mobile_number: countryCode + mobileNumber,
          country_code: countryCode,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        return {
          success: true,
          sessionId: data.session_id,
          message: 'OTP sent successfully',
        };
      } else {
        return {success: false, message: data.message || 'Failed to send OTP'};
      }
    } catch (error) {
      console.error('OTP request error:', error);
      return {success: false, message: 'Network error. Please try again.'};
    }
  };

  const verifyMobileOTP = async (sessionId, otp, mobileNumber) => {
    try {
      const response = await fetch(`${MOBILE_API_BASE}/verify-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          otp: otp,
          mobile_number: mobileNumber,
        }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        const userData = {
          id: data.user_id,
          mobile: mobileNumber,
          name: `User ${mobileNumber.slice(-4)}`,
        };

        await AsyncStorage.setItem('userToken', data.token);
        await AsyncStorage.setItem('userData', JSON.stringify(userData));
        
        setToken(data.token);
        setUser(userData);
        
        return {success: true};
      } else {
        return {success: false, message: data.message || 'OTP verification failed'};
      }
    } catch (error) {
      console.error('OTP verification error:', error);
      return {success: false, message: 'Network error. Please try again.'};
    }
  };

  // Logout
  const logout = async () => {
    try {
      await AsyncStorage.removeItem('userToken');
      await AsyncStorage.removeItem('userData');
      setToken(null);
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  // Update user profile
  const updateProfile = async (profileData) => {
    try {
      // Here you would typically make an API call to update the profile
      const updatedUser = {...user, ...profileData};
      await AsyncStorage.setItem('userData', JSON.stringify(updatedUser));
      setUser(updatedUser);
      return {success: true};
    } catch (error) {
      console.error('Profile update error:', error);
      return {success: false, message: 'Failed to update profile'};
    }
  };

  const value = {
    user,
    token,
    isLoading,
    isAuthenticated: !!token,
    login,
    register,
    requestMobileOTP,
    verifyMobileOTP,
    logout,
    updateProfile,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};