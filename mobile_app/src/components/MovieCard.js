/**
 * Movie Card Component
 * Displays movie information in a card format
 */

import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
} from 'react-native';
import { Card, Chip } from 'react-native-paper';
import FastImage from 'react-native-fast-image';
import Icon from 'react-native-vector-icons/MaterialIcons';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '../theme/AppTheme';

const MovieCard = ({ 
  movie, 
  onPress, 
  style, 
  showRating = true, 
  showGenre = true,
  size = 'medium' 
}) => {
  const cardWidth = size === 'small' ? 120 : size === 'large' ? 200 : 150;
  const cardHeight = size === 'small' ? 180 : size === 'large' ? 300 : 225;

  const getRatingColor = (rating) => {
    if (rating >= 8) return theme.colors.ratingExcellent;
    if (rating >= 6) return theme.colors.ratingGood;
    if (rating >= 4) return theme.colors.ratingAverage;
    return theme.colors.ratingPoor;
  };

  const formatRating = (rating) => {
    return typeof rating === 'number' ? rating.toFixed(1) : '0.0';
  };

  const formatGenres = (genres) => {
    if (!genres || !Array.isArray(genres)) return '';
    return genres.slice(0, 2).map(genre => 
      typeof genre === 'object' ? genre.name : genre
    ).join(', ');
  };

  const getImageUri = () => {
    if (movie.poster_url) return movie.poster_url;
    if (movie.poster_path) return movie.poster_path;
    if (movie.image) return movie.image;
    return null;
  };

  return (
    <TouchableOpacity 
      style={[styles.container, { width: cardWidth }, style]} 
      onPress={() => onPress && onPress(movie)}
      activeOpacity={0.8}
    >
      <Card style={[styles.card, { height: cardHeight }]}>
        <View style={styles.imageContainer}>
          {getImageUri() ? (
            <FastImage
              source={{ 
                uri: getImageUri(),
                priority: FastImage.priority.normal,
                cache: FastImage.cacheControl.immutable
              }}
              style={styles.image}
              resizeMode={FastImage.resizeMode.cover}
              fallback={true}
            >
              <Image
                source={require('../assets/images/movie-placeholder.png')}
                style={styles.image}
                resizeMode="cover"
              />
            </FastImage>
          ) : (
            <View style={styles.placeholderContainer}>
              <Icon 
                name="movie" 
                size={40} 
                color={theme.colors.disabled} 
              />
            </View>
          )}

          {/* Rating Badge */}
          {showRating && movie.rating && (
            <View 
              style={[
                styles.ratingBadge, 
                { backgroundColor: getRatingColor(movie.rating) }
              ]}
            >
              <Icon name="star" size={12} color="#FFFFFF" />
              <Text style={styles.ratingText}>
                {formatRating(movie.rating)}
              </Text>
            </View>
          )}

          {/* Duration Badge */}
          {movie.duration && (
            <View style={styles.durationBadge}>
              <Text style={styles.durationText}>
                {movie.duration}min
              </Text>
            </View>
          )}

          {/* Gradient Overlay for Text */}
          <LinearGradient
            colors={['transparent', 'rgba(0,0,0,0.8)']}
            style={styles.gradientOverlay}
          />
        </View>

        <View style={styles.content}>
          <Text style={styles.title} numberOfLines={2}>
            {movie.title || movie.name || 'Unknown Title'}
          </Text>

          {showGenre && movie.genres && (
            <Text style={styles.genre} numberOfLines={1}>
              {formatGenres(movie.genres)}
            </Text>
          )}

          {movie.release_date && (
            <Text style={styles.releaseDate}>
              {new Date(movie.release_date).getFullYear()}
            </Text>
          )}

          {movie.language && (
            <Chip 
              mode="outlined" 
              compact 
              style={styles.languageChip}
              textStyle={styles.languageChipText}
            >
              {movie.language.toUpperCase()}
            </Chip>
          )}
        </View>

        {/* Favorite/Watchlist Button */}
        <TouchableOpacity 
          style={styles.favoriteButton}
          onPress={(e) => {
            e.stopPropagation();
            // Handle favorite toggle
          }}
        >
          <Icon 
            name="favorite-border" 
            size={20} 
            color={theme.colors.text} 
          />
        </TouchableOpacity>
      </Card>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    marginBottom: theme.spacing.sm,
  },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    overflow: 'hidden',
    ...theme.shadows.medium,
  },
  imageContainer: {
    flex: 1,
    position: 'relative',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  placeholderContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
  },
  ratingBadge: {
    position: 'absolute',
    top: theme.spacing.sm,
    left: theme.spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.xs,
    paddingVertical: 2,
    borderRadius: theme.borderRadius.sm,
    ...theme.shadows.small,
  },
  ratingText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: 'bold',
    marginLeft: 2,
  },
  durationBadge: {
    position: 'absolute',
    top: theme.spacing.sm,
    right: theme.spacing.sm,
    backgroundColor: 'rgba(0,0,0,0.7)',
    paddingHorizontal: theme.spacing.xs,
    paddingVertical: 2,
    borderRadius: theme.borderRadius.sm,
  },
  durationText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '500',
  },
  gradientOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 60,
  },
  content: {
    padding: theme.spacing.sm,
    minHeight: 80,
  },
  title: {
    fontSize: 14,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
    lineHeight: 18,
  },
  genre: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
  },
  releaseDate: {
    fontSize: 11,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
  },
  languageChip: {
    alignSelf: 'flex-start',
    height: 24,
    backgroundColor: theme.colors.primary + '20',
    borderColor: theme.colors.primary,
  },
  languageChipText: {
    fontSize: 10,
    color: theme.colors.primary,
  },
  favoriteButton: {
    position: 'absolute',
    bottom: theme.spacing.sm,
    right: theme.spacing.sm,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(0,0,0,0.7)',
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default MovieCard;