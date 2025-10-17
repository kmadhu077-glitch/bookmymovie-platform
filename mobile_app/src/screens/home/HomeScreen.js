/**
 * Home Screen - Main dashboard with movie recommendations and features
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  Dimensions,
  TouchableOpacity,
  Image,
} from 'react-native';
import {
  Card,
  Searchbar,
  Avatar,
  Button,
  Chip,
  ActivityIndicator,
} from 'react-native-paper';
import LinearGradient from 'react-native-linear-gradient';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { useQuery } from 'react-query';
import { useAuth } from '../../contexts/AuthContext';
import { apiService } from '../../services/ApiService';
import { theme } from '../../theme/AppTheme';
import MovieCard from '../../components/MovieCard';
import TheaterCard from '../../components/TheaterCard';
import LoadingScreen from '../../components/LoadingScreen';
import ErrorScreen from '../../components/ErrorScreen';

const { width } = Dimensions.get('window');

const HomeScreen = ({ navigation }) => {
  const { user, isAuthenticated } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [selectedGenre, setSelectedGenre] = useState(null);

  // Fetch trending movies
  const {
    data: trendingMovies,
    isLoading: loadingTrending,
    error: trendingError,
    refetch: refetchTrending,
  } = useQuery(
    'trendingMovies',
    () => apiService.getMovies({ trending: true, limit: 10 }),
    {
      staleTime: theme.cache?.MOVIES_LIST || 300000,
    }
  );

  // Fetch personalized recommendations
  const {
    data: recommendations,
    isLoading: loadingRecommendations,
    error: recommendationsError,
    refetch: refetchRecommendations,
  } = useQuery(
    ['recommendations', user?.id],
    () => apiService.getMovieRecommendations(user?.id),
    {
      enabled: isAuthenticated && !!user?.id,
      staleTime: theme.cache?.MOVIES_LIST || 300000,
    }
  );

  // Fetch nearby theaters
  const {
    data: nearbyTheaters,
    isLoading: loadingTheaters,
    error: theatersError,
    refetch: refetchTheaters,
  } = useQuery(
    'nearbyTheaters',
    () => apiService.getTheaters({ nearby: true, limit: 5 }),
    {
      staleTime: theme.cache?.THEATERS_LIST || 600000,
    }
  );

  // Fetch movie genres
  const {
    data: genres,
    isLoading: loadingGenres,
  } = useQuery(
    'movieGenres',
    () => apiService.request('GET', '/catalog/genres'),
    {
      staleTime: 24 * 60 * 60 * 1000, // 24 hours
    }
  );

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([
      refetchTrending(),
      refetchRecommendations(),
      refetchTheaters(),
    ]);
    setRefreshing(false);
  };

  const handleSearch = () => {
    if (searchQuery.trim()) {
      navigation.navigate('Movies', { searchQuery });
    }
  };

  const handleMoviePress = (movie) => {
    navigation.navigate('MovieDetails', { movieId: movie.id, movie });
  };

  const handleTheaterPress = (theater) => {
    navigation.navigate('TheaterDetails', { theaterId: theater.id, theater });
  };

  const handleGenrePress = (genre) => {
    navigation.navigate('Movies', { genre: genre.id, genreName: genre.name });
  };

  const renderWelcomeSection = () => (
    <LinearGradient
      colors={[theme.colors.primary, theme.colors.primaryVariant]}
      style={styles.welcomeSection}
    >
      <View style={styles.welcomeContent}>
        <View style={styles.welcomeHeader}>
          <View>
            <Text style={styles.welcomeText}>
              {isAuthenticated ? `Welcome back, ${user?.name}!` : 'Welcome to BookMyMovie'}
            </Text>
            <Text style={styles.welcomeSubtext}>
              Discover amazing movies and book your tickets
            </Text>
          </View>
          {isAuthenticated && (
            <TouchableOpacity
              onPress={() => navigation.navigate('Profile')}
              style={styles.avatarContainer}
            >
              <Avatar.Text
                size={50}
                label={user?.name?.charAt(0) || 'U'}
                style={styles.avatar}
              />
            </TouchableOpacity>
          )}
        </View>

        <Searchbar
          placeholder="Search movies, theaters..."
          onChangeText={setSearchQuery}
          value={searchQuery}
          onSubmitEditing={handleSearch}
          style={styles.searchBar}
          inputStyle={styles.searchInput}
          iconColor={theme.colors.text}
        />
      </View>
    </LinearGradient>
  );

  const renderGenresSection = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Browse by Genre</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.genresContainer}>
          {genres?.data?.map((genre) => (
            <Chip
              key={genre.id}
              mode={selectedGenre === genre.id ? 'flat' : 'outlined'}
              selected={selectedGenre === genre.id}
              onPress={() => handleGenrePress(genre)}
              style={[
                styles.genreChip,
                selectedGenre === genre.id && styles.selectedGenreChip,
              ]}
              textStyle={[
                styles.genreChipText,
                selectedGenre === genre.id && styles.selectedGenreChipText,
              ]}
            >
              {genre.name}
            </Chip>
          ))}
        </View>
      </ScrollView>
    </View>
  );

  const renderMoviesSection = (title, movies, loading, error) => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Movies')}>
          <Text style={styles.seeAllText}>See All</Text>
        </TouchableOpacity>
      </View>

      {loading ? (
        <ActivityIndicator size="large" color={theme.colors.primary} />
      ) : error ? (
        <Text style={styles.errorText}>Failed to load movies</Text>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={styles.moviesContainer}>
            {movies?.data?.map((movie) => (
              <MovieCard
                key={movie.id}
                movie={movie}
                onPress={() => handleMoviePress(movie)}
                style={styles.movieCard}
              />
            ))}
          </View>
        </ScrollView>
      )}
    </View>
  );

  const renderTheatersSection = () => (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Nearby Theaters</Text>
        <TouchableOpacity onPress={() => navigation.navigate('Theaters')}>
          <Text style={styles.seeAllText}>See All</Text>
        </TouchableOpacity>
      </View>

      {loadingTheaters ? (
        <ActivityIndicator size="large" color={theme.colors.primary} />
      ) : theatersError ? (
        <Text style={styles.errorText}>Failed to load theaters</Text>
      ) : (
        <View>
          {nearbyTheaters?.data?.slice(0, 3).map((theater) => (
            <TheaterCard
              key={theater.id}
              theater={theater}
              onPress={() => handleTheaterPress(theater)}
              style={styles.theaterCard}
            />
          ))}
        </View>
      )}
    </View>
  );

  const renderQuickActions = () => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>Quick Actions</Text>
      <View style={styles.quickActionsContainer}>
        <TouchableOpacity
          style={styles.quickActionButton}
          onPress={() => navigation.navigate('MyBookings')}
        >
          <Icon name="confirmation-number" size={24} color={theme.colors.primary} />
          <Text style={styles.quickActionText}>My Tickets</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionButton}
          onPress={() => navigation.navigate('Notifications')}
        >
          <Icon name="notifications" size={24} color={theme.colors.primary} />
          <Text style={styles.quickActionText}>Notifications</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.quickActionButton}
          onPress={() => navigation.navigate('Settings')}
        >
          <Icon name="settings" size={24} color={theme.colors.primary} />
          <Text style={styles.quickActionText}>Settings</Text>
        </TouchableOpacity>
      </View>
    </View>
  );

  if (loadingTrending && loadingRecommendations && loadingTheaters) {
    return <LoadingScreen />;
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
    >
      {renderWelcomeSection()}
      
      {!loadingGenres && genres?.data && renderGenresSection()}
      
      {isAuthenticated && recommendations?.data && (
        <>
          {renderMoviesSection(
            'Recommended For You',
            recommendations,
            loadingRecommendations,
            recommendationsError
          )}
        </>
      )}
      
      {renderMoviesSection(
        'Trending Now',
        trendingMovies,
        loadingTrending,
        trendingError
      )}
      
      {renderTheatersSection()}
      
      {isAuthenticated && renderQuickActions()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  welcomeSection: {
    padding: theme.spacing.md,
    paddingTop: theme.spacing.xl,
  },
  welcomeContent: {
    paddingBottom: theme.spacing.md,
  },
  welcomeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  welcomeText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: theme.colors.onPrimary,
    marginBottom: theme.spacing.xs,
  },
  welcomeSubtext: {
    fontSize: 16,
    color: theme.colors.onPrimary,
    opacity: 0.8,
  },
  avatarContainer: {
    ...theme.shadows.small,
  },
  avatar: {
    backgroundColor: theme.colors.secondary,
  },
  searchBar: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    elevation: 4,
  },
  searchInput: {
    color: theme.colors.text,
  },
  section: {
    padding: theme.spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  seeAllText: {
    fontSize: 16,
    color: theme.colors.primary,
    fontWeight: '500',
  },
  genresContainer: {
    flexDirection: 'row',
    paddingVertical: theme.spacing.xs,
  },
  genreChip: {
    marginRight: theme.spacing.sm,
    backgroundColor: theme.colors.surface,
  },
  selectedGenreChip: {
    backgroundColor: theme.colors.primary,
  },
  genreChipText: {
    color: theme.colors.text,
  },
  selectedGenreChipText: {
    color: theme.colors.onPrimary,
  },
  moviesContainer: {
    flexDirection: 'row',
    paddingVertical: theme.spacing.xs,
  },
  movieCard: {
    marginRight: theme.spacing.md,
  },
  theaterCard: {
    marginBottom: theme.spacing.sm,
  },
  quickActionsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: theme.spacing.sm,
  },
  quickActionButton: {
    alignItems: 'center',
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    minWidth: 80,
    ...theme.shadows.small,
  },
  quickActionText: {
    marginTop: theme.spacing.xs,
    fontSize: 12,
    color: theme.colors.text,
    textAlign: 'center',
  },
  errorText: {
    color: theme.colors.error,
    textAlign: 'center',
    marginVertical: theme.spacing.md,
  },
});

export default HomeScreen;