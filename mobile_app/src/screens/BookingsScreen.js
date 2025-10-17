import React, {useEffect} from 'react';
import {View, Text, StyleSheet, FlatList} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useBooking} from '../context/BookingContext';

const BookingsScreen = () => {
  const {userBookings, fetchUserBookings} = useBooking();

  useEffect(() => {
    fetchUserBookings();
  }, []);

  const renderBooking = ({item: booking}) => (
    <View style={styles.bookingCard}>
      <Text style={styles.movieTitle}>{booking.movie_title}</Text>
      <Text style={styles.theater}>{booking.theater_name}</Text>
      <Text style={styles.showtime}>{new Date(booking.showtime).toLocaleString()}</Text>
      <Text style={styles.seats}>Seats: {booking.seats.join(', ')}</Text>
      <Text style={styles.amount}>Amount: ₹{booking.total_amount?.toFixed(2)}</Text>
      <Text style={[styles.status, booking.status === 'confirmed' ? styles.confirmed : styles.completed]}>{booking.status.toUpperCase()}</Text>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.header}>My Bookings</Text>
      <FlatList
        data={userBookings}
        renderItem={renderBooking}
        keyExtractor={item => item.id}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Icon name="movie" size={48} color="#94a3b8" />
            <Text style={styles.emptyText}>No bookings found</Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#f8fafc', padding: 16},
  header: {fontSize: 22, fontWeight: 'bold', color: '#1e293b', marginBottom: 16},
  bookingCard: {backgroundColor: 'white', borderRadius: 12, padding: 16, marginBottom: 12, elevation: 2},
  movieTitle: {fontSize: 16, fontWeight: 'bold', color: '#4f46e5'},
  theater: {fontSize: 14, color: '#64748b'},
  showtime: {fontSize: 12, color: '#64748b'},
  seats: {fontSize: 12, color: '#1e293b'},
  amount: {fontSize: 14, color: '#10b981', fontWeight: '600'},
  status: {fontSize: 12, fontWeight: 'bold', marginTop: 8, padding: 4, borderRadius: 8, textAlign: 'center'},
  confirmed: {backgroundColor: '#d1fae5', color: '#065f46'},
  completed: {backgroundColor: '#e0e7ff', color: '#3730a3'},
  emptyState: {alignItems: 'center', paddingVertical: 60},
  emptyText: {fontSize: 18, fontWeight: '600', color: '#64748b', marginTop: 16},
});

export default BookingsScreen;