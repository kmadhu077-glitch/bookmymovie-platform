import React, {useState} from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import LinearGradient from 'react-native-linear-gradient';
import {useAuth} from '../context/AuthContext';

const LoginScreen = ({navigation}) => {
  const [loginType, setLoginType] = useState('email'); // 'email' or 'mobile'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mobileNumber, setMobileNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otpSessionId, setOtpSessionId] = useState(null);

  const {login, requestMobileOTP, verifyMobileOTP} = useAuth();

  const handleEmailLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please enter email and password');
      return;
    }

    setIsLoading(true);
    const result = await login(email, password);
    setIsLoading(false);

    if (result.success) {
      // Navigation will be handled by the root navigator
    } else {
      Alert.alert('Login Failed', result.message);
    }
  };

  const handleRequestOTP = async () => {
    if (!mobileNumber || mobileNumber.length < 10) {
      Alert.alert('Error', 'Please enter a valid mobile number');
      return;
    }

    setIsLoading(true);
    const result = await requestMobileOTP(mobileNumber);
    setIsLoading(false);

    if (result.success) {
      setOtpSent(true);
      setOtpSessionId(result.sessionId);
      Alert.alert('Success', 'OTP sent to your mobile number');
    } else {
      Alert.alert('Error', result.message);
    }
  };

  const handleVerifyOTP = async () => {
    if (!otp || otp.length !== 6) {
      Alert.alert('Error', 'Please enter a valid 6-digit OTP');
      return;
    }

    setIsLoading(true);
    const result = await verifyMobileOTP(otpSessionId, otp, '+91' + mobileNumber);
    setIsLoading(false);

    if (result.success) {
      // Navigation will be handled by the root navigator
    } else {
      Alert.alert('Verification Failed', result.message);
    }
  };

  const resetMobileLogin = () => {
    setOtpSent(false);
    setOtp('');
    setOtpSessionId(null);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}>
      <LinearGradient
        colors={['#4f46e5', '#7c3aed']}
        style={styles.gradient}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled">
          
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.welcomeText}>Welcome Back!</Text>
            <Text style={styles.subtitleText}>Sign in to continue</Text>
          </View>

          {/* Login Type Selector */}
          <View style={styles.tabContainer}>
            <TouchableOpacity
              style={[styles.tab, loginType === 'email' && styles.activeTab]}
              onPress={() => setLoginType('email')}>
              <Icon name="email" size={20} color={loginType === 'email' ? '#4f46e5' : '#64748b'} />
              <Text style={[styles.tabText, loginType === 'email' && styles.activeTabText]}>
                Email
              </Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[styles.tab, loginType === 'mobile' && styles.activeTab]}
              onPress={() => setLoginType('mobile')}>
              <Icon name="phone" size={20} color={loginType === 'mobile' ? '#4f46e5' : '#64748b'} />
              <Text style={[styles.tabText, loginType === 'mobile' && styles.activeTabText]}>
                Mobile
              </Text>
            </TouchableOpacity>
          </View>

          {/* Form Container */}
          <View style={styles.formContainer}>
            
            {/* Email Login Form */}
            {loginType === 'email' && (
              <>
                <View style={styles.inputContainer}>
                  <Icon name="email" size={20} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Email address"
                    placeholderTextColor="#94a3b8"
                    value={email}
                    onChangeText={setEmail}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>

                <View style={styles.inputContainer}>
                  <Icon name="lock" size={20} color="#64748b" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Password"
                    placeholderTextColor="#94a3b8"
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry={!showPassword}
                  />
                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
                    style={styles.eyeIcon}>
                    <Icon 
                      name={showPassword ? 'visibility-off' : 'visibility'} 
                      size={20} 
                      color="#64748b" 
                    />
                  </TouchableOpacity>
                </View>

                <TouchableOpacity style={styles.forgotPassword}>
                  <Text style={styles.forgotPasswordText}>Forgot Password?</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.loginButton, isLoading && styles.disabledButton]}
                  onPress={handleEmailLogin}
                  disabled={isLoading}>
                  <Text style={styles.loginButtonText}>
                    {isLoading ? 'Signing In...' : 'Sign In'}
                  </Text>
                </TouchableOpacity>
              </>
            )}

            {/* Mobile Login Form */}
            {loginType === 'mobile' && (
              <>
                {!otpSent ? (
                  <>
                    <View style={styles.inputContainer}>
                      <Text style={styles.countryCode}>+91</Text>
                      <TextInput
                        style={[styles.input, styles.mobileInput]}
                        placeholder="Mobile number"
                        placeholderTextColor="#94a3b8"
                        value={mobileNumber}
                        onChangeText={setMobileNumber}
                        keyboardType="numeric"
                        maxLength={10}
                      />
                    </View>

                    <TouchableOpacity
                      style={[styles.loginButton, isLoading && styles.disabledButton]}
                      onPress={handleRequestOTP}
                      disabled={isLoading}>
                      <Text style={styles.loginButtonText}>
                        {isLoading ? 'Sending OTP...' : 'Send OTP'}
                      </Text>
                    </TouchableOpacity>
                  </>
                ) : (
                  <>
                    <View style={styles.otpContainer}>
                      <Text style={styles.otpSentText}>
                        OTP sent to +91 {mobileNumber}
                      </Text>
                      <TouchableOpacity onPress={resetMobileLogin}>
                        <Text style={styles.changeNumberText}>Change number</Text>
                      </TouchableOpacity>
                    </View>

                    <View style={styles.inputContainer}>
                      <Icon name="security" size={20} color="#64748b" style={styles.inputIcon} />
                      <TextInput
                        style={styles.input}
                        placeholder="Enter 6-digit OTP"
                        placeholderTextColor="#94a3b8"
                        value={otp}
                        onChangeText={setOtp}
                        keyboardType="numeric"
                        maxLength={6}
                      />
                    </View>

                    <TouchableOpacity
                      style={[styles.loginButton, isLoading && styles.disabledButton]}
                      onPress={handleVerifyOTP}
                      disabled={isLoading}>
                      <Text style={styles.loginButtonText}>
                        {isLoading ? 'Verifying...' : 'Verify OTP'}
                      </Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={styles.resendContainer}
                      onPress={handleRequestOTP}>
                      <Text style={styles.resendText}>Didn't receive OTP? Resend</Text>
                    </TouchableOpacity>
                  </>
                )}
              </>
            )}
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={styles.footerText}>Don't have an account? </Text>
            <TouchableOpacity onPress={() => navigation.navigate('Register')}>
              <Text style={styles.signUpText}>Sign Up</Text>
            </TouchableOpacity>
          </View>

        </ScrollView>
      </LinearGradient>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  gradient: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  header: {
    alignItems: 'center',
    marginBottom: 32,
  },
  welcomeText: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 8,
  },
  subtitleText: {
    fontSize: 16,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 4,
    marginBottom: 24,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
  },
  activeTab: {
    backgroundColor: '#f1f5f9',
  },
  tabText: {
    marginLeft: 8,
    fontSize: 16,
    fontWeight: '500',
    color: '#64748b',
  },
  activeTabText: {
    color: '#4f46e5',
  },
  formContainer: {
    backgroundColor: 'white',
    borderRadius: 16,
    padding: 24,
    marginBottom: 24,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 16,
    backgroundColor: '#f8fafc',
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#1e293b',
  },
  mobileInput: {
    marginLeft: 12,
  },
  countryCode: {
    fontSize: 16,
    color: '#1e293b',
    fontWeight: '500',
  },
  eyeIcon: {
    padding: 4,
  },
  forgotPassword: {
    alignSelf: 'flex-end',
    marginBottom: 24,
  },
  forgotPasswordText: {
    color: '#4f46e5',
    fontSize: 14,
    fontWeight: '500',
  },
  loginButton: {
    backgroundColor: '#4f46e5',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  disabledButton: {
    opacity: 0.6,
  },
  loginButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  otpContainer: {
    alignItems: 'center',
    marginBottom: 16,
  },
  otpSentText: {
    fontSize: 14,
    color: '#64748b',
    marginBottom: 4,
  },
  changeNumberText: {
    fontSize: 14,
    color: '#4f46e5',
    fontWeight: '500',
  },
  resendContainer: {
    alignItems: 'center',
    marginTop: 16,
  },
  resendText: {
    color: '#4f46e5',
    fontSize: 14,
    fontWeight: '500',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  footerText: {
    color: 'rgba(255, 255, 255, 0.8)',
    fontSize: 14,
  },
  signUpText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
});

export default LoginScreen;