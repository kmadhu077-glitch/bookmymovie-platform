/**
 * API Service
 * Centralized API communication handler
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, API_ENDPOINTS } from '../config/api';

class ApiService {
  constructor() {
    // Create axios instance with default configuration
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        try {
          const token = await AsyncStorage.getItem('userToken');
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } catch (error) {
          console.error('Error getting token:', error);
        }
        
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
      },
      async (error) => {
        const { response } = error;
        
        console.error(`API Error: ${response?.status} ${error.config?.url}`, error.message);

        // Handle authentication errors
        if (response?.status === 401) {
          // Token expired or invalid
          await AsyncStorage.multiRemove(['userToken', 'userData']);
          // Navigate to login screen - you might want to use navigation service here
        }

        // Handle network errors
        if (!response) {
          return Promise.reject({
            message: 'Network error. Please check your connection.',
            code: 'NETWORK_ERROR'
          });
        }

        // Handle server errors
        if (response.status >= 500) {
          return Promise.reject({
            message: 'Server error. Please try again later.',
            code: 'SERVER_ERROR'
          });
        }

        // Return formatted error
        return Promise.reject({
          message: response.data?.message || error.message || 'An error occurred',
          code: response.data?.code || 'API_ERROR',
          status: response.status
        });
      }
    );
  }

  // Authentication endpoints
  async login(email, password) {
    try {
      const response = await this.api.post(API_ENDPOINTS.AUTH.LOGIN, {
        email,
        password,
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async register(userData) {
    try {
      const response = await this.api.post(API_ENDPOINTS.AUTH.REGISTER, userData);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async verifyToken(token) {
    try {
      const response = await this.api.get(API_ENDPOINTS.AUTH.VERIFY, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  async logout() {
    try {
      await this.api.post(API_ENDPOINTS.AUTH.LOGOUT);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Movie endpoints
  async getMovies(params = {}) {
    try {
      const response = await this.api.get(API_ENDPOINTS.MOVIES.LIST, { params });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getMovieDetails(movieId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.MOVIES.DETAILS(movieId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getMovieRecommendations(userId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.MOVIES.RECOMMENDATIONS(userId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Theater endpoints
  async getTheaters(params = {}) {
    try {
      const response = await this.api.get(API_ENDPOINTS.THEATERS.LIST, { params });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getTheaterDetails(theaterId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.THEATERS.DETAILS(theaterId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getShowtimes(movieId, theaterId, date) {
    try {
      const response = await this.api.get(API_ENDPOINTS.THEATERS.SHOWTIMES, {
        params: { movie_id: movieId, theater_id: theaterId, date }
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Booking endpoints
  async createBooking(bookingData) {
    try {
      const response = await this.api.post(API_ENDPOINTS.BOOKINGS.CREATE, bookingData);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getBookings(userId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.BOOKINGS.LIST(userId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getBookingDetails(bookingId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.BOOKINGS.DETAILS(bookingId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async cancelBooking(bookingId) {
    try {
      const response = await this.api.delete(API_ENDPOINTS.BOOKINGS.CANCEL(bookingId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Payment endpoints
  async processPayment(paymentData) {
    try {
      const response = await this.api.post(API_ENDPOINTS.PAYMENTS.PROCESS, paymentData);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getPaymentMethods(userId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.PAYMENTS.METHODS(userId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // User profile endpoints
  async getUserProfile(userId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.USERS.PROFILE(userId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async updateUserProfile(userId, profileData) {
    try {
      const response = await this.api.put(API_ENDPOINTS.USERS.PROFILE(userId), profileData);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Notification endpoints
  async registerPushToken(token, userId) {
    try {
      const response = await this.api.post(API_ENDPOINTS.NOTIFICATIONS.REGISTER_TOKEN, {
        token,
        user_id: userId,
        platform: Platform.OS
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async getNotifications(userId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.NOTIFICATIONS.LIST(userId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Social features endpoints
  async getMovieReviews(movieId) {
    try {
      const response = await this.api.get(API_ENDPOINTS.SOCIAL.REVIEWS(movieId));
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  async submitMovieReview(reviewData) {
    try {
      const response = await this.api.post(API_ENDPOINTS.SOCIAL.SUBMIT_REVIEW, reviewData);
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  // Generic request method
  async request(method, url, data = null, config = {}) {
    try {
      const response = await this.api.request({
        method,
        url,
        data,
        ...config
      });
      return { success: true, data: response.data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
}

// Create and export singleton instance
export const apiService = new ApiService();
export default apiService;