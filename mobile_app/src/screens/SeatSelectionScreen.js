import React, {useEffect, useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useBooking} from '../context/BookingContext';

const SeatSelectionScreen = ({navigation, route}) => {
  const {movie} = route.params;
  const {fetchTheaters, theaters, fetchAvailableSeats, updateCurrentBooking, currentBooking, calculateTotal} = useBooking();
  const [selectedTheater, setSelectedTheater] = useState(null);
  const [selectedShowtime, setSelectedShowtime] = useState(null);
  const [availableSeats, setAvailableSeats] = useState([]);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [loadingSeats, setLoadingSeats] = useState(false);

  useEffect(() => {
    fetchTheaters(movie.id);
  }, [movie.id]);

  useEffect(() => {
    if (selectedTheater && selectedShowtime) {
      loadSeats();
    }
  }, [selectedTheater, selectedShowtime]);

  const loadSeats = async () => {
    setLoadingSeats(true);
    const seats = await fetchAvailableSeats(selectedTheater.id, selectedShowtime);
    setAvailableSeats(seats);
    setLoadingSeats(false);
  };

  const toggleSeat = (seat) => {
    if (!seat.isAvailable) return;
    if (selectedSeats.some(s => s.id === seat.id)) {
      setSelectedSeats(selectedSeats.filter(s => s.id !== seat.id));
    } else {
      setSelectedSeats([...selectedSeats, seat]);
    }
  };

  const proceedToPayment = () => {
    updateCurrentBooking({
      movie,
      theater: selectedTheater,
      showtime: selectedShowtime,
      seats: selectedSeats,
      totalAmount: calculateTotal(selectedSeats),
    });
    navigation.navigate('Payment');
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Select Theater & Showtime</Text>
      <View style={styles.theaterList}>
        {theaters.map(theater => (
          <TouchableOpacity
            key={theater.id}
            style={[styles.theaterCard, selectedTheater?.id === theater.id && styles.selectedCard]}
            onPress={() => {
              setSelectedTheater(theater);
              setSelectedShowtime(null);
              setAvailableSeats([]);
              setSelectedSeats([]);
            }}>
            <Text style={styles.theaterName}>{theater.name}</Text>
            <Text style={styles.theaterLocation}>{theater.location}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {selectedTheater && (
        <View style={styles.showtimeList}>
          <Text style={styles.subHeader}>Showtimes</Text>
          <View style={styles.showtimeGrid}>
            {selectedTheater.showtimes.map(showtime => (
              <TouchableOpacity
                key={showtime}
                style={[styles.showtimeChip, selectedShowtime === showtime && styles.selectedChip]}
                onPress={() => {
                  setSelectedShowtime(showtime);
                  setAvailableSeats([]);
                  setSelectedSeats([]);
                }}>
                <Text style={styles.showtimeText}>{showtime}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      )}

      {selectedShowtime && (
        <View style={styles.seatSection}>
          <Text style={styles.subHeader}>Select Seats</Text>
          {loadingSeats ? (
            <ActivityIndicator size="large" color="#4f46e5" />
          ) : (
            <View style={styles.seatGrid}>
              {availableSeats.map(seat => (
                <TouchableOpacity
                  key={seat.id}
                  style={[styles.seat,
                    seat.isAvailable ? (selectedSeats.some(s => s.id === seat.id) ? styles.selectedSeat : styles.availableSeat) : styles.unavailableSeat
                  ]}
                  onPress={() => toggleSeat(seat)}>
                  <Text style={styles.seatText}>{seat.id}</Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>
      )}

      {selectedSeats.length > 0 && (
        <View style={styles.summarySection}>
          <Text style={styles.summaryText}>Selected Seats: {selectedSeats.map(s => s.id).join(', ')}</Text>
          <Text style={styles.summaryText}>Total: ₹{calculateTotal(selectedSeats).toFixed(2)}</Text>
          <TouchableOpacity style={styles.payButton} onPress={proceedToPayment}>
            <Text style={styles.payButtonText}>Proceed to Payment</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#f8fafc', padding: 16},
  header: {fontSize: 22, fontWeight: 'bold', color: '#1e293b', marginBottom: 16},
  theaterList: {flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 16},
  theaterCard: {backgroundColor: 'white', borderRadius: 12, padding: 16, marginRight: 12, marginBottom: 12, elevation: 2},
  selectedCard: {borderColor: '#4f46e5', borderWidth: 2},
  theaterName: {fontSize: 16, fontWeight: '600', color: '#4f46e5'},
  theaterLocation: {fontSize: 12, color: '#64748b'},
  showtimeList: {marginBottom: 16},
  subHeader: {fontSize: 18, fontWeight: 'bold', color: '#1e293b', marginBottom: 8},
  showtimeGrid: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
  showtimeChip: {backgroundColor: '#e0e7ff', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 8, marginRight: 8, marginBottom: 8},
  selectedChip: {backgroundColor: '#4f46e5'},
  showtimeText: {color: '#1e293b', fontWeight: '500'},
  seatSection: {marginBottom: 16},
  seatGrid: {flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8},
  seat: {width: 40, height: 40, borderRadius: 8, justifyContent: 'center', alignItems: 'center', margin: 2},
  seatText: {fontSize: 12, fontWeight: '600'},
  availableSeat: {backgroundColor: '#e0e7ff'},
  selectedSeat: {backgroundColor: '#4f46e5'},
  unavailableSeat: {backgroundColor: '#d1d5db'},
  summarySection: {marginTop: 16, alignItems: 'center'},
  summaryText: {fontSize: 16, color: '#1e293b', marginBottom: 8},
  payButton: {backgroundColor: '#4f46e5', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 32, marginTop: 8},
  payButtonText: {color: 'white', fontSize: 16, fontWeight: '600'},
});

export default SeatSelectionScreen;