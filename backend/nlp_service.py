"""
Natural Language Processing Service
Advanced NLP for review analysis, sentiment classification, content moderation, and chatbot
"""

import asyncio
import logging
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from collections import Counter, defaultdict

# NLP Libraries
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.sentiment import SentimentIntensityAnalyzer
import spacy
from textblob import TextBlob

# Machine Learning
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score
from sklearn.cluster import KMeans
import joblib

# Deep Learning
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
    nltk.download('omw-1.4', quiet=True)
except Exception as e:
    logger.warning(f"NLTK download warning: {e}")

@dataclass
class ReviewAnalysis:
    """Review analysis result structure"""
    review_id: str
    text: str
    sentiment: str  # positive, negative, neutral
    sentiment_score: float  # -1 to 1
    confidence: float
    emotions: Dict[str, float]
    topics: List[str]
    key_phrases: List[str]
    language: str
    toxicity_score: float
    is_spam: bool
    rating_prediction: float
    word_count: int
    analyzed_at: datetime

@dataclass
class SentimentSummary:
    """Sentiment analysis summary"""
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    average_sentiment: float
    sentiment_trend: List[Dict[str, Any]]
    top_positive_themes: List[str]
    top_negative_themes: List[str]
    improvement_suggestions: List[str]

@dataclass
class ChatbotResponse:
    """Chatbot response structure"""
    response_text: str
    intent: str
    confidence: float
    entities: Dict[str, Any]
    follow_up_questions: List[str]
    requires_human: bool = False
    context_id: str = None

class SentimentAnalyzer:
    """Advanced sentiment analysis using multiple approaches"""
    
    def __init__(self):
        # Initialize NLTK sentiment analyzer
        self.vader_analyzer = SentimentIntensityAnalyzer()
        
        # Initialize spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, using basic features")
            self.nlp = None
        
        # Initialize lemmatizer
        self.lemmatizer = WordNetLemmatizer()
        
        # Initialize stop words
        self.stop_words = set(stopwords.words('english'))
        
        # Custom movie-related sentiment words
        self.movie_sentiment_words = {
            'positive': [
                'amazing', 'brilliant', 'excellent', 'fantastic', 'incredible',
                'outstanding', 'spectacular', 'wonderful', 'masterpiece', 'thrilling',
                'captivating', 'engaging', 'entertaining', 'hilarious', 'heartwarming',
                'stunning', 'breathtaking', 'compelling', 'gripping', 'riveting'
            ],
            'negative': [
                'terrible', 'awful', 'horrible', 'boring', 'disappointing',
                'waste', 'pointless', 'ridiculous', 'stupid', 'annoying',
                'confusing', 'poorly', 'badly', 'worst', 'unwatchable',
                'overrated', 'predictable', 'cliche', 'dull', 'tedious'
            ]
        }
        
        # Initialize transformer model for advanced sentiment
        self.transformer_model = None
        self._load_transformer_model()
    
    def _load_transformer_model(self):
        """Load pre-trained transformer model for sentiment analysis"""
        try:
            self.transformer_model = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                return_all_scores=True
            )
            logger.info("Transformer sentiment model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load transformer model: {e}")
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        
        # Remove special characters but keep punctuation for sentiment
        text = re.sub(r'[^a-zA-Z0-9\s.,!?]', '', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Comprehensive sentiment analysis"""
        
        preprocessed_text = self.preprocess_text(text)
        
        # VADER sentiment analysis
        vader_scores = self.vader_analyzer.polarity_scores(text)
        
        # TextBlob sentiment analysis
        blob = TextBlob(text)
        textblob_sentiment = blob.sentiment
        
        # Transformer-based sentiment (if available)
        transformer_scores = None
        if self.transformer_model:
            try:
                transformer_results = self.transformer_model(text[:512])  # Limit input length
                transformer_scores = {
                    result['label'].lower(): result['score']
                    for result in transformer_results[0]
                }
            except Exception as e:
                logger.warning(f"Transformer sentiment analysis failed: {e}")
        
        # Custom movie sentiment analysis
        movie_sentiment = self._analyze_movie_sentiment(preprocessed_text)
        
        # Combine all sentiment scores
        combined_sentiment = self._combine_sentiment_scores(
            vader_scores, textblob_sentiment, transformer_scores, movie_sentiment
        )
        
        return combined_sentiment
    
    def _analyze_movie_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment using movie-specific vocabulary"""
        
        words = word_tokenize(text.lower())
        
        positive_count = sum(1 for word in words if word in self.movie_sentiment_words['positive'])
        negative_count = sum(1 for word in words if word in self.movie_sentiment_words['negative'])
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
        
        pos_ratio = positive_count / total_sentiment_words
        neg_ratio = negative_count / total_sentiment_words
        neu_ratio = 1.0 - pos_ratio - neg_ratio
        
        compound = pos_ratio - neg_ratio
        
        return {
            'compound': compound,
            'pos': pos_ratio,
            'neu': neu_ratio,
            'neg': neg_ratio
        }
    
    def _combine_sentiment_scores(self, vader_scores: Dict, textblob_sentiment,
                                transformer_scores: Optional[Dict], 
                                movie_sentiment: Dict) -> Dict[str, Any]:
        """Combine sentiment scores from different analyzers"""
        
        # Extract sentiment values
        vader_compound = vader_scores['compound']
        textblob_polarity = textblob_sentiment.polarity
        
        # Weights for different methods
        weights = {
            'vader': 0.3,
            'textblob': 0.2,
            'transformer': 0.35 if transformer_scores else 0.0,
            'movie_custom': 0.15
        }
        
        # Normalize weights if transformer is not available
        if not transformer_scores:
            total_weight = sum(weights.values())
            weights = {k: v/total_weight for k, v in weights.items()}
        
        # Calculate weighted sentiment
        combined_score = (
            vader_compound * weights['vader'] +
            textblob_polarity * weights['textblob'] +
            movie_sentiment['compound'] * weights['movie_custom']
        )
        
        # Add transformer score if available
        if transformer_scores:
            # Convert transformer labels to numeric score
            transformer_score = 0.0
            if 'positive' in transformer_scores:
                transformer_score = transformer_scores['positive'] - transformer_scores.get('negative', 0)
            elif 'label_2' in transformer_scores:  # Some models use different labels
                transformer_score = transformer_scores['label_2'] - transformer_scores.get('label_0', 0)
            
            combined_score += transformer_score * weights['transformer']
        
        # Determine sentiment label
        if combined_score >= 0.1:
            sentiment_label = 'positive'
        elif combined_score <= -0.1:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        # Calculate confidence based on agreement between methods
        confidence = self._calculate_confidence(
            vader_compound, textblob_polarity, transformer_scores, movie_sentiment['compound']
        )
        
        return {
            'sentiment': sentiment_label,
            'score': combined_score,
            'confidence': confidence,
            'individual_scores': {
                'vader': vader_scores,
                'textblob': textblob_polarity,
                'transformer': transformer_scores,
                'movie_custom': movie_sentiment
            }
        }
    
    def _calculate_confidence(self, vader: float, textblob: float, 
                            transformer: Optional[Dict], movie_custom: float) -> float:
        """Calculate confidence based on agreement between sentiment analyzers"""
        
        scores = [vader, textblob, movie_custom]
        
        if transformer:
            # Convert transformer to comparable scale
            transformer_score = 0.0
            if 'positive' in transformer:
                transformer_score = transformer['positive'] - transformer.get('negative', 0)
            scores.append(transformer_score)
        
        # Calculate standard deviation of scores (lower = more agreement)
        std_dev = np.std(scores)
        
        # Convert to confidence score (0-1)
        confidence = max(0.0, 1.0 - std_dev)
        
        return confidence

class EmotionAnalyzer:
    """Emotion detection in text"""
    
    def __init__(self):
        # Emotion lexicon (simplified version)
        self.emotion_lexicon = {
            'joy': ['happy', 'joy', 'excited', 'thrilled', 'delighted', 'cheerful', 'elated', 'jubilant'],
            'sadness': ['sad', 'depressed', 'melancholy', 'gloomy', 'sorrowful', 'dejected', 'downhearted'],
            'anger': ['angry', 'furious', 'mad', 'irritated', 'annoyed', 'outraged', 'livid', 'irate'],
            'fear': ['scared', 'afraid', 'terrified', 'frightened', 'anxious', 'worried', 'nervous'],
            'surprise': ['surprised', 'amazed', 'astonished', 'shocked', 'stunned', 'startled'],
            'disgust': ['disgusted', 'revolted', 'repulsed', 'sickened', 'nauseated'],
            'anticipation': ['excited', 'eager', 'hopeful', 'expectant', 'optimistic']
        }
    
    def analyze_emotions(self, text: str) -> Dict[str, float]:
        """Analyze emotions in text"""
        
        words = word_tokenize(text.lower())
        emotion_scores = {emotion: 0.0 for emotion in self.emotion_lexicon}
        
        for word in words:
            for emotion, emotion_words in self.emotion_lexicon.items():
                if word in emotion_words:
                    emotion_scores[emotion] += 1.0
        
        # Normalize scores
        total_emotion_words = sum(emotion_scores.values())
        if total_emotion_words > 0:
            emotion_scores = {
                emotion: score / total_emotion_words 
                for emotion, score in emotion_scores.items()
            }
        
        return emotion_scores

class TopicExtractor:
    """Topic modeling and key phrase extraction"""
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3)
        )
        self.kmeans_model = KMeans(n_clusters=5, random_state=42)
        
        # Movie-specific topics
        self.movie_topics = {
            'plot': ['story', 'plot', 'narrative', 'storyline', 'script'],
            'acting': ['acting', 'performance', 'actor', 'actress', 'cast'],
            'visuals': ['visual', 'cinematography', 'effects', 'graphics', 'animation'],
            'audio': ['music', 'soundtrack', 'sound', 'audio', 'score'],
            'direction': ['director', 'direction', 'directing', 'filmmaking'],
            'pacing': ['pacing', 'slow', 'fast', 'boring', 'exciting']
        }
    
    def extract_topics(self, texts: List[str]) -> List[List[str]]:
        """Extract topics from multiple texts using clustering"""
        
        if len(texts) < 2:
            return [self.extract_movie_topics(texts[0])] if texts else []
        
        try:
            # Vectorize texts
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            
            # Perform clustering
            clusters = self.kmeans_model.fit_predict(tfidf_matrix)
            
            # Extract top terms for each cluster
            feature_names = self.tfidf_vectorizer.get_feature_names_out()
            cluster_topics = []
            
            for i in range(self.kmeans_model.n_clusters):
                # Get texts in this cluster
                cluster_texts = [texts[j] for j in range(len(texts)) if clusters[j] == i]
                
                if cluster_texts:
                    # Get cluster centroid
                    cluster_center = self.kmeans_model.cluster_centers_[i]
                    
                    # Get top terms
                    top_indices = cluster_center.argsort()[-10:][::-1]
                    top_terms = [feature_names[idx] for idx in top_indices]
                    
                    cluster_topics.append(top_terms)
            
            return cluster_topics
            
        except Exception as e:
            logger.error(f"Topic extraction failed: {e}")
            return [self.extract_movie_topics(text) for text in texts]
    
    def extract_movie_topics(self, text: str) -> List[str]:
        """Extract movie-specific topics from single text"""
        
        words = word_tokenize(text.lower())
        found_topics = []
        
        for topic, topic_words in self.movie_topics.items():
            if any(word in words for word in topic_words):
                found_topics.append(topic)
        
        return found_topics if found_topics else ['general']
    
    def extract_key_phrases(self, text: str, num_phrases: int = 5) -> List[str]:
        """Extract key phrases using TF-IDF"""
        
        try:
            # Create single-document vectorizer
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words='english',
                ngram_range=(1, 3)
            )
            
            tfidf_matrix = vectorizer.fit_transform([text])
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Get top phrases
            top_indices = tfidf_scores.argsort()[-num_phrases:][::-1]
            key_phrases = [feature_names[idx] for idx in top_indices if tfidf_scores[idx] > 0]
            
            return key_phrases
            
        except Exception as e:
            logger.warning(f"Key phrase extraction failed: {e}")
            return []

class ContentModerator:
    """Content moderation for toxicity, spam, and inappropriate content"""
    
    def __init__(self):
        # Toxicity keywords (simplified)
        self.toxicity_keywords = {
            'hate_speech': ['hate', 'stupid', 'idiot', 'moron'],
            'profanity': ['damn', 'hell'],  # Add more as needed
            'spam_indicators': ['click here', 'buy now', 'free money', 'limited time']
        }
        
        # Spam patterns
        self.spam_patterns = [
            r'\b(?:http|www)\b',  # URLs
            r'\b\d{10,}\b',  # Long numbers (phone numbers)
            r'[A-Z]{5,}',  # All caps words
            r'(.)\1{3,}'  # Repeated characters
        ]
        
        # Load pre-trained toxicity classifier if available
        self.toxicity_classifier = None
        self._load_toxicity_classifier()
    
    def _load_toxicity_classifier(self):
        """Load pre-trained toxicity detection model"""
        try:
            # Try to load Perspective API or similar model
            # For demo, we'll use a simple rule-based approach
            pass
        except Exception as e:
            logger.warning(f"Could not load toxicity classifier: {e}")
    
    def moderate_content(self, text: str) -> Dict[str, Any]:
        """Comprehensive content moderation"""
        
        # Calculate toxicity score
        toxicity_score = self._calculate_toxicity_score(text)
        
        # Check for spam
        is_spam = self._detect_spam(text)
        
        # Language detection
        language = self._detect_language(text)
        
        # Content flags
        flags = self._check_content_flags(text)
        
        return {
            'toxicity_score': toxicity_score,
            'is_spam': is_spam,
            'language': language,
            'flags': flags,
            'is_safe': toxicity_score < 0.7 and not is_spam and len(flags) == 0
        }
    
    def _calculate_toxicity_score(self, text: str) -> float:
        """Calculate toxicity score (0-1)"""
        
        words = word_tokenize(text.lower())
        total_words = len(words)
        
        if total_words == 0:
            return 0.0
        
        toxicity_count = 0
        
        for category, toxic_words in self.toxicity_keywords.items():
            for word in words:
                if word in toxic_words:
                    toxicity_count += 1
        
        # Check for repeated caps (indicates shouting)
        caps_count = sum(1 for char in text if char.isupper())
        if len(text) > 0 and caps_count / len(text) > 0.5:
            toxicity_count += 2
        
        # Normalize to 0-1 scale
        toxicity_score = min(toxicity_count / total_words, 1.0)
        
        return toxicity_score
    
    def _detect_spam(self, text: str) -> bool:
        """Detect spam content"""
        
        spam_indicators = 0
        
        # Check for spam keywords
        words = word_tokenize(text.lower())
        for word in words:
            if word in self.toxicity_keywords['spam_indicators']:
                spam_indicators += 1
        
        # Check for spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                spam_indicators += 1
        
        # Check text characteristics
        if len(text) > 0:
            # High ratio of numbers
            digit_ratio = sum(1 for char in text if char.isdigit()) / len(text)
            if digit_ratio > 0.3:
                spam_indicators += 1
            
            # Excessive punctuation
            punct_ratio = sum(1 for char in text if not char.isalnum() and not char.isspace()) / len(text)
            if punct_ratio > 0.2:
                spam_indicators += 1
        
        return spam_indicators >= 2
    
    def _detect_language(self, text: str) -> str:
        """Simple language detection"""
        try:
            blob = TextBlob(text)
            detected_lang = blob.detect_language()
            return detected_lang if detected_lang else 'en'
        except:
            return 'unknown'
    
    def _check_content_flags(self, text: str) -> List[str]:
        """Check for various content flags"""
        
        flags = []
        
        # Check length
        if len(text.split()) < 3:
            flags.append('too_short')
        elif len(text.split()) > 1000:
            flags.append('too_long')
        
        # Check for excessive repetition
        words = text.split()
        word_counts = Counter(words)
        most_common_count = word_counts.most_common(1)[0][1] if word_counts else 0
        
        if most_common_count > len(words) * 0.3:
            flags.append('excessive_repetition')
        
        # Check for all caps
        if text.isupper() and len(text) > 10:
            flags.append('all_caps')
        
        return flags

class MovieChatbot:
    """Intelligent chatbot for movie-related queries"""
    
    def __init__(self):
        # Intent patterns
        self.intent_patterns = {
            'movie_search': [
                r'\b(?:find|search|look for|show me)\b.*\bmovie',
                r'\bwhat.*movie.*\b(?:recommend|suggest)',
                r'\bmovie.*\b(?:about|with|starring)'
            ],
            'showtimes': [
                r'\b(?:showtime|show time|schedule|when)\b',
                r'\bwhat time\b.*\bshow',
                r'\b(?:screening|playing)\b.*\btime'
            ],
            'booking': [
                r'\b(?:book|reserve|buy)\b.*\bticket',
                r'\bticket.*\b(?:booking|reservation)',
                r'\bhow.*\bbook'
            ],
            'theater_info': [
                r'\b(?:theater|cinema|location)\b',
                r'\bwhere.*\b(?:playing|showing)',
                r'\b(?:address|direction)\b'
            ],
            'price_info': [
                r'\b(?:price|cost|how much)\b',
                r'\bticket.*\bprice',
                r'\bhow much.*\bticket'
            ],
            'greeting': [
                r'\b(?:hello|hi|hey|good morning|good afternoon|good evening)\b',
                r'\bwhat\'?s up\b',
                r'\bhow are you\b'
            ],
            'help': [
                r'\bhelp\b',
                r'\bwhat.*\bcan.*\bdo\b',
                r'\bcommands?\b'
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'movie_title': r'\b[A-Z][a-z]*(?:\s+[A-Z][a-z]*)*\b(?=.*(?:movie|film))',
            'time': r'\b(?:\d{1,2}:\d{2}|morning|afternoon|evening|night)\b',
            'date': r'\b(?:today|tomorrow|this\s+week|next\s+week|\d{1,2}/\d{1,2})\b',
            'genre': r'\b(?:action|comedy|drama|horror|romance|thriller|sci-fi|fantasy)\b'
        }
        
        # Response templates
        self.response_templates = {
            'movie_search': [
                "I can help you find movies! What genre or type of movie are you looking for?",
                "Let me help you discover some great movies. Do you have any preferences?",
                "I'd be happy to recommend movies! Tell me what you're in the mood for."
            ],
            'showtimes': [
                "I can show you movie showtimes. Which movie and location are you interested in?",
                "Let me check the showtimes for you. What movie would you like to see?",
                "I can help with showtimes! Please tell me the movie and your preferred theater."
            ],
            'booking': [
                "I can help you book tickets! Which movie would you like to see?",
                "Great! Let's get your tickets booked. What movie and showtime work for you?",
                "I'd be happy to help with ticket booking. Please specify the movie and time."
            ],
            'theater_info': [
                "I can provide theater information. Which location are you interested in?",
                "Let me help you find theater details. What area are you looking in?",
                "I can show you theater locations and information. Where would you like to go?"
            ],
            'price_info': [
                "Ticket prices vary by theater and showtime. Let me check specific pricing for you.",
                "I can show you ticket prices. Which theater and movie are you interested in?",
                "Pricing depends on the theater and time. What specific show are you asking about?"
            ],
            'greeting': [
                "Hello! I'm here to help with all your movie needs. What can I do for you today?",
                "Hi there! I can help you find movies, check showtimes, and book tickets. How can I assist?",
                "Welcome! I'm your movie assistant. What would you like to know about movies today?"
            ],
            'help': [
                "I can help you with:\n• Finding movies and recommendations\n• Checking showtimes\n• Booking tickets\n• Theater information\n• Movie reviews and ratings",
                "Here's what I can do:\n- Search for movies\n- Show theater schedules\n- Help book tickets\n- Provide movie information\n- Answer questions about theaters",
                "I'm here to help with movies! I can find showtimes, help book tickets, recommend movies, and answer questions about theaters."
            ],
            'fallback': [
                "I'm not sure I understood that. Could you rephrase your question about movies?",
                "I didn't catch that. I can help with movie searches, showtimes, and bookings. What would you like to know?",
                "I'm here to help with movie-related questions. Could you be more specific about what you need?"
            ]
        }
    
    def process_message(self, message: str, user_id: str = None, context: Dict[str, Any] = None) -> ChatbotResponse:
        """Process user message and generate response"""
        
        # Detect intent
        intent = self._detect_intent(message)
        
        # Extract entities
        entities = self._extract_entities(message)
        
        # Generate response
        response_text = self._generate_response(intent, entities, context)
        
        # Calculate confidence
        confidence = self._calculate_response_confidence(intent, entities)
        
        # Generate follow-up questions
        follow_up_questions = self._generate_follow_up_questions(intent, entities)
        
        # Determine if human assistance needed
        requires_human = confidence < 0.6 or intent == 'complex_query'
        
        return ChatbotResponse(
            response_text=response_text,
            intent=intent,
            confidence=confidence,
            entities=entities,
            follow_up_questions=follow_up_questions,
            requires_human=requires_human,
            context_id=f"ctx_{user_id}_{datetime.now().timestamp()}" if user_id else None
        )
    
    def _detect_intent(self, message: str) -> str:
        """Detect user intent from message"""
        
        message_lower = message.lower()
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        return 'unknown'
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities from message"""
        
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                entities[entity_type] = matches
        
        return entities
    
    def _generate_response(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Generate appropriate response based on intent and entities"""
        
        if intent in self.response_templates:
            responses = self.response_templates[intent]
            
            # Select response (could be made more sophisticated)
            import random
            base_response = random.choice(responses)
            
            # Customize response based on entities
            if entities:
                if 'movie_title' in entities:
                    movie_titles = entities['movie_title']
                    base_response += f" I see you're interested in {', '.join(movie_titles)}."
                
                if 'genre' in entities:
                    genres = entities['genre']
                    base_response += f" {', '.join(genres).title()} movies are great choices!"
            
            return base_response
        
        else:
            # Fallback response
            return random.choice(self.response_templates['fallback'])
    
    def _calculate_response_confidence(self, intent: str, entities: Dict[str, Any]) -> float:
        """Calculate confidence in the response"""
        
        # Base confidence based on intent detection
        if intent == 'unknown':
            confidence = 0.3
        elif intent in ['greeting', 'help']:
            confidence = 0.9
        else:
            confidence = 0.7
        
        # Boost confidence if entities are detected
        if entities:
            confidence = min(confidence + 0.2, 1.0)
        
        return confidence
    
    def _generate_follow_up_questions(self, intent: str, entities: Dict[str, Any]) -> List[str]:
        """Generate relevant follow-up questions"""
        
        follow_ups = []
        
        if intent == 'movie_search':
            follow_ups = [
                "What genre do you prefer?",
                "Are you looking for new releases or classics?",
                "Any specific actors you'd like to see?"
            ]
        
        elif intent == 'showtimes':
            follow_ups = [
                "What's your preferred time of day?",
                "Which theater location works best for you?",
                "Are you flexible with dates?"
            ]
        
        elif intent == 'booking':
            follow_ups = [
                "How many tickets do you need?",
                "Do you have a seating preference?",
                "Would you like to add any concessions?"
            ]
        
        return follow_ups

class NLPService:
    """Main NLP service orchestrator"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.emotion_analyzer = EmotionAnalyzer()
        self.topic_extractor = TopicExtractor()
        self.content_moderator = ContentModerator()
        self.chatbot = MovieChatbot()
        
        # Cache for expensive operations
        self.analysis_cache = {}
    
    async def analyze_review(self, review_id: str, text: str) -> ReviewAnalysis:
        """Comprehensive review analysis"""
        
        try:
            # Check cache
            cache_key = f"review_{hashlib.md5(text.encode()).hexdigest()}"
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]
            
            # Sentiment analysis
            sentiment_result = self.sentiment_analyzer.analyze_sentiment(text)
            
            # Emotion analysis
            emotions = self.emotion_analyzer.analyze_emotions(text)
            
            # Topic extraction
            topics = self.topic_extractor.extract_movie_topics(text)
            
            # Key phrase extraction
            key_phrases = self.topic_extractor.extract_key_phrases(text)
            
            # Content moderation
            moderation_result = self.content_moderator.moderate_content(text)
            
            # Predict rating from sentiment (simple mapping)
            predicted_rating = self._sentiment_to_rating(sentiment_result['score'])
            
            # Create analysis result
            analysis = ReviewAnalysis(
                review_id=review_id,
                text=text,
                sentiment=sentiment_result['sentiment'],
                sentiment_score=sentiment_result['score'],
                confidence=sentiment_result['confidence'],
                emotions=emotions,
                topics=topics,
                key_phrases=key_phrases,
                language=moderation_result['language'],
                toxicity_score=moderation_result['toxicity_score'],
                is_spam=moderation_result['is_spam'],
                rating_prediction=predicted_rating,
                word_count=len(text.split()),
                analyzed_at=datetime.now()
            )
            
            # Cache result
            self.analysis_cache[cache_key] = analysis
            
            return analysis
            
        except Exception as e:
            logger.error(f"Review analysis failed for {review_id}: {e}")
            raise
    
    async def analyze_multiple_reviews(self, reviews: List[Tuple[str, str]]) -> SentimentSummary:
        """Analyze multiple reviews and generate summary"""
        
        try:
            analyses = []
            
            # Analyze each review
            for review_id, text in reviews:
                analysis = await self.analyze_review(review_id, text)
                analyses.append(analysis)
            
            # Generate summary
            total_reviews = len(analyses)
            positive_count = len([a for a in analyses if a.sentiment == 'positive'])
            negative_count = len([a for a in analyses if a.sentiment == 'negative'])
            neutral_count = total_reviews - positive_count - negative_count
            
            # Calculate average sentiment
            avg_sentiment = np.mean([a.sentiment_score for a in analyses]) if analyses else 0.0
            
            # Extract themes
            all_topics = []
            positive_topics = []
            negative_topics = []
            
            for analysis in analyses:
                all_topics.extend(analysis.topics)
                if analysis.sentiment == 'positive':
                    positive_topics.extend(analysis.topics)
                elif analysis.sentiment == 'negative':
                    negative_topics.extend(analysis.topics)
            
            # Get top themes
            positive_theme_counts = Counter(positive_topics)
            negative_theme_counts = Counter(negative_topics)
            
            top_positive_themes = [theme for theme, _ in positive_theme_counts.most_common(5)]
            top_negative_themes = [theme for theme, _ in negative_theme_counts.most_common(5)]
            
            # Generate improvement suggestions
            improvement_suggestions = self._generate_improvement_suggestions(
                negative_theme_counts, analyses
            )
            
            # Create sentiment trend (simplified)
            sentiment_trend = [
                {
                    'date': (datetime.now() - timedelta(days=i)).isoformat(),
                    'sentiment_score': avg_sentiment + np.random.normal(0, 0.1)  # Mock trend
                }
                for i in range(7)
            ]
            
            summary = SentimentSummary(
                total_reviews=total_reviews,
                positive_count=positive_count,
                negative_count=negative_count,
                neutral_count=neutral_count,
                average_sentiment=avg_sentiment,
                sentiment_trend=sentiment_trend,
                top_positive_themes=top_positive_themes,
                top_negative_themes=top_negative_themes,
                improvement_suggestions=improvement_suggestions
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Multiple review analysis failed: {e}")
            raise
    
    def _sentiment_to_rating(self, sentiment_score: float) -> float:
        """Convert sentiment score to 1-5 rating prediction"""
        
        # Map sentiment score (-1 to 1) to rating (1 to 5)
        normalized_score = (sentiment_score + 1) / 2  # Convert to 0-1
        rating = 1 + (normalized_score * 4)  # Scale to 1-5
        
        return round(rating, 1)
    
    def _generate_improvement_suggestions(self, negative_themes: Counter, 
                                       analyses: List[ReviewAnalysis]) -> List[str]:
        """Generate improvement suggestions based on negative feedback"""
        
        suggestions = []
        
        if 'plot' in negative_themes:
            suggestions.append("Consider stories with stronger narrative structure")
        
        if 'acting' in negative_themes:
            suggestions.append("Focus on casting and performance quality")
        
        if 'pacing' in negative_themes:
            suggestions.append("Review editing and pacing in future selections")
        
        if 'visuals' in negative_themes:
            suggestions.append("Prioritize movies with better visual production")
        
        # Check overall toxicity
        avg_toxicity = np.mean([a.toxicity_score for a in analyses])
        if avg_toxicity > 0.3:
            suggestions.append("Implement stronger community guidelines")
        
        return suggestions[:5]  # Return top 5 suggestions
    
    async def process_chatbot_message(self, message: str, user_id: str = None, 
                                    context: Dict[str, Any] = None) -> ChatbotResponse:
        """Process chatbot message"""
        
        return self.chatbot.process_message(message, user_id, context)

# Global NLP service
nlp_service = NLPService()

# Utility functions
async def analyze_movie_review(review_id: str, review_text: str) -> ReviewAnalysis:
    """Analyze a single movie review"""
    return await nlp_service.analyze_review(review_id, review_text)

async def analyze_movie_reviews_batch(reviews: List[Tuple[str, str]]) -> SentimentSummary:
    """Analyze multiple reviews and get summary"""
    return await nlp_service.analyze_multiple_reviews(reviews)

async def chat_with_bot(message: str, user_id: str = None) -> ChatbotResponse:
    """Chat with movie recommendation bot"""
    return await nlp_service.process_chatbot_message(message, user_id)

def moderate_user_content(text: str) -> Dict[str, Any]:
    """Moderate user-generated content"""
    return nlp_service.content_moderator.moderate_content(text)