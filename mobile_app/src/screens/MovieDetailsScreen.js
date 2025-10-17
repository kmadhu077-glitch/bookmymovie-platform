import React, {useEffect} from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import LinearGradient from 'react-native-linear-gradient';
import {useBooking} from '../context/BookingContext';

const {width, height} = Dimensions.get('window');

const MovieDetailsScreen = ({navigation, route}) => {
  const {movie} = route.params;
  const {fetchTheaters} = useBooking();

  useEffect(() => {
    fetchTheaters(movie.id);
  }, [movie.id]);

  const handleBookNow = () => {
    navigation.navigate('SeatSelection', {movie});
  };

  return (
    <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
      {/* Movie Poster & Header */}
      <View style={styles.posterContainer}>
        <Image
          source={{uri: movie.poster_url}}
          style={styles.posterImage}
          resizeMode="cover"
        />
        <LinearGradient
          colors={['transparent', 'rgba(0,0,0,0.8)']}
          style={styles.posterOverlay}>
          <View style={styles.movieHeader}>
            <Text style={styles.movieTitle}>{movie.title}</Text>
            <View style={styles.movieMeta}>
              <View style={styles.ratingContainer}>
                <Icon name="star" size={20} color="#fbbf24" />
                <Text style={styles.rating}>{movie.rating}</Text>
              </View>
              <Text style={styles.genre}>{movie.genre}</Text>
              <Text style={styles.duration}>{movie.duration} min</Text>
            </View>
          </View>
        </LinearGradient>
      </View>

      {/* Movie Info */}
      <View style={styles.infoSection}>
        <Text style={styles.sectionTitle}>Synopsis</Text>
        <Text style={styles.description}>
          {movie.description || 'Experience an incredible cinematic journey with stunning visuals and compelling storytelling. This movie promises to deliver entertainment that will keep you on the edge of your seat from start to finish.'}
        </Text>

        <View style={styles.detailsGrid}>
          <View style={styles.detailItem}>
            <Icon name="calendar-today" size={20} color="#4f46e5" />
            <Text style={styles.detailText}>Release Date</Text>
            <Text style={styles.detailValue}>
              {movie.release_date ? new Date(movie.release_date).toLocaleDateString() : 'TBA'}
            </Text>
          </View>
          <View style={styles.detailItem}>
            <Icon name="category" size={20} color="#4f46e5" />
            <Text style={styles.detailText}>Genre</Text>
            <Text style={styles.detailValue}>{movie.genre}</Text>
          </View>
          <View style={styles.detailItem}>
            <Icon name="access-time" size={20} color="#4f46e5" />
            <Text style={styles.detailText}>Duration</Text>
            <Text style={styles.detailValue}>{movie.duration} mins</Text>
          </View>
          <View style={styles.detailItem}>
            <Icon name="star-rate" size={20} color="#4f46e5" />
            <Text style={styles.detailText}>Rating</Text>
            <Text style={styles.detailValue}>{movie.rating}/10</Text>
          </View>
        </View>
      </View>

      {/* Book Now Button */}
      <View style={styles.bookingSection}>
        <TouchableOpacity style={styles.bookButton} onPress={handleBookNow}>
          <LinearGradient
            colors={['#4f46e5', '#7c3aed']}
            style={styles.bookButtonGradient}>
            <Icon name="event-seat" size={24} color="white" />
            <Text style={styles.bookButtonText}>Book Tickets</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

// SeatSelectionScreen
export const SeatSelectionScreen = ({navigation, route}) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Select Seats</Text>
      <Text style={styles.subtitle}>Choose your preferred seats</Text>
      <TouchableOpacity 
        style={styles.button}
        onPress={() => navigation.navigate('Payment')}>
        <Text style={styles.buttonText}>Proceed to Payment</Text>
      </TouchableOpacity>
    </View>
  );
};

// PaymentScreen
export const PaymentScreen = ({navigation}) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Payment</Text>
      <Text style={styles.subtitle}>Complete your booking</Text>
      <TouchableOpacity 
        style={styles.button}
        onPress={() => navigation.navigate('BookingConfirmation')}>
        <Text style={styles.buttonText}>Pay Now</Text>
      </TouchableOpacity>
    </View>
  );
};

// BookingConfirmationScreen
export const BookingConfirmationScreen = ({navigation}) => {
  return (
    <View style={styles.container}>
      <Icon name="check-circle" size={64} color="#10b981" />
      <Text style={styles.title}>Booking Confirmed!</Text>
      <Text style={styles.subtitle}>Your tickets have been booked successfully</Text>
      <TouchableOpacity 
        style={styles.button}
        onPress={() => navigation.navigate('MainTabs')}>
        <Text style={styles.buttonText}>Go to Home</Text>
      </TouchableOpacity>
    </View>
  );
};

// ProfileScreen
export const ProfileScreen = ({navigation}) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Profile</Text>
      <Text style={styles.subtitle}>Manage your account</Text>
    </View>
  );
};

// BookingsScreen
export const BookingsScreen = ({navigation}) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>My Bookings</Text>
      <Text style={styles.subtitle}>View your booking history</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  posterContainer: {
    height: height * 0.5,
    position: 'relative',
  },
  posterImage: {
    width: '100%',
    height: '100%',
  },
  posterOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '50%',
    justifyContent: 'flex-end',
  },
  movieHeader: {
    padding: 20,
  },
  movieTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 12,
  },
  movieMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 12,
    marginBottom: 8,
  },
  rating: {
    fontSize: 14,
    color: 'white',
    marginLeft: 4,
    fontWeight: '600',
  },
  genre: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 12,
    marginBottom: 8,
  },
  duration: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginBottom: 8,
  },
  infoSection: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 12,
  },
  description: {
    fontSize: 16,
    color: '#64748b',
    lineHeight: 24,
    marginBottom: 24,
  },
  detailsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 16,
  },
  detailItem: {
    width: (width - 56) / 2,
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  detailText: {
    fontSize: 12,
    color: '#64748b',
    marginTop: 8,
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 14,
    color: '#1e293b',
    fontWeight: '600',
  },
  bookingSection: {
    padding: 20,
    paddingBottom: 40,
  },
  bookButton: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  bookButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
    paddingHorizontal: 32,
  },
  bookButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
    marginLeft: 12,
  },
});

export default MovieDetailsScreen;