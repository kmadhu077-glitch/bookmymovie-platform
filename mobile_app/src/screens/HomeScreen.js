import React, {useEffect, useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
  RefreshControl,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import LinearGradient from 'react-native-linear-gradient';
import {useAuth} from '../context/AuthContext';
import {useBooking} from '../context/BookingContext';

const {width} = Dimensions.get('window');
const CARD_WIDTH = width * 0.8;

const HomeScreen = ({navigation}) => {
  const {user} = useAuth();
  const {movies, fetchMovies} = useBooking();
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchMovies();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchMovies();
    setRefreshing(false);
  };

  const navigateToMovieDetails = (movie) => {
    navigation.navigate('MovieDetails', {movie});
  };

  const featuredMovies = movies.slice(0, 5);
  const popularMovies = movies.slice(0, 3);

  return (
    <ScrollView
      style={styles.container}
      showsVerticalScrollIndicator={false}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      
      {/* Header */}
      <LinearGradient
        colors={['#4f46e5', '#7c3aed']}
        style={styles.header}>
        <View style={styles.headerContent}>
          <View>
            <Text style={styles.greeting}>Hello, {user?.name || 'User'}!</Text>
            <Text style={styles.subtitle}>What movie would you like to watch?</Text>
          </View>
          <TouchableOpacity 
            style={styles.profileButton}
            onPress={() => navigation.navigate('Profile')}>
            <Icon name="person" size={24} color="white" />
          </TouchableOpacity>
        </View>
      </LinearGradient>

      {/* Quick Actions */}
      <View style={styles.quickActions}>
        <TouchableOpacity 
          style={styles.actionCard}
          onPress={() => navigation.navigate('Movies')}>
          <LinearGradient
            colors={['#ef4444', '#dc2626']}
            style={styles.actionGradient}>
            <Icon name="local-movies" size={32} color="white" />
            <Text style={styles.actionText}>Browse Movies</Text>
          </LinearGradient>
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.actionCard}
          onPress={() => navigation.navigate('Bookings')}>
          <LinearGradient
            colors={['#10b981', '#059669']}
            style={styles.actionGradient}>
            <Icon name="confirmation-number" size={32} color="white" />
            <Text style={styles.actionText}>My Bookings</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>

      {/* Featured Movies Carousel */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Featured Movies</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Movies')}>
            <Text style={styles.seeAll}>See All</Text>
          </TouchableOpacity>
        </View>

        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.carouselContent}
          snapToInterval={CARD_WIDTH + 16}
          decelerationRate="fast">
          {featuredMovies.map((movie, index) => (
            <TouchableOpacity
              key={movie.id}
              style={styles.featuredCard}
              onPress={() => navigateToMovieDetails(movie)}>
              <Image
                source={{uri: movie.poster_url}}
                style={styles.featuredImage}
                resizeMode="cover"
              />
              <LinearGradient
                colors={['transparent', 'rgba(0,0,0,0.8)']}
                style={styles.featuredOverlay}>
                <View style={styles.featuredContent}>
                  <Text style={styles.featuredTitle} numberOfLines={2}>
                    {movie.title}
                  </Text>
                  <View style={styles.movieInfo}>
                    <View style={styles.ratingContainer}>
                      <Icon name="star" size={16} color="#fbbf24" />
                      <Text style={styles.rating}>{movie.rating}</Text>
                    </View>
                    <Text style={styles.genre}>{movie.genre}</Text>
                  </View>
                </View>
              </LinearGradient>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Popular Movies */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Popular This Week</Text>
          <TouchableOpacity onPress={() => navigation.navigate('Movies')}>
            <Text style={styles.seeAll}>See All</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.popularGrid}>
          {popularMovies.map((movie, index) => (
            <TouchableOpacity
              key={movie.id}
              style={styles.popularCard}
              onPress={() => navigateToMovieDetails(movie)}>
              <Image
                source={{uri: movie.poster_url}}
                style={styles.popularImage}
                resizeMode="cover"
              />
              <View style={styles.popularContent}>
                <Text style={styles.popularTitle} numberOfLines={2}>
                  {movie.title}
                </Text>
                <View style={styles.popularInfo}>
                  <View style={styles.ratingContainer}>
                    <Icon name="star" size={14} color="#fbbf24" />
                    <Text style={styles.popularRating}>{movie.rating}</Text>
                  </View>
                  <Text style={styles.popularGenre}>{movie.genre}</Text>
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Movie Categories */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Browse by Genre</Text>
        <View style={styles.genreGrid}>
          {[
            {name: 'Action', icon: 'flash-on', color: '#ef4444'},
            {name: 'Comedy', icon: 'sentiment-very-satisfied', color: '#f59e0b'},
            {name: 'Drama', icon: 'theater-comedy', color: '#8b5cf6'},
            {name: 'Horror', icon: 'sentiment-very-dissatisfied', color: '#1f2937'},
            {name: 'Romance', icon: 'favorite', color: '#ec4899'},
            {name: 'Sci-Fi', icon: 'science', color: '#06b6d4'},
          ].map((genre, index) => (
            <TouchableOpacity
              key={index}
              style={[styles.genreCard, {backgroundColor: genre.color}]}
              onPress={() => navigation.navigate('Movies', {genre: genre.name})}>
              <Icon name={genre.icon} size={24} color="white" />
              <Text style={styles.genreText}>{genre.name}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Recent Activity */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Continue Watching</Text>
        <View style={styles.emptyState}>
          <Icon name="movie" size={48} color="#94a3b8" />
          <Text style={styles.emptyText}>No recent activity</Text>
          <Text style={styles.emptySubtext}>Start booking movies to see them here</Text>
        </View>
      </View>

    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    paddingTop: 60,
    paddingBottom: 24,
    paddingHorizontal: 20,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: {
    fontSize: 24,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  profileButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  quickActions: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingTop: 20,
    gap: 16,
  },
  actionCard: {
    flex: 1,
    height: 100,
    borderRadius: 16,
    overflow: 'hidden',
  },
  actionGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  actionText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 8,
  },
  section: {
    paddingHorizontal: 20,
    paddingTop: 32,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1e293b',
  },
  seeAll: {
    fontSize: 14,
    color: '#4f46e5',
    fontWeight: '600',
  },
  carouselContent: {
    paddingLeft: 20,
    paddingRight: 4,
  },
  featuredCard: {
    width: CARD_WIDTH,
    height: 200,
    borderRadius: 16,
    marginRight: 16,
    overflow: 'hidden',
  },
  featuredImage: {
    width: '100%',
    height: '100%',
  },
  featuredOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: '60%',
    justifyContent: 'flex-end',
  },
  featuredContent: {
    padding: 16,
  },
  featuredTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 8,
  },
  movieInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rating: {
    fontSize: 14,
    color: 'white',
    marginLeft: 4,
    fontWeight: '600',
  },
  genre: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
  },
  popularGrid: {
    gap: 16,
  },
  popularCard: {
    flexDirection: 'row',
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  popularImage: {
    width: 80,
    height: 100,
    borderRadius: 8,
  },
  popularContent: {
    flex: 1,
    marginLeft: 12,
    justifyContent: 'space-between',
  },
  popularTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1e293b',
    marginBottom: 8,
  },
  popularInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  popularRating: {
    fontSize: 12,
    color: '#64748b',
    marginLeft: 4,
  },
  popularGenre: {
    fontSize: 12,
    color: '#64748b',
  },
  genreGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  genreCard: {
    width: (width - 64) / 3,
    height: 80,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  genreText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 4,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#64748b',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#94a3b8',
    marginTop: 4,
    textAlign: 'center',
  },
});

export default HomeScreen;