"""
External Movie Database Integration Service
Integration with TMDB, OMDB, and other movie databases
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, date
import json
import os
from enum import Enum
import hashlib

logger = logging.getLogger(__name__)

class MovieProvider(Enum):
    """Supported movie database providers"""
    TMDB = "tmdb"
    OMDB = "omdb"
    IMDB = "imdb"
    TVDB = "tvdb"

@dataclass
class MovieData:
    """Standardized movie data structure"""
    external_id: str
    title: str
    original_title: str
    overview: str
    release_date: Optional[date]
    runtime: Optional[int]
    genres: List[str]
    rating: Optional[float]
    vote_count: Optional[int]
    poster_url: Optional[str]
    backdrop_url: Optional[str]
    trailer_url: Optional[str]
    cast: List[Dict[str, Any]]
    crew: List[Dict[str, Any]]
    production_companies: List[str]
    budget: Optional[int]
    revenue: Optional[int]
    languages: List[str]
    countries: List[str]
    status: str
    tagline: Optional[str]
    provider: MovieProvider
    raw_data: Dict[str, Any]

@dataclass
class PersonData:
    """Person (actor/director) data structure"""
    external_id: str
    name: str
    biography: Optional[str]
    birthday: Optional[date]
    deathday: Optional[date]
    place_of_birth: Optional[str]
    profile_url: Optional[str]
    known_for: List[Dict[str, Any]]
    provider: MovieProvider
    raw_data: Dict[str, Any]

class TMDBService:
    """The Movie Database (TMDB) integration"""
    
    def __init__(self):
        self.api_key = os.getenv('TMDB_API_KEY')
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_movies(self, query: str, page: int = 1, year: int = None) -> Dict[str, Any]:
        """Search for movies on TMDB"""
        params = {
            'api_key': self.api_key,
            'query': query,
            'page': page,
            'language': 'en-US'
        }
        
        if year:
            params['year'] = year
        
        async with self.session.get(f"{self.base_url}/search/movie", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'results': [self._format_movie_result(movie) for movie in data.get('results', [])],
                    'total_results': data.get('total_results', 0),
                    'total_pages': data.get('total_pages', 0),
                    'current_page': page
                }
            else:
                logger.error(f"TMDB search failed: {response.status}")
                return {'results': [], 'total_results': 0, 'total_pages': 0, 'current_page': page}
    
    async def get_movie_details(self, movie_id: str) -> Optional[MovieData]:
        """Get detailed movie information from TMDB"""
        try:
            # Get basic movie details
            params = {'api_key': self.api_key, 'language': 'en-US'}
            
            async with self.session.get(f"{self.base_url}/movie/{movie_id}", params=params) as response:
                if response.status != 200:
                    return None
                
                movie_data = await response.json()
            
            # Get additional details (credits, videos)
            credits_task = self._get_movie_credits(movie_id)
            videos_task = self._get_movie_videos(movie_id)
            
            credits, videos = await asyncio.gather(credits_task, videos_task, return_exceptions=True)
            
            # Format the data
            return self._format_movie_details(movie_data, credits, videos)
            
        except Exception as e:
            logger.error(f"Failed to get TMDB movie details for {movie_id}: {e}")
            return None
    
    async def _get_movie_credits(self, movie_id: str) -> Dict[str, Any]:
        """Get movie credits (cast and crew)"""
        params = {'api_key': self.api_key}
        
        async with self.session.get(f"{self.base_url}/movie/{movie_id}/credits", params=params) as response:
            if response.status == 200:
                return await response.json()
            return {'cast': [], 'crew': []}
    
    async def _get_movie_videos(self, movie_id: str) -> Dict[str, Any]:
        """Get movie videos (trailers, teasers)"""
        params = {'api_key': self.api_key, 'language': 'en-US'}
        
        async with self.session.get(f"{self.base_url}/movie/{movie_id}/videos", params=params) as response:
            if response.status == 200:
                return await response.json()
            return {'results': []}
    
    def _format_movie_result(self, movie: Dict[str, Any]) -> Dict[str, Any]:
        """Format movie search result"""
        return {
            'id': movie.get('id'),
            'title': movie.get('title'),
            'original_title': movie.get('original_title'),
            'overview': movie.get('overview'),
            'release_date': movie.get('release_date'),
            'poster_url': self._get_image_url(movie.get('poster_path')),
            'backdrop_url': self._get_image_url(movie.get('backdrop_path'), 'w1280'),
            'rating': movie.get('vote_average'),
            'vote_count': movie.get('vote_count'),
            'genre_ids': movie.get('genre_ids', []),
            'provider': 'tmdb'
        }
    
    def _format_movie_details(self, movie: Dict[str, Any], credits: Dict[str, Any], videos: Dict[str, Any]) -> MovieData:
        """Format detailed movie data"""
        # Get trailer URL
        trailer_url = None
        if isinstance(videos, dict):
            for video in videos.get('results', []):
                if video.get('type') == 'Trailer' and video.get('site') == 'YouTube':
                    trailer_url = f"https://www.youtube.com/watch?v={video.get('key')}"
                    break
        
        # Format cast
        cast = []
        if isinstance(credits, dict):
            for person in credits.get('cast', [])[:10]:  # Top 10 cast members
                cast.append({
                    'id': person.get('id'),
                    'name': person.get('name'),
                    'character': person.get('character'),
                    'profile_url': self._get_image_url(person.get('profile_path'))
                })
        
        # Format crew (directors, producers, etc.)
        crew = []
        if isinstance(credits, dict):
            for person in credits.get('crew', []):
                if person.get('job') in ['Director', 'Producer', 'Executive Producer', 'Writer']:
                    crew.append({
                        'id': person.get('id'),
                        'name': person.get('name'),
                        'job': person.get('job'),
                        'profile_url': self._get_image_url(person.get('profile_path'))
                    })
        
        return MovieData(
            external_id=str(movie.get('id')),
            title=movie.get('title', ''),
            original_title=movie.get('original_title', ''),
            overview=movie.get('overview', ''),
            release_date=self._parse_date(movie.get('release_date')),
            runtime=movie.get('runtime'),
            genres=[genre.get('name') for genre in movie.get('genres', [])],
            rating=movie.get('vote_average'),
            vote_count=movie.get('vote_count'),
            poster_url=self._get_image_url(movie.get('poster_path')),
            backdrop_url=self._get_image_url(movie.get('backdrop_path'), 'w1280'),
            trailer_url=trailer_url,
            cast=cast,
            crew=crew,
            production_companies=[company.get('name') for company in movie.get('production_companies', [])],
            budget=movie.get('budget'),
            revenue=movie.get('revenue'),
            languages=[lang.get('english_name') for lang in movie.get('spoken_languages', [])],
            countries=[country.get('name') for country in movie.get('production_countries', [])],
            status=movie.get('status', 'Unknown'),
            tagline=movie.get('tagline'),
            provider=MovieProvider.TMDB,
            raw_data=movie
        )
    
    def _get_image_url(self, path: str, size: str = 'w500') -> Optional[str]:
        """Generate full image URL"""
        if path:
            return f"{self.image_base_url}/{size}{path}"
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        return None
    
    async def get_popular_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get popular movies from TMDB"""
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': 'en-US'
        }
        
        async with self.session.get(f"{self.base_url}/movie/popular", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'results': [self._format_movie_result(movie) for movie in data.get('results', [])],
                    'total_results': data.get('total_results', 0),
                    'total_pages': data.get('total_pages', 0),
                    'current_page': page
                }
            return {'results': [], 'total_results': 0, 'total_pages': 0, 'current_page': page}
    
    async def get_top_rated_movies(self, page: int = 1) -> Dict[str, Any]:
        """Get top-rated movies from TMDB"""
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': 'en-US'
        }
        
        async with self.session.get(f"{self.base_url}/movie/top_rated", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'results': [self._format_movie_result(movie) for movie in data.get('results', [])],
                    'total_results': data.get('total_results', 0),
                    'total_pages': data.get('total_pages', 0),
                    'current_page': page
                }
            return {'results': [], 'total_results': 0, 'total_pages': 0, 'current_page': page}
    
    async def get_movie_recommendations(self, movie_id: str, page: int = 1) -> List[Dict[str, Any]]:
        """Get movie recommendations from TMDB"""
        params = {
            'api_key': self.api_key,
            'page': page,
            'language': 'en-US'
        }
        
        async with self.session.get(f"{self.base_url}/movie/{movie_id}/recommendations", params=params) as response:
            if response.status == 200:
                data = await response.json()
                return [self._format_movie_result(movie) for movie in data.get('results', [])]
            return []

class OMDBService:
    """Open Movie Database (OMDB) integration"""
    
    def __init__(self):
        self.api_key = os.getenv('OMDB_API_KEY')
        self.base_url = "http://www.omdbapi.com"
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_movies(self, query: str, page: int = 1, year: int = None) -> Dict[str, Any]:
        """Search for movies on OMDB"""
        params = {
            'apikey': self.api_key,
            's': query,
            'page': page,
            'type': 'movie'
        }
        
        if year:
            params['y'] = year
        
        async with self.session.get(self.base_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                if data.get('Response') == 'True':
                    return {
                        'results': [self._format_movie_result(movie) for movie in data.get('Search', [])],
                        'total_results': int(data.get('totalResults', 0)),
                        'current_page': page
                    }
                
            return {'results': [], 'total_results': 0, 'current_page': page}
    
    async def get_movie_details(self, imdb_id: str = None, title: str = None, year: int = None) -> Optional[MovieData]:
        """Get detailed movie information from OMDB"""
        try:
            params = {
                'apikey': self.api_key,
                'plot': 'full',
                'type': 'movie'
            }
            
            if imdb_id:
                params['i'] = imdb_id
            elif title:
                params['t'] = title
                if year:
                    params['y'] = year
            else:
                return None
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('Response') == 'True':
                        return self._format_movie_details(data)
                
            return None
            
        except Exception as e:
            logger.error(f"Failed to get OMDB movie details: {e}")
            return None
    
    def _format_movie_result(self, movie: Dict[str, Any]) -> Dict[str, Any]:
        """Format movie search result"""
        return {
            'imdb_id': movie.get('imdbID'),
            'title': movie.get('Title'),
            'year': movie.get('Year'),
            'type': movie.get('Type'),
            'poster_url': movie.get('Poster') if movie.get('Poster') != 'N/A' else None,
            'provider': 'omdb'
        }
    
    def _format_movie_details(self, movie: Dict[str, Any]) -> MovieData:
        """Format detailed movie data"""
        # Parse genres
        genres = []
        if movie.get('Genre') and movie.get('Genre') != 'N/A':
            genres = [g.strip() for g in movie.get('Genre').split(',')]
        
        # Parse cast
        cast = []
        if movie.get('Actors') and movie.get('Actors') != 'N/A':
            actors = [actor.strip() for actor in movie.get('Actors').split(',')]
            cast = [{'name': actor, 'character': '', 'profile_url': None} for actor in actors]
        
        # Parse crew
        crew = []
        if movie.get('Director') and movie.get('Director') != 'N/A':
            directors = [director.strip() for director in movie.get('Director').split(',')]
            crew.extend([{'name': director, 'job': 'Director', 'profile_url': None} for director in directors])
        
        if movie.get('Writer') and movie.get('Writer') != 'N/A':
            writers = [writer.strip() for writer in movie.get('Writer').split(',')]
            crew.extend([{'name': writer, 'job': 'Writer', 'profile_url': None} for writer in writers])
        
        # Parse rating
        rating = None
        if movie.get('imdbRating') and movie.get('imdbRating') != 'N/A':
            try:
                rating = float(movie.get('imdbRating'))
            except ValueError:
                pass
        
        # Parse runtime
        runtime = None
        if movie.get('Runtime') and movie.get('Runtime') != 'N/A':
            try:
                runtime = int(movie.get('Runtime').split()[0])
            except (ValueError, IndexError):
                pass
        
        return MovieData(
            external_id=movie.get('imdbID', ''),
            title=movie.get('Title', ''),
            original_title=movie.get('Title', ''),
            overview=movie.get('Plot', ''),
            release_date=self._parse_date(movie.get('Released')),
            runtime=runtime,
            genres=genres,
            rating=rating,
            vote_count=None,
            poster_url=movie.get('Poster') if movie.get('Poster') != 'N/A' else None,
            backdrop_url=None,
            trailer_url=None,
            cast=cast,
            crew=crew,
            production_companies=[],
            budget=None,
            revenue=None,
            languages=[movie.get('Language', '')] if movie.get('Language') != 'N/A' else [],
            countries=[movie.get('Country', '')] if movie.get('Country') != 'N/A' else [],
            status='Released',
            tagline=None,
            provider=MovieProvider.OMDB,
            raw_data=movie
        )
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if date_str and date_str != 'N/A':
            try:
                return datetime.strptime(date_str, '%d %b %Y').date()
            except ValueError:
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
        return None

class MovieDatabaseService:
    """Unified movie database service with multiple providers"""
    
    def __init__(self):
        self.providers = {}
        self.default_provider = MovieProvider.TMDB
        
    async def __aenter__(self):
        # Initialize providers with API keys
        if os.getenv('TMDB_API_KEY'):
            self.providers[MovieProvider.TMDB] = TMDBService()
            await self.providers[MovieProvider.TMDB].__aenter__()
        
        if os.getenv('OMDB_API_KEY'):
            self.providers[MovieProvider.OMDB] = OMDBService()
            await self.providers[MovieProvider.OMDB].__aenter__()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for provider in self.providers.values():
            if hasattr(provider, '__aexit__'):
                await provider.__aexit__(exc_type, exc_val, exc_tb)
    
    async def search_movies(
        self, 
        query: str, 
        page: int = 1, 
        year: int = None, 
        provider: MovieProvider = None
    ) -> Dict[str, Any]:
        """Search for movies using specified or default provider"""
        provider = provider or self.default_provider
        
        if provider in self.providers:
            return await self.providers[provider].search_movies(query, page, year)
        
        logger.error(f"Provider {provider} not available")
        return {'results': [], 'total_results': 0, 'current_page': page}
    
    async def get_movie_details(
        self, 
        movie_id: str, 
        provider: MovieProvider = None,
        imdb_id: str = None,
        title: str = None,
        year: int = None
    ) -> Optional[MovieData]:
        """Get detailed movie information"""
        provider = provider or self.default_provider
        
        if provider in self.providers:
            if provider == MovieProvider.TMDB:
                return await self.providers[provider].get_movie_details(movie_id)
            elif provider == MovieProvider.OMDB:
                return await self.providers[provider].get_movie_details(imdb_id, title, year)
        
        logger.error(f"Provider {provider} not available")
        return None
    
    async def get_popular_movies(
        self, 
        page: int = 1, 
        provider: MovieProvider = None
    ) -> Dict[str, Any]:
        """Get popular movies"""
        provider = provider or self.default_provider
        
        if provider == MovieProvider.TMDB and provider in self.providers:
            return await self.providers[provider].get_popular_movies(page)
        
        # Fallback to search if provider doesn't support popular movies
        return await self.search_movies("popular", page)
    
    async def get_movie_recommendations(
        self, 
        movie_id: str, 
        page: int = 1, 
        provider: MovieProvider = None
    ) -> List[Dict[str, Any]]:
        """Get movie recommendations"""
        provider = provider or self.default_provider
        
        if provider == MovieProvider.TMDB and provider in self.providers:
            return await self.providers[provider].get_movie_recommendations(movie_id, page)
        
        return []
    
    async def cross_reference_movie(self, tmdb_id: str = None, imdb_id: str = None, title: str = None) -> Dict[str, MovieData]:
        """Get movie data from multiple providers for cross-reference"""
        results = {}
        
        if tmdb_id and MovieProvider.TMDB in self.providers:
            tmdb_data = await self.providers[MovieProvider.TMDB].get_movie_details(tmdb_id)
            if tmdb_data:
                results['tmdb'] = tmdb_data
        
        if (imdb_id or title) and MovieProvider.OMDB in self.providers:
            omdb_data = await self.providers[MovieProvider.OMDB].get_movie_details(imdb_id, title)
            if omdb_data:
                results['omdb'] = omdb_data
        
        return results
    
    def get_available_providers(self) -> List[MovieProvider]:
        """Get list of available providers"""
        return list(self.providers.keys())
    
    async def sync_movie_data(self, local_movie_id: str, external_ids: Dict[str, str]) -> Dict[str, Any]:
        """Sync movie data from external sources"""
        sync_results = {
            'local_movie_id': local_movie_id,
            'updated_fields': [],
            'errors': [],
            'provider_data': {}
        }
        
        try:
            # Get data from all available providers
            for provider in self.providers:
                provider_id = external_ids.get(provider.value)
                if provider_id:
                    movie_data = await self.get_movie_details(
                        movie_id=provider_id if provider == MovieProvider.TMDB else None,
                        imdb_id=provider_id if provider == MovieProvider.OMDB else None,
                        provider=provider
                    )
                    
                    if movie_data:
                        sync_results['provider_data'][provider.value] = asdict(movie_data)
            
            # Here you would implement logic to merge and update local database
            # This is a placeholder for the actual database update logic
            
        except Exception as e:
            sync_results['errors'].append(str(e))
        
        return sync_results

# Global movie database service
movie_db_service = MovieDatabaseService()

# Utility functions
async def get_movie_by_imdb_id(imdb_id: str) -> Optional[MovieData]:
    """Get movie details by IMDB ID"""
    async with movie_db_service as service:
        return await service.get_movie_details(
            movie_id=None,
            imdb_id=imdb_id,
            provider=MovieProvider.OMDB
        )

async def search_movies_all_providers(query: str) -> Dict[str, Any]:
    """Search movies across all available providers"""
    async with movie_db_service as service:
        results = {}
        
        for provider in service.get_available_providers():
            try:
                provider_results = await service.search_movies(query, provider=provider)
                results[provider.value] = provider_results
            except Exception as e:
                logger.error(f"Search failed for provider {provider}: {e}")
                results[provider.value] = {'error': str(e)}
        
        return results