import React, {useEffect, useState} from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  TextInput,
  RefreshControl,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import {useBooking} from '../context/BookingContext';

const MoviesScreen = ({navigation, route}) => {
  const {movies, fetchMovies} = useBooking();
  const [filteredMovies, setFilteredMovies] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('all');
  const [refreshing, setRefreshing] = useState(false);

  const genres = ['all', 'action', 'comedy', 'drama', 'horror', 'romance', 'sci-fi'];

  useEffect(() => {
    fetchMovies();
  }, []);

  useEffect(() => {
    // Check if genre filter was passed from navigation
    if (route.params?.genre) {
      setSelectedGenre(route.params.genre.toLowerCase());
    }
  }, [route.params]);

  useEffect(() => {
    filterMovies();
  }, [movies, searchQuery, selectedGenre]);

  const filterMovies = () => {
    let filtered = [...movies];

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(movie =>
        movie.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        movie.genre.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Filter by genre
    if (selectedGenre !== 'all') {
      filtered = filtered.filter(movie =>
        movie.genre.toLowerCase() === selectedGenre
      );
    }

    setFilteredMovies(filtered);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchMovies();
    setRefreshing(false);
  };

  const navigateToMovieDetails = (movie) => {
    navigation.navigate('MovieDetails', {movie});
  };

  const renderMovieCard = ({item: movie}) => (
    <TouchableOpacity
      style={styles.movieCard}
      onPress={() => navigateToMovieDetails(movie)}>
      <Image
        source={{uri: movie.poster_url}}
        style={styles.movieImage}
        resizeMode="cover"
      />
      <View style={styles.movieContent}>
        <Text style={styles.movieTitle} numberOfLines={2}>
          {movie.title}
        </Text>
        <View style={styles.movieInfo}>
          <View style={styles.ratingContainer}>
            <Icon name="star" size={16} color="#fbbf24" />
            <Text style={styles.rating}>{movie.rating}</Text>
          </View>
          <Text style={styles.genre}>{movie.genre}</Text>
        </View>
        <Text style={styles.duration}>{movie.duration} min</Text>
        <TouchableOpacity
          style={styles.bookButton}
          onPress={() => navigateToMovieDetails(movie)}>
          <Text style={styles.bookButtonText}>Book Now</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  );

  const renderGenreFilter = () => (
    <View style={styles.genreFilter}>
      <FlatList
        horizontal
        showsHorizontalScrollIndicator={false}
        data={genres}
        keyExtractor={item => item}
        contentContainerStyle={styles.genreList}
        renderItem={({item}) => (
          <TouchableOpacity
            style={[
              styles.genreChip,
              selectedGenre === item && styles.activeGenreChip,
            ]}
            onPress={() => setSelectedGenre(item)}>
            <Text
              style={[
                styles.genreChipText,
                selectedGenre === item && styles.activeGenreChipText,
              ]}>
              {item.charAt(0).toUpperCase() + item.slice(1)}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Movies</Text>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Icon name="arrow-back" size={24} color="#1e293b" />
        </TouchableOpacity>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Icon name="search" size={20} color="#64748b" />
        <TextInput
          style={styles.searchInput}
          placeholder="Search movies..."
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholderTextColor="#94a3b8"
        />
        {searchQuery !== '' && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Icon name="close" size={20} color="#64748b" />
          </TouchableOpacity>
        )}
      </View>

      {/* Genre Filter */}
      {renderGenreFilter()}

      {/* Movies List */}
      <FlatList
        data={filteredMovies}
        renderItem={renderMovieCard}
        keyExtractor={item => item.id}
        numColumns={2}
        contentContainerStyle={styles.moviesList}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Icon name="movie" size={48} color="#94a3b8" />
            <Text style={styles.emptyText}>No movies found</Text>
            <Text style={styles.emptySubtext}>
              Try adjusting your search or filters
            </Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
    backgroundColor: 'white',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1e293b',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'white',
    marginHorizontal: 20,
    marginVertical: 16,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    color: '#1e293b',
    marginLeft: 12,
  },
  genreFilter: {
    paddingVertical: 8,
  },
  genreList: {
    paddingHorizontal: 20,
  },
  genreChip: {
    backgroundColor: 'white',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  activeGenreChip: {
    backgroundColor: '#4f46e5',
    borderColor: '#4f46e5',
  },
  genreChipText: {
    fontSize: 14,
    color: '#64748b',
    fontWeight: '500',
  },
  activeGenreChipText: {
    color: 'white',
  },
  moviesList: {
    paddingHorizontal: 12,
    paddingBottom: 20,
  },
  movieCard: {
    flex: 1,
    backgroundColor: 'white',
    borderRadius: 16,
    margin: 8,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 2},
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  movieImage: {
    width: '100%',
    height: 200,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  movieContent: {
    padding: 16,
  },
  movieTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1e293b',
    marginBottom: 8,
  },
  movieInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rating: {
    fontSize: 14,
    color: '#64748b',
    marginLeft: 4,
    fontWeight: '600',
  },
  genre: {
    fontSize: 12,
    color: '#64748b',
    backgroundColor: '#f1f5f9',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  duration: {
    fontSize: 12,
    color: '#94a3b8',
    marginBottom: 12,
  },
  bookButton: {
    backgroundColor: '#4f46e5',
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: 'center',
  },
  bookButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#64748b',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#94a3b8',
    marginTop: 8,
    textAlign: 'center',
  },
});

export default MoviesScreen;