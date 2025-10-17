import React from 'react';
import {View, Text, StyleSheet, TouchableOpacity} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useNavigation} from '@react-navigation/native';

const BookingConfirmationScreen = () => {
  const navigation = useNavigation();
  return (
    <View style={styles.container}>
      <Icon name="check-circle" size={64} color="#10b981" />
      <Text style={styles.title}>Booking Confirmed!</Text>
      <Text style={styles.subtitle}>Your tickets have been booked successfully</Text>
      <TouchableOpacity style={styles.button} onPress={() => navigation.navigate('Home')}>
        <Text style={styles.buttonText}>Go to Home</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f8fafc'},
  title: {fontSize: 24, fontWeight: 'bold', color: '#1e293b', marginBottom: 8, textAlign: 'center'},
  subtitle: {fontSize: 16, color: '#64748b', marginBottom: 32, textAlign: 'center'},
  button: {backgroundColor: '#4f46e5', paddingHorizontal: 32, paddingVertical: 16, borderRadius: 12},
  buttonText: {color: 'white', fontSize: 16, fontWeight: '600'},
});

export default BookingConfirmationScreen;