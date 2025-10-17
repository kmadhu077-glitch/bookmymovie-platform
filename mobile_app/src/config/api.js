/**
 * API Configuration
 * Centralized API endpoints and configuration
 */

import { Platform } from 'react-native';

// Base URL configuration
// For development, use your local machine's IP address or localhost
export const API_BASE_URL = __DEV__ 
  ? Platform.OS === 'android' 
    ? 'http://10.0.2.2:8016'  // Android emulator localhost
    : 'http://localhost:8016'  // iOS simulator localhost
  : 'https://api.bookmymovie.com'; // Production URL

// API Endpoints
export const API_ENDPOINTS = {
  // Authentication endpoints
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    LOGOUT: '/auth/logout',
    VERIFY: '/auth/verify',
    REFRESH: '/auth/refresh',
    FORGOT_PASSWORD: '/auth/forgot-password',
    RESET_PASSWORD: '/auth/reset-password',
  },

  // Movie endpoints
  MOVIES: {
    LIST: '/catalog/movies',
    DETAILS: (id) => `/catalog/movies/${id}`,
    SEARCH: '/catalog/movies/search',
    TRENDING: '/catalog/movies/trending',
    RECOMMENDATIONS: (userId) => `/ai-recommendations/user/${userId}`,
    GENRES: '/catalog/genres',
    RATINGS: (movieId) => `/catalog/movies/${movieId}/ratings`,
  },

  // Theater endpoints
  THEATERS: {
    LIST: '/multi-cinema/theaters',
    DETAILS: (id) => `/multi-cinema/theaters/${id}`,
    SEARCH: '/multi-cinema/theaters/search',
    NEARBY: '/multi-cinema/theaters/nearby',
    SHOWTIMES: '/multi-cinema/showtimes',
    SEATS: (showtimeId) => `/multi-cinema/showtimes/${showtimeId}/seats`,
  },

  // Booking endpoints
  BOOKINGS: {
    CREATE: '/booking/create',
    LIST: (userId) => `/booking/user/${userId}`,
    DETAILS: (id) => `/booking/${id}`,
    CANCEL: (id) => `/booking/${id}/cancel`,
    CONFIRM: (id) => `/booking/${id}/confirm`,
    HISTORY: (userId) => `/booking/user/${userId}/history`,
  },

  // Payment endpoints
  PAYMENTS: {
    PROCESS: '/payment/process',
    METHODS: (userId) => `/payment/methods/${userId}`,
    ADD_METHOD: '/payment/methods/add',
    REMOVE_METHOD: (id) => `/payment/methods/${id}`,
    HISTORY: (userId) => `/payment/history/${userId}`,
  },

  // User profile endpoints
  USERS: {
    PROFILE: (id) => `/users/${id}`,
    UPDATE_PROFILE: (id) => `/users/${id}`,
    PREFERENCES: (id) => `/users/${id}/preferences`,
    AVATAR: (id) => `/users/${id}/avatar`,
  },

  // Notification endpoints
  NOTIFICATIONS: {
    LIST: (userId) => `/notifications/user/${userId}`,
    MARK_READ: (id) => `/notifications/${id}/read`,
    REGISTER_TOKEN: '/notifications/register-token',
    UNREGISTER_TOKEN: '/notifications/unregister-token',
    PREFERENCES: (userId) => `/notifications/preferences/${userId}`,
  },

  // Social features endpoints
  SOCIAL: {
    REVIEWS: (movieId) => `/social/reviews/movie/${movieId}`,
    SUBMIT_REVIEW: '/social/reviews',
    UPDATE_REVIEW: (id) => `/social/reviews/${id}`,
    DELETE_REVIEW: (id) => `/social/reviews/${id}`,
    USER_REVIEWS: (userId) => `/social/reviews/user/${userId}`,
    FORUMS: '/social/forums',
    FORUM_POSTS: (forumId) => `/social/forums/${forumId}/posts`,
    CREATE_POST: '/social/forums/posts',
  },

  // Analytics endpoints
  ANALYTICS: {
    USER_BEHAVIOR: '/analytics/user-behavior',
    MOVIE_STATS: (movieId) => `/analytics/movies/${movieId}/stats`,
    THEATER_STATS: (theaterId) => `/analytics/theaters/${theaterId}/stats`,
  },

  // Dynamic pricing endpoints
  PRICING: {
    GET_PRICE: '/dynamic-pricing/calculate',
    PRICE_HISTORY: (movieId, theaterId) => `/dynamic-pricing/history/${movieId}/${theaterId}`,
  },

  // Security endpoints
  SECURITY: {
    REPORT_FRAUD: '/security/fraud/report',
    VERIFY_TRANSACTION: '/security/verify-transaction',
    SECURITY_LOGS: '/security/logs',
  },
};

// Request timeout configuration
export const REQUEST_TIMEOUT = {
  DEFAULT: 30000, // 30 seconds
  UPLOAD: 60000,  // 60 seconds for file uploads
  DOWNLOAD: 120000, // 2 minutes for downloads
};

// Cache configuration
export const CACHE_CONFIG = {
  // Cache durations in milliseconds
  MOVIES_LIST: 5 * 60 * 1000,     // 5 minutes
  MOVIE_DETAILS: 15 * 60 * 1000,  // 15 minutes
  THEATERS_LIST: 10 * 60 * 1000,  // 10 minutes
  USER_PROFILE: 30 * 60 * 1000,   // 30 minutes
  SHOWTIMES: 2 * 60 * 1000,       // 2 minutes
};

// API response status codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  INTERNAL_SERVER_ERROR: 500,
  SERVICE_UNAVAILABLE: 503,
};

// Error messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  SERVER_ERROR: 'Server error. Please try again later.',
  UNAUTHORIZED: 'Please log in to continue.',
  FORBIDDEN: 'You don\'t have permission to perform this action.',
  NOT_FOUND: 'Requested resource not found.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  UNKNOWN_ERROR: 'An unexpected error occurred.',
};

// Feature flags
export const FEATURES = {
  BIOMETRIC_AUTH: true,
  PUSH_NOTIFICATIONS: true,
  OFFLINE_MODE: true,
  SOCIAL_FEATURES: true,
  LOCATION_SERVICES: true,
  ANALYTICS_TRACKING: true,
  DYNAMIC_PRICING: true,
  AI_RECOMMENDATIONS: true,
};

// App configuration
export const APP_CONFIG = {
  APP_NAME: 'BookMyMovie',
  APP_VERSION: '1.0.0',
  MIN_PASSWORD_LENGTH: 8,
  MAX_REVIEW_LENGTH: 500,
  ITEMS_PER_PAGE: 20,
  MAX_FILE_SIZE: 5 * 1024 * 1024, // 5MB
  SUPPORTED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/jpg'],
};

export default {
  API_BASE_URL,
  API_ENDPOINTS,
  REQUEST_TIMEOUT,
  CACHE_CONFIG,
  HTTP_STATUS,
  ERROR_MESSAGES,
  FEATURES,
  APP_CONFIG,
};