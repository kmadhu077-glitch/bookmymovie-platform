import React, {createContext, useContext, useState, useEffect} from 'react';
import {useAuth} from './AuthContext';

const BookingContext = createContext();

export const useBooking = () => {
  const context = useContext(BookingContext);
  if (!context) {
    throw new Error('useBooking must be used within a BookingProvider');
  }
  return context;
};

export const BookingProvider = ({children}) => {
  const {token} = useAuth();
  const [movies, setMovies] = useState([]);
  const [theaters, setTheaters] = useState([]);
  const [currentBooking, setCurrentBooking] = useState({
    movie: null,
    theater: null,
    showtime: null,
    seats: [],
    totalAmount: 0,
  });
  const [userBookings, setUserBookings] = useState([]);

  // API Base URLs
  const CATALOG_API_BASE = 'http://127.0.0.1:8005/v1/catalog';
  const BOOKING_API_BASE = 'http://127.0.0.1:8007/v1/booking';
  const PAYMENT_API_BASE = 'http://127.0.0.1:8011/v1/payment';

  // Fetch movies from catalog service
  const fetchMovies = async () => {
    try {
      const response = await fetch(`${CATALOG_API_BASE}/movies`);
      const data = await response.json();
      
      if (response.ok) {
        setMovies(data.movies || []);
      } else {
        // Fallback mock data
        setMovies([
          {
            id: 'movie_1',
            title: 'Avengers: Endgame',
            genre: 'Action',
            duration: 181,
            rating: 8.4,
            poster_url: 'https://via.placeholder.com/300x450/6366f1/white?text=Avengers',
            description: 'After the devastating events of Infinity War, the universe is in ruins...',
            release_date: '2019-04-26',
          },
          {
            id: 'movie_2',
            title: 'Inception',
            genre: 'Sci-Fi',
            duration: 148,
            rating: 8.8,
            poster_url: 'https://via.placeholder.com/300x450/8b5cf6/white?text=Inception',
            description: 'A thief who steals corporate secrets through dream-sharing technology...',
            release_date: '2010-07-16',
          },
          {
            id: 'movie_3',
            title: 'The Dark Knight',
            genre: 'Action',
            duration: 152,
            rating: 9.0,
            poster_url: 'https://via.placeholder.com/300x450/ef4444/white?text=Dark+Knight',
            description: 'When the menace known as the Joker wreaks havoc on Gotham...',
            release_date: '2008-07-18',
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching movies:', error);
      // Use mock data as fallback
      setMovies([
        {
          id: 'movie_1',
          title: 'Avengers: Endgame',
          genre: 'Action',
          duration: 181,
          rating: 8.4,
          poster_url: 'https://via.placeholder.com/300x450/6366f1/white?text=Avengers',
          description: 'After the devastating events of Infinity War, the universe is in ruins...',
          release_date: '2019-04-26',
        },
      ]);
    }
  };

  // Fetch theaters
  const fetchTheaters = async (movieId) => {
    try {
      const response = await fetch(`${CATALOG_API_BASE}/theaters?movie_id=${movieId}`);
      const data = await response.json();
      
      if (response.ok) {
        setTheaters(data.theaters || []);
      } else {
        // Mock theaters data
        setTheaters([
          {
            id: 'theater_1',
            name: 'IMAX Downtown',
            location: 'Downtown Plaza',
            showtimes: ['10:00', '13:30', '17:00', '20:30'],
            price: 15.99,
          },
          {
            id: 'theater_2',
            name: 'Cinema Plus',
            location: 'Mall Center',
            showtimes: ['11:00', '14:00', '18:00', '21:00'],
            price: 12.50,
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching theaters:', error);
      // Mock fallback
      setTheaters([
        {
          id: 'theater_1',
          name: 'IMAX Downtown',
          location: 'Downtown Plaza',
          showtimes: ['10:00', '13:30', '17:00', '20:30'],
          price: 15.99,
        },
      ]);
    }
  };

  // Get available seats for a showtime
  const fetchAvailableSeats = async (theaterId, showtime) => {
    try {
      const response = await fetch(
        `${BOOKING_API_BASE}/seats?theater_id=${theaterId}&showtime=${showtime}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
      
      const data = await response.json();
      
      if (response.ok) {
        return data.available_seats || generateMockSeats();
      } else {
        return generateMockSeats();
      }
    } catch (error) {
      console.error('Error fetching seats:', error);
      return generateMockSeats();
    }
  };

  // Generate mock seat layout
  const generateMockSeats = () => {
    const rows = ['A', 'B', 'C', 'D', 'E', 'F'];
    const seatsPerRow = 10;
    const seats = [];

    rows.forEach(row => {
      for (let i = 1; i <= seatsPerRow; i++) {
        seats.push({
          id: `${row}${i}`,
          row: row,
          number: i,
          type: i <= 2 || i >= 9 ? 'premium' : 'regular',
          isAvailable: Math.random() > 0.3, // 70% availability
          price: i <= 2 || i >= 9 ? 18.99 : 12.99,
        });
      }
    });

    return seats;
  };

  // Book selected seats
  const bookSeats = async (bookingData) => {
    try {
      const response = await fetch(`${BOOKING_API_BASE}/book`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(bookingData),
      });

      const data = await response.json();

      if (response.ok) {
        return {success: true, bookingId: data.booking_id};
      } else {
        return {success: false, message: data.message || 'Booking failed'};
      }
    } catch (error) {
      console.error('Booking error:', error);
      // Mock success for demo
      return {success: true, bookingId: `BKG${Date.now()}`};
    }
  };

  // Process payment
  const processPayment = async (paymentData) => {
    try {
      const response = await fetch(`${PAYMENT_API_BASE}/process`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(paymentData),
      });

      const data = await response.json();

      if (response.ok) {
        return {success: true, transactionId: data.transaction_id};
      } else {
        return {success: false, message: data.message || 'Payment failed'};
      }
    } catch (error) {
      console.error('Payment error:', error);
      // Mock success for demo
      return {success: true, transactionId: `TXN${Date.now()}`};
    }
  };

  // Fetch user bookings
  const fetchUserBookings = async () => {
    try {
      const response = await fetch(`${BOOKING_API_BASE}/user-bookings`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await response.json();

      if (response.ok) {
        setUserBookings(data.bookings || []);
      } else {
        // Mock bookings
        setUserBookings([
          {
            id: 'BKG001',
            movie_title: 'Avengers: Endgame',
            theater_name: 'IMAX Downtown',
            showtime: '2024-01-15T19:00:00Z',
            seats: ['A1', 'A2'],
            total_amount: 31.98,
            status: 'confirmed',
            booking_date: '2024-01-10T10:30:00Z',
          },
        ]);
      }
    } catch (error) {
      console.error('Error fetching bookings:', error);
      setUserBookings([]);
    }
  };

  // Update current booking details
  const updateCurrentBooking = (updates) => {
    setCurrentBooking(prev => ({...prev, ...updates}));
  };

  // Clear current booking
  const clearCurrentBooking = () => {
    setCurrentBooking({
      movie: null,
      theater: null,
      showtime: null,
      seats: [],
      totalAmount: 0,
    });
  };

  // Calculate total amount based on selected seats
  const calculateTotal = (seats) => {
    return seats.reduce((total, seat) => total + seat.price, 0);
  };

  // Get movie by ID
  const getMovieById = (id) => {
    return movies.find(movie => movie.id === id);
  };

  // Get theater by ID
  const getTheaterById = (id) => {
    return theaters.find(theater => theater.id === id);
  };

  useEffect(() => {
    fetchMovies();
  }, []);

  useEffect(() => {
    if (token) {
      fetchUserBookings();
    }
  }, [token]);

  const value = {
    movies,
    theaters,
    currentBooking,
    userBookings,
    fetchMovies,
    fetchTheaters,
    fetchAvailableSeats,
    bookSeats,
    processPayment,
    fetchUserBookings,
    updateCurrentBooking,
    clearCurrentBooking,
    calculateTotal,
    getMovieById,
    getTheaterById,
  };

  return (
    <BookingContext.Provider value={value}>
      {children}
    </BookingContext.Provider>
  );
};