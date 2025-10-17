import React, {useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useBooking} from '../context/BookingContext';

const PaymentScreen = ({navigation}) => {
  const {currentBooking, processPayment, clearCurrentBooking} = useBooking();
  const [paymentType, setPaymentType] = useState('credit_card');
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [cardCVV, setCardCVV] = useState('');
  const [upiId, setUpiId] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handlePayment = async () => {
    setIsLoading(true);
    let paymentData = {
      booking_id: currentBooking.bookingId || 'demo',
      amount: currentBooking.totalAmount,
      payment_type: paymentType,
    };
    if (paymentType === 'credit_card' || paymentType === 'debit_card') {
      paymentData.card_number = cardNumber;
      paymentData.card_expiry = cardExpiry;
      paymentData.card_cvv = cardCVV;
    } else {
      paymentData.upi_id = upiId;
    }
    const result = await processPayment(paymentData);
    setIsLoading(false);
    if (result.success) {
      clearCurrentBooking();
      navigation.navigate('BookingConfirmation');
    } else {
      Alert.alert('Payment Failed', result.message);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Payment</Text>
      <Text style={styles.amount}>Amount: ₹{currentBooking.totalAmount?.toFixed(2) || '0.00'}</Text>
      <View style={styles.paymentTypeRow}>
        <TouchableOpacity onPress={() => setPaymentType('credit_card')} style={[styles.paymentTypeChip, paymentType === 'credit_card' && styles.selectedChip]}>
          <Icon name="credit-card" size={20} color={paymentType === 'credit_card' ? '#4f46e5' : '#64748b'} />
          <Text style={styles.paymentTypeText}>Credit Card</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setPaymentType('debit_card')} style={[styles.paymentTypeChip, paymentType === 'debit_card' && styles.selectedChip]}>
          <Icon name="credit-card" size={20} color={paymentType === 'debit_card' ? '#4f46e5' : '#64748b'} />
          <Text style={styles.paymentTypeText}>Debit Card</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setPaymentType('upi')} style={[styles.paymentTypeChip, paymentType === 'upi' && styles.selectedChip]}>
          <Icon name="mobile-friendly" size={20} color={paymentType === 'upi' ? '#4f46e5' : '#64748b'} />
          <Text style={styles.paymentTypeText}>UPI</Text>
        </TouchableOpacity>
      </View>
      {paymentType === 'credit_card' || paymentType === 'debit_card' ? (
        <View style={styles.formSection}>
          <TextInput style={styles.input} placeholder="Card Number" value={cardNumber} onChangeText={setCardNumber} keyboardType="numeric" maxLength={16} />
          <View style={styles.row}>
            <TextInput style={[styles.input, {flex: 1, marginRight: 8}]} placeholder="MM/YY" value={cardExpiry} onChangeText={setCardExpiry} maxLength={5} />
            <TextInput style={[styles.input, {flex: 1}]} placeholder="CVV" value={cardCVV} onChangeText={setCardCVV} keyboardType="numeric" maxLength={3} />
          </View>
        </View>
      ) : (
        <View style={styles.formSection}>
          <TextInput style={styles.input} placeholder="UPI ID" value={upiId} onChangeText={setUpiId} autoCapitalize="none" />
        </View>
      )}
      <TouchableOpacity style={styles.payButton} onPress={handlePayment} disabled={isLoading}>
        {isLoading ? <ActivityIndicator color="white" /> : <Text style={styles.payButtonText}>Pay Now</Text>}
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#f8fafc', padding: 16},
  header: {fontSize: 22, fontWeight: 'bold', color: '#1e293b', marginBottom: 16},
  amount: {fontSize: 18, color: '#4f46e5', marginBottom: 16},
  paymentTypeRow: {flexDirection: 'row', gap: 8, marginBottom: 16},
  paymentTypeChip: {flexDirection: 'row', alignItems: 'center', backgroundColor: '#e0e7ff', borderRadius: 20, paddingHorizontal: 16, paddingVertical: 8, marginRight: 8},
  selectedChip: {backgroundColor: '#4f46e5'},
  paymentTypeText: {marginLeft: 8, color: '#1e293b', fontWeight: '500'},
  formSection: {marginBottom: 16},
  input: {backgroundColor: 'white', borderRadius: 8, padding: 12, marginBottom: 8, fontSize: 16, borderWidth: 1, borderColor: '#e2e8f0'},
  row: {flexDirection: 'row'},
  payButton: {backgroundColor: '#4f46e5', borderRadius: 12, paddingVertical: 14, alignItems: 'center'},
  payButtonText: {color: 'white', fontSize: 16, fontWeight: '600'},
});

export default PaymentScreen;