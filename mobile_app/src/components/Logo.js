import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { AppBranding, LogoStyles } from '../constants/branding';

const Logo = ({ 
  size = 'medium', 
  showText = true, 
  showTagline = false, 
  style = {} 
}) => {
  const sizes = {
    small: { icon: 32, text: 18, tagline: 12 },
    medium: { icon: 48, text: 24, tagline: 14 },
    large: { icon: 64, text: 32, tagline: 16 },
    xlarge: { icon: 80, text: 40, tagline: 18 }
  };

  const currentSize = sizes[size];

  return (
    <View style={[styles.container, style]}>
      <View style={[
        styles.icon,
        {
          width: currentSize.icon,
          height: currentSize.icon,
          borderRadius: currentSize.icon * 0.25,
        }
      ]}>
        <Text style={[styles.iconText, { fontSize: currentSize.icon * 0.5 }]}>
          {AppBranding.logo.icon}
        </Text>
      </View>
      
      {showText && (
        <View style={styles.textContainer}>
          <Text style={[styles.brandName, { fontSize: currentSize.text }]}>
            {AppBranding.appName}
          </Text>
          {showTagline && (
            <Text style={[styles.tagline, { fontSize: currentSize.tagline }]}>
              {AppBranding.tagline}
            </Text>
          )}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: AppBranding.spacing.sm,
  },
  
  icon: {
    backgroundColor: AppBranding.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: AppBranding.colors.primary,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  
  iconText: {
    color: 'white',
  },
  
  textContainer: {
    flex: 1,
  },
  
  brandName: {
    fontFamily: AppBranding.typography.fontFamily.primary,
    fontWeight: AppBranding.typography.weights.heavy,
    color: AppBranding.colors.text,
    letterSpacing: -0.5,
  },
  
  tagline: {
    fontFamily: AppBranding.typography.fontFamily.primary,
    fontWeight: AppBranding.typography.weights.light,
    color: AppBranding.colors.textSecondary,
    letterSpacing: 0.5,
    marginTop: 2,
  },
});

export default Logo;