import React, {useEffect, useState} from 'react';
import {View, Text, StyleSheet, ScrollView, TouchableOpacity, TextInput, Alert} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useAuth} from '../context/AuthContext';

const ProfileScreen = () => {
  const {user, updateProfile, logout} = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');

  useEffect(() => {
    setName(user?.name || '');
    setEmail(user?.email || '');
    setPhone(user?.phone || '');
  }, [user]);

  const handleSave = async () => {
    const result = await updateProfile({name, email, phone});
    if (result.success) {
      Alert.alert('Success', 'Profile updated successfully!');
      setEditing(false);
    } else {
      Alert.alert('Error', result.message);
    }
  };

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Icon name="person" size={64} color="#4f46e5" />
        <Text style={styles.title}>Profile</Text>
      </View>
      <View style={styles.formSection}>
        <Text style={styles.label}>Name</Text>
        <TextInput style={styles.input} value={name} onChangeText={setName} editable={editing} />
        <Text style={styles.label}>Email</Text>
        <TextInput style={styles.input} value={email} onChangeText={setEmail} editable={editing} />
        <Text style={styles.label}>Phone</Text>
        <TextInput style={styles.input} value={phone} onChangeText={setPhone} editable={editing} />
      </View>
      <View style={styles.buttonRow}>
        {editing ? (
          <>
            <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
              <Text style={styles.buttonText}>Save</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.cancelButton} onPress={() => setEditing(false)}>
              <Text style={styles.buttonText}>Cancel</Text>
            </TouchableOpacity>
          </>
        ) : (
          <TouchableOpacity style={styles.editButton} onPress={() => setEditing(true)}>
            <Text style={styles.buttonText}>Edit Profile</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity style={styles.logoutButton} onPress={logout}>
          <Text style={styles.buttonText}>Logout</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#f8fafc', padding: 16},
  header: {alignItems: 'center', marginBottom: 24},
  title: {fontSize: 24, fontWeight: 'bold', color: '#1e293b', marginTop: 8},
  formSection: {marginBottom: 24},
  label: {fontSize: 14, color: '#64748b', marginBottom: 4},
  input: {backgroundColor: 'white', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 16, borderWidth: 1, borderColor: '#e2e8f0'},
  buttonRow: {flexDirection: 'row', justifyContent: 'space-between'},
  editButton: {backgroundColor: '#4f46e5', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 24, marginRight: 8},
  saveButton: {backgroundColor: '#10b981', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 24, marginRight: 8},
  cancelButton: {backgroundColor: '#64748b', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 24, marginRight: 8},
  logoutButton: {backgroundColor: '#ef4444', borderRadius: 12, paddingVertical: 14, paddingHorizontal: 24},
  buttonText: {color: 'white', fontSize: 16, fontWeight: '600'},
});

export default ProfileScreen;