/**
 * BookMyMovie App - Branding Configuration
 * Logo, colors, and visual identity
 */

export const AppBranding = {
  // App Information
  appName: 'BookMyMovie',
  tagline: 'Book Fast Feel First',
  
  // Logo Configuration
  logo: {
    icon: '🎬',
  
  // Custom Logo Configuration
  customLogo: {
    enabled: true,
    pdfPath: '../assets/custom_logo.pdf',
    fallbackIcon: '🎬',
    description: 'User uploaded custom logo (PDF format)',
    usage: 'Display in splash screen, headers, and branding elements',
  }, // Cinema emoji as primary icon
    iconFallback: 'BM', // Text fallback
    backgroundColor: '#667eea',
    gradientColors: ['#667eea', '#764ba2'],
  },
  
  // Color Palette
  colors: {
    primary: '#667eea',
    primaryDark: '#764ba2',
    secondary: '#ff6b6b',
    accent: '#ee5a24',
    
    // Gradients
    primaryGradient: 'linear-gradient(45deg, #667eea, #764ba2)',
    accentGradient: 'linear-gradient(45deg, #ff6b6b, #ee5a24)',
    
    // UI Colors
    background: '#f8f9fa',
    surface: '#ffffff',
    text: '#2c3e50',
    textSecondary: '#7f8c8d',
    border: '#e9ecef',
    
    // Status Colors
    success: '#27ae60',
    warning: '#f39c12',
    error: '#e74c3c',
    info: '#3498db',
  },
  
  // Typography
  typography: {
    fontFamily: {
      primary: 'Segoe UI, Arial, Helvetica, sans-serif',
      secondary: 'Georgia, serif',
    },
    sizes: {
      xs: 12,
      sm: 14,
      md: 16,
      lg: 18,
      xl: 24,
      xxl: 32,
      xxxl: 48,
    },
    weights: {
      light: '300',
      normal: '400',
      medium: '500',
      bold: '700',
      heavy: '800',
    },
  },
  
  // Spacing
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
    xxl: 48,
  },
  
  // Border Radius
  borderRadius: {
    small: 8,
    medium: 12,
    large: 20,
    round: 50,
  },
  
  // Shadows
  shadows: {
    small: '0 2px 8px rgba(0,0,0,0.1)',
    medium: '0 4px 16px rgba(0,0,0,0.12)',
    large: '0 8px 32px rgba(0,0,0,0.15)',
    primary: '0 4px 16px rgba(102, 126, 234, 0.3)',
  },
  
  // Animation
  animation: {
    duration: {
      fast: 200,
      normal: 300,
      slow: 500,
    },
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
};

// Logo Component Styles
export const LogoStyles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: AppBranding.spacing.sm,
  },
  
  icon: {
    width: 48,
    height: 48,
    backgroundColor: AppBranding.colors.primary,
    borderRadius: AppBranding.borderRadius.medium,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 24,
    background: AppBranding.colors.primaryGradient,
    boxShadow: AppBranding.shadows.primary,
  },
  
  text: {
    fontSize: AppBranding.typography.sizes.xl,
    fontWeight: AppBranding.typography.weights.heavy,
    color: AppBranding.colors.text,
    margin: 0,
  },
  
  tagline: {
    fontSize: AppBranding.typography.sizes.sm,
    color: AppBranding.colors.textSecondary,
    fontWeight: AppBranding.typography.weights.light,
    margin: 0,
    letterSpacing: '0.5px',
  },
};

// Tagline Options
export const TaglineOptions = [
  'Book Fast Feel First', // Primary tagline
  'Your Cinema Experience, Perfected',
  'Where Stories Come to Life',
  'Book Smart. Watch Better.',
  'Every Seat. Every Show. Every Moment.',
  'The Future of Movie Booking',
  'Seamless Booking. Endless Entertainment.',
  'Your Movies. Your Way. Your Time.',
];

// App Icon Specifications
export const AppIconSpecs = {
  ios: {
    sizes: [1024, 180, 167, 152, 144, 120, 114, 76, 72, 60, 57, 40, 29, 20],
    format: 'PNG',
    background: AppBranding.colors.primaryGradient,
  },
  
  android: {
    sizes: [512, 192, 144, 96, 72, 48, 36],
    format: 'PNG',
    adaptiveIcon: true,
    background: AppBranding.colors.primaryGradient,
  },
  
  web: {
    favicon: [32, 16],
    appleTouchIcon: [180, 152, 144, 120, 114, 76, 72, 60, 57],
    manifest: [512, 192, 144, 96, 72, 48],
  },
};

// Social Media Specifications
export const SocialMediaSpecs = {
  facebook: { width: 1200, height: 630 },
  twitter: { width: 1200, height: 675 },
  instagram: { width: 1080, height: 1080 },
  linkedin: { width: 1200, height: 627 },
  youtube: { width: 1280, height: 720 },
};

// Brand Guidelines
export const BrandGuidelines = {
  logo: {
    minimumSize: '32px height',
    clearSpace: '1x logo height on all sides',
    doNot: [
      'Stretch or distort the logo',
      'Change the colors',
      'Add effects or shadows',
      'Use on busy backgrounds',
      'Rotate or flip the logo',
    ],
  },
  
  colors: {
    primary: 'Use for main actions, headers, and brand elements',
    secondary: 'Use for accents, highlights, and secondary actions',
    neutral: 'Use for text, backgrounds, and UI elements',
  },
  
  typography: {
    headings: 'Use bold weights for impact',
    body: 'Use normal weight for readability',
    captions: 'Use light weight for secondary text',
  },
};

export default AppBranding;