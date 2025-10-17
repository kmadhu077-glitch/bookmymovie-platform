"""
Predictive Analytics Service
Advanced forecasting and demand prediction using machine learning
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')

# Time series forecasting
try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("Statsmodels not available, using alternative forecasting methods")

# Deep learning for time series
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model, callbacks

logger = logging.getLogger(__name__)

@dataclass
class DemandForecast:
    """Demand forecast result structure"""
    forecast_id: str
    movie_id: str
    theater_id: str
    prediction_date: datetime
    forecasted_demand: float
    confidence_interval: Tuple[float, float]
    confidence_level: float
    factors_analyzed: List[str]
    model_used: str
    accuracy_score: float
    generated_at: datetime

@dataclass
class RevenueProjection:
    """Revenue projection structure"""
    projection_id: str
    time_period: str  # daily, weekly, monthly
    start_date: datetime
    end_date: datetime
    projected_revenue: float
    actual_revenue: Optional[float] = None
    variance: Optional[float] = None
    contributing_factors: List[Dict[str, Any]] = None
    seasonal_adjustments: Dict[str, float] = None
    risk_factors: List[str] = None

@dataclass
class CustomerBehaviorInsight:
    """Customer behavior prediction"""
    user_segment: str
    predicted_behavior: str
    probability: float
    behavioral_triggers: List[str]
    recommendation_actions: List[str]
    expected_value: float
    time_frame: str

class DemandPredictor:
    """Movie demand prediction using multiple ML models"""
    
    def __init__(self):
        # Models for ensemble prediction
        self.models = {
            'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
            'gradient_boost': GradientBoostingRegressor(n_estimators=100, random_state=42),
            'ridge_regression': Ridge(alpha=1.0),
            'lstm_model': None  # Will be built dynamically
        }
        
        # Feature scalers
        self.scalers = {}
        self.label_encoders = {}
        
        # Feature importance tracking
        self.feature_importance = {}
        
        # Model performance history
        self.model_performance = {
            'training_scores': {},
            'validation_scores': {},
            'prediction_accuracy': {}
        }
    
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for demand prediction"""
        
        features_df = data.copy()
        
        # Time-based features
        if 'date' in features_df.columns:
            features_df['date'] = pd.to_datetime(features_df['date'])
            features_df['day_of_week'] = features_df['date'].dt.dayofweek
            features_df['month'] = features_df['date'].dt.month
            features_df['quarter'] = features_df['date'].dt.quarter
            features_df['is_weekend'] = (features_df['day_of_week'] >= 5).astype(int)
            features_df['is_holiday'] = self._check_holidays(features_df['date'])
        
        # Movie features
        movie_features = [
            'genre_encoded', 'rating_encoded', 'runtime_minutes',
            'budget_millions', 'star_rating', 'director_popularity'
        ]
        
        # Theater features
        theater_features = [
            'theater_capacity', 'location_tier', 'premium_screens',
            'parking_availability', 'food_court_rating'
        ]
        
        # Weather and external features
        external_features = [
            'temperature', 'weather_condition_encoded', 'local_events',
            'competitor_releases', 'marketing_spend'
        ]
        
        # Encode categorical features
        categorical_columns = ['genre', 'rating', 'weather_condition', 'location_tier']
        for col in categorical_columns:
            if col in features_df.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    features_df[f'{col}_encoded'] = self.label_encoders[col].fit_transform(features_df[col].fillna('Unknown'))
                else:
                    features_df[f'{col}_encoded'] = self.label_encoders[col].transform(features_df[col].fillna('Unknown'))
        
        # Create interaction features
        if 'star_rating' in features_df.columns and 'marketing_spend' in features_df.columns:
            features_df['rating_marketing_interaction'] = features_df['star_rating'] * features_df['marketing_spend']
        
        if 'is_weekend' in features_df.columns and 'theater_capacity' in features_df.columns:
            features_df['weekend_capacity_interaction'] = features_df['is_weekend'] * features_df['theater_capacity']
        
        # Lag features (previous demand)
        if 'demand' in features_df.columns:
            features_df = features_df.sort_values('date')
            features_df['demand_lag_1'] = features_df['demand'].shift(1)
            features_df['demand_lag_7'] = features_df['demand'].shift(7)  # Previous week
            features_df['demand_rolling_mean_7'] = features_df['demand'].rolling(window=7).mean()
        
        return features_df
    
    def _check_holidays(self, dates: pd.Series) -> pd.Series:
        """Check if dates are holidays (simplified)"""
        
        # Major US holidays (simplified)
        holidays = [
            '2024-01-01', '2024-07-04', '2024-12-25', '2024-11-28',  # New Year, July 4th, Christmas, Thanksgiving
            '2025-01-01', '2025-07-04', '2025-12-25', '2025-11-27'
        ]
        
        holiday_dates = pd.to_datetime(holidays)
        return dates.dt.date.isin(holiday_dates.date).astype(int)
    
    def train_models(self, training_data: pd.DataFrame, target_column: str = 'demand'):
        """Train ensemble of demand prediction models"""
        
        logger.info("Preparing features for model training...")
        
        # Prepare features
        features_df = self.prepare_features(training_data)
        
        # Select feature columns (exclude non-feature columns)
        exclude_columns = ['date', target_column, 'movie_id', 'theater_id']
        feature_columns = [col for col in features_df.columns if col not in exclude_columns]
        
        X = features_df[feature_columns].fillna(0)
        y = features_df[target_column]
        
        # Scale features
        self.scalers['features'] = StandardScaler()
        X_scaled = self.scalers['features'].fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # Train traditional ML models
        for model_name, model in self.models.items():
            if model_name == 'lstm_model':
                continue  # Handle LSTM separately
            
            logger.info(f"Training {model_name}...")
            
            # Train model
            model.fit(X_train, y_train)
            
            # Evaluate model
            train_score = model.score(X_train, y_train)
            test_score = model.score(X_test, y_test)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_scaled, y, cv=5)
            
            # Store performance
            self.model_performance['training_scores'][model_name] = train_score
            self.model_performance['validation_scores'][model_name] = test_score
            self.model_performance['prediction_accuracy'][model_name] = cv_scores.mean()
            
            # Feature importance (if available)
            if hasattr(model, 'feature_importances_'):
                importance_dict = dict(zip(feature_columns, model.feature_importances_))
                self.feature_importance[model_name] = importance_dict
            
            logger.info(f"{model_name} - Train Score: {train_score:.4f}, Test Score: {test_score:.4f}, CV Score: {cv_scores.mean():.4f}")
        
        # Train LSTM model
        self._train_lstm_model(X_train, y_train, X_test, y_test)
        
        # Save models
        self._save_models()
        
        logger.info("Model training completed successfully!")
    
    def _train_lstm_model(self, X_train: np.ndarray, y_train: np.ndarray, 
                         X_test: np.ndarray, y_test: np.ndarray):
        """Train LSTM model for time series prediction"""
        
        try:
            logger.info("Training LSTM model...")
            
            # Reshape data for LSTM (samples, time steps, features)
            # For simplicity, we'll use sequence length of 1
            X_train_lstm = X_train.reshape((X_train.shape[0], 1, X_train.shape[1]))
            X_test_lstm = X_test.reshape((X_test.shape[0], 1, X_test.shape[1]))
            
            # Build LSTM model
            model = keras.Sequential([
                layers.LSTM(50, return_sequences=True, input_shape=(1, X_train.shape[1])),
                layers.Dropout(0.2),
                layers.LSTM(50, return_sequences=False),
                layers.Dropout(0.2),
                layers.Dense(25),
                layers.Dense(1)
            ])
            
            # Compile model
            model.compile(
                optimizer=keras.optimizers.Adam(learning_rate=0.001),
                loss='mse',
                metrics=['mae']
            )
            
            # Callbacks
            early_stopping = callbacks.EarlyStopping(
                monitor='val_loss', patience=10, restore_best_weights=True
            )
            
            reduce_lr = callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=5, min_lr=1e-7
            )
            
            # Train model
            history = model.fit(
                X_train_lstm, y_train,
                validation_data=(X_test_lstm, y_test),
                epochs=100,
                batch_size=32,
                callbacks=[early_stopping, reduce_lr],
                verbose=0
            )
            
            # Evaluate model
            train_loss = model.evaluate(X_train_lstm, y_train, verbose=0)[0]
            test_loss = model.evaluate(X_test_lstm, y_test, verbose=0)[0]
            
            # Store model and performance
            self.models['lstm_model'] = model
            self.model_performance['training_scores']['lstm_model'] = 1.0 - train_loss  # Convert loss to score-like metric
            self.model_performance['validation_scores']['lstm_model'] = 1.0 - test_loss
            self.model_performance['prediction_accuracy']['lstm_model'] = 1.0 - test_loss
            
            logger.info(f"LSTM - Train Loss: {train_loss:.4f}, Test Loss: {test_loss:.4f}")
            
        except Exception as e:
            logger.error(f"LSTM training failed: {e}")
            self.models['lstm_model'] = None
    
    def predict_demand(self, prediction_data: pd.DataFrame, ensemble: bool = True) -> np.ndarray:
        """Predict demand using trained models"""
        
        # Prepare features
        features_df = self.prepare_features(prediction_data)
        
        # Select feature columns
        exclude_columns = ['date', 'demand', 'movie_id', 'theater_id']
        feature_columns = [col for col in features_df.columns if col not in exclude_columns]
        
        X = features_df[feature_columns].fillna(0)
        
        # Scale features
        X_scaled = self.scalers['features'].transform(X)
        
        if ensemble:
            # Ensemble prediction
            predictions = []
            weights = []
            
            for model_name, model in self.models.items():
                if model is None:
                    continue
                
                if model_name == 'lstm_model':
                    # LSTM prediction
                    X_lstm = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
                    pred = model.predict(X_lstm, verbose=0).flatten()
                else:
                    # Traditional ML prediction
                    pred = model.predict(X_scaled)
                
                predictions.append(pred)
                
                # Weight by model performance
                model_weight = self.model_performance['prediction_accuracy'].get(model_name, 0.5)
                weights.append(model_weight)
            
            # Weighted ensemble
            if predictions:
                weighted_predictions = np.average(predictions, axis=0, weights=weights)
                return weighted_predictions
            else:
                logger.warning("No models available for prediction")
                return np.zeros(len(X))
        
        else:
            # Use best performing model
            best_model_name = max(
                self.model_performance['prediction_accuracy'].items(),
                key=lambda x: x[1]
            )[0]
            
            best_model = self.models[best_model_name]
            
            if best_model_name == 'lstm_model':
                X_lstm = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
                return best_model.predict(X_lstm, verbose=0).flatten()
            else:
                return best_model.predict(X_scaled)
    
    def calculate_prediction_confidence(self, prediction_data: pd.DataFrame, predictions: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate confidence intervals for predictions"""
        
        # Use model variance to estimate confidence
        individual_predictions = []
        
        features_df = self.prepare_features(prediction_data)
        exclude_columns = ['date', 'demand', 'movie_id', 'theater_id']
        feature_columns = [col for col in features_df.columns if col not in exclude_columns]
        
        X = features_df[feature_columns].fillna(0)
        X_scaled = self.scalers['features'].transform(X)
        
        for model_name, model in self.models.items():
            if model is None:
                continue
            
            if model_name == 'lstm_model':
                X_lstm = X_scaled.reshape((X_scaled.shape[0], 1, X_scaled.shape[1]))
                pred = model.predict(X_lstm, verbose=0).flatten()
            else:
                pred = model.predict(X_scaled)
            
            individual_predictions.append(pred)
        
        # Calculate standard deviation across models
        if len(individual_predictions) > 1:
            pred_std = np.std(individual_predictions, axis=0)
        else:
            # Fallback: use 10% of prediction as uncertainty
            pred_std = predictions * 0.1
        
        # 95% confidence interval (approximately ±2 standard deviations)
        lower_bound = predictions - 2 * pred_std
        upper_bound = predictions + 2 * pred_std
        
        # Ensure non-negative predictions
        lower_bound = np.maximum(lower_bound, 0)
        upper_bound = np.maximum(upper_bound, predictions)
        
        return lower_bound, upper_bound
    
    def _save_models(self):
        """Save trained models"""
        try:
            # Save traditional ML models
            for model_name, model in self.models.items():
                if model_name != 'lstm_model' and model is not None:
                    joblib.dump(model, f'models/demand_{model_name}.pkl')
            
            # Save LSTM model separately
            if self.models['lstm_model'] is not None:
                self.models['lstm_model'].save('models/demand_lstm_model.h5')
            
            # Save scalers and encoders
            joblib.dump(self.scalers, 'models/demand_scalers.pkl')
            joblib.dump(self.label_encoders, 'models/demand_encoders.pkl')
            
            # Save performance metrics
            with open('models/demand_performance.json', 'w') as f:
                json.dump(self.model_performance, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")

class RevenueForecaster:
    """Revenue forecasting using time series analysis"""
    
    def __init__(self):
        self.time_series_models = {}
        self.seasonal_patterns = {}
        self.trend_components = {}
    
    def analyze_revenue_patterns(self, revenue_data: pd.DataFrame):
        """Analyze historical revenue patterns"""
        
        # Ensure date column is datetime
        revenue_data['date'] = pd.to_datetime(revenue_data['date'])
        revenue_data = revenue_data.sort_values('date')
        
        # Set date as index for time series analysis
        ts_data = revenue_data.set_index('date')['revenue']
        
        if STATSMODELS_AVAILABLE:
            try:
                # Seasonal decomposition
                decomposition = seasonal_decompose(
                    ts_data.resample('D').sum(),  # Daily aggregation
                    model='multiplicative',
                    period=7  # Weekly seasonality
                )
                
                self.seasonal_patterns['weekly'] = decomposition.seasonal
                self.trend_components['linear'] = decomposition.trend
                
                logger.info("Seasonal decomposition completed")
                
            except Exception as e:
                logger.warning(f"Seasonal decomposition failed: {e}")
        
        # Calculate growth rates
        daily_revenue = ts_data.resample('D').sum()
        growth_rates = daily_revenue.pct_change().dropna()
        
        self.revenue_statistics = {
            'mean_daily_revenue': daily_revenue.mean(),
            'std_daily_revenue': daily_revenue.std(),
            'mean_growth_rate': growth_rates.mean(),
            'volatility': growth_rates.std(),
            'trend_direction': 'increasing' if daily_revenue.iloc[-30:].mean() > daily_revenue.iloc[-60:-30].mean() else 'decreasing'
        }
    
    def forecast_revenue(self, forecast_days: int = 30, confidence_level: float = 0.95) -> List[RevenueProjection]:
        """Forecast revenue for specified number of days"""
        
        forecasts = []
        
        try:
            base_revenue = self.revenue_statistics['mean_daily_revenue']
            volatility = self.revenue_statistics['std_daily_revenue']
            growth_rate = self.revenue_statistics['mean_growth_rate']
            
            for day in range(1, forecast_days + 1):
                forecast_date = datetime.now() + timedelta(days=day)
                
                # Simple trend + seasonal model
                trend_component = base_revenue * (1 + growth_rate) ** day
                
                # Add weekly seasonality (higher on weekends)
                seasonal_multiplier = 1.2 if forecast_date.weekday() >= 5 else 0.9
                
                # Add random variation
                random_factor = 1.0 + np.random.normal(0, volatility / base_revenue)
                
                projected_revenue = trend_component * seasonal_multiplier * random_factor
                
                # Calculate confidence interval
                confidence_margin = 1.96 * volatility  # 95% confidence
                
                # Risk factors
                risk_factors = []
                if forecast_date.weekday() == 0:  # Monday
                    risk_factors.append("Typically lower Monday performance")
                if day > 14:
                    risk_factors.append("Longer-term forecast uncertainty")
                
                forecast = RevenueProjection(
                    projection_id=f"rev_forecast_{forecast_date.strftime('%Y%m%d')}",
                    time_period="daily",
                    start_date=forecast_date,
                    end_date=forecast_date,
                    projected_revenue=projected_revenue,
                    contributing_factors=[
                        {"factor": "historical_trend", "impact": growth_rate},
                        {"factor": "seasonal_pattern", "impact": seasonal_multiplier - 1.0},
                        {"factor": "day_of_week", "impact": seasonal_multiplier}
                    ],
                    seasonal_adjustments={
                        "weekend_boost": seasonal_multiplier if seasonal_multiplier > 1.0 else 0.0,
                        "weekday_adjustment": seasonal_multiplier if seasonal_multiplier < 1.0 else 0.0
                    },
                    risk_factors=risk_factors
                )
                
                forecasts.append(forecast)
        
        except Exception as e:
            logger.error(f"Revenue forecasting failed: {e}")
        
        return forecasts

class CustomerBehaviorPredictor:
    """Predict customer behavior patterns"""
    
    def __init__(self):
        self.behavior_models = {}
        self.customer_segments = {}
        
    def analyze_customer_segments(self, customer_data: pd.DataFrame):
        """Analyze and create customer segments"""
        
        # Feature engineering for customer segmentation
        features = []
        
        # RFM Analysis (Recency, Frequency, Monetary)
        current_date = datetime.now()
        
        customer_metrics = customer_data.groupby('user_id').agg({
            'booking_date': lambda x: (current_date - pd.to_datetime(x).max()).days,  # Recency
            'booking_id': 'count',  # Frequency
            'total_amount': 'sum'  # Monetary
        }).rename(columns={
            'booking_date': 'recency_days',
            'booking_id': 'frequency',
            'total_amount': 'monetary_value'
        })
        
        # Additional behavioral features
        customer_features = customer_data.groupby('user_id').agg({
            'show_time': lambda x: pd.to_datetime(x).dt.hour.mode().iloc[0] if len(x) > 0 else 19,  # Preferred time
            'genre': lambda x: x.mode().iloc[0] if len(x) > 0 else 'Unknown',  # Preferred genre
            'theater_id': 'nunique',  # Theater diversity
            'movie_id': 'nunique'  # Movie diversity
        }).rename(columns={
            'show_time': 'preferred_hour',
            'genre': 'preferred_genre',
            'theater_id': 'theater_diversity',
            'movie_id': 'movie_diversity'
        })
        
        # Combine metrics
        combined_features = customer_metrics.join(customer_features)
        
        # Customer segmentation using simple rules
        segments = {}
        
        for user_id, row in combined_features.iterrows():
            # Determine segment based on RFM
            if row['recency_days'] <= 30 and row['frequency'] >= 4 and row['monetary_value'] >= 200:
                segment = 'vip_customer'
            elif row['recency_days'] <= 60 and row['frequency'] >= 2:
                segment = 'regular_customer'
            elif row['recency_days'] <= 90:
                segment = 'occasional_customer'
            else:
                segment = 'at_risk_customer'
            
            segments[user_id] = {
                'segment': segment,
                'metrics': row.to_dict()
            }
        
        self.customer_segments = segments
        return segments
    
    def predict_customer_behavior(self, user_id: str, prediction_horizon_days: int = 30) -> CustomerBehaviorInsight:
        """Predict individual customer behavior"""
        
        if user_id not in self.customer_segments:
            # Default prediction for unknown customer
            return CustomerBehaviorInsight(
                user_segment='new_customer',
                predicted_behavior='first_booking_likely',
                probability=0.3,
                behavioral_triggers=['new_movie_releases', 'promotional_offers'],
                recommendation_actions=['send_welcome_offer', 'recommend_popular_movies'],
                expected_value=25.0,
                time_frame=f'{prediction_horizon_days}_days'
            )
        
        customer_info = self.customer_segments[user_id]
        segment = customer_info['segment']
        metrics = customer_info['metrics']
        
        # Behavior prediction based on segment
        if segment == 'vip_customer':
            predicted_behavior = 'multiple_bookings'
            probability = 0.85
            expected_value = metrics['monetary_value'] / metrics['frequency'] * 2
            triggers = ['premium_screenings', 'early_access', 'exclusive_events']
            actions = ['offer_vip_perks', 'premium_recommendations', 'concierge_service']
            
        elif segment == 'regular_customer':
            predicted_behavior = 'regular_booking'
            probability = 0.7
            expected_value = metrics['monetary_value'] / metrics['frequency']
            triggers = ['favorite_genre_releases', 'weekend_availability', 'group_discounts']
            actions = ['genre_based_recommendations', 'weekend_promotions', 'loyalty_points']
            
        elif segment == 'occasional_customer':
            predicted_behavior = 'sporadic_booking'
            probability = 0.4
            expected_value = metrics['monetary_value'] / max(metrics['frequency'], 1) * 0.8
            triggers = ['blockbuster_releases', 'special_occasions', 'deep_discounts']
            actions = ['blockbuster_alerts', 'seasonal_campaigns', 'win_back_offers']
            
        else:  # at_risk_customer
            predicted_behavior = 'churn_risk'
            probability = 0.2
            expected_value = 15.0  # Conservative estimate
            triggers = ['major_franchise_releases', 'significant_discounts', 'social_influence']
            actions = ['reactivation_campaign', 'deep_discounts', 'social_proof_messages']
        
        return CustomerBehaviorInsight(
            user_segment=segment,
            predicted_behavior=predicted_behavior,
            probability=probability,
            behavioral_triggers=triggers,
            recommendation_actions=actions,
            expected_value=expected_value,
            time_frame=f'{prediction_horizon_days}_days'
        )
    
    def predict_churn_risk(self, user_id: str) -> Dict[str, Any]:
        """Predict customer churn risk"""
        
        if user_id not in self.customer_segments:
            return {
                'churn_risk': 'unknown',
                'probability': 0.5,
                'risk_factors': ['insufficient_data'],
                'retention_strategies': ['engagement_campaign']
            }
        
        customer_info = self.customer_segments[user_id]
        metrics = customer_info['metrics']
        
        # Calculate churn risk based on recency and frequency
        recency_score = min(metrics['recency_days'] / 180.0, 1.0)  # Normalize to 0-1
        frequency_score = 1.0 - min(metrics['frequency'] / 10.0, 1.0)  # Inverse frequency
        
        # Combined churn risk
        churn_probability = (recency_score * 0.6) + (frequency_score * 0.4)
        
        # Risk categorization
        if churn_probability >= 0.7:
            risk_level = 'high'
            strategies = ['immediate_intervention', 'personal_outreach', 'exclusive_offers']
        elif churn_probability >= 0.4:
            risk_level = 'medium'
            strategies = ['targeted_campaigns', 'loyalty_program', 'preference_based_offers']
        else:
            risk_level = 'low'
            strategies = ['maintenance_engagement', 'cross_sell_opportunities']
        
        # Risk factors
        risk_factors = []
        if metrics['recency_days'] > 90:
            risk_factors.append('long_absence')
        if metrics['frequency'] < 2:
            risk_factors.append('low_engagement')
        if metrics['monetary_value'] < 50:
            risk_factors.append('low_value')
        
        return {
            'churn_risk': risk_level,
            'probability': churn_probability,
            'risk_factors': risk_factors,
            'retention_strategies': strategies
        }

class PredictiveAnalyticsService:
    """Main predictive analytics orchestrator"""
    
    def __init__(self):
        self.demand_predictor = DemandPredictor()
        self.revenue_forecaster = RevenueForecaster()
        self.behavior_predictor = CustomerBehaviorPredictor()
        
        # Cache for expensive predictions
        self.prediction_cache = {}
    
    async def initialize_models(self, historical_data: Dict[str, pd.DataFrame]):
        """Initialize all predictive models with historical data"""
        
        logger.info("Initializing predictive analytics models...")
        
        try:
            # Initialize demand prediction models
            if 'bookings' in historical_data:
                booking_data = historical_data['bookings']
                
                # Add demand column (bookings aggregated by date/movie/theater)
                demand_data = booking_data.groupby(['date', 'movie_id', 'theater_id']).agg({
                    'booking_id': 'count',
                    'total_amount': 'sum'
                }).rename(columns={'booking_id': 'demand'}).reset_index()
                
                # Add mock features for demonstration
                np.random.seed(42)
                demand_data['genre'] = np.random.choice(['Action', 'Comedy', 'Drama'], len(demand_data))
                demand_data['rating'] = np.random.choice(['PG', 'PG-13', 'R'], len(demand_data))
                demand_data['runtime_minutes'] = np.random.normal(120, 20, len(demand_data))
                demand_data['star_rating'] = np.random.uniform(3.0, 5.0, len(demand_data))
                demand_data['theater_capacity'] = np.random.randint(100, 500, len(demand_data))
                demand_data['marketing_spend'] = np.random.uniform(10000, 100000, len(demand_data))
                
                # Train demand prediction models
                await asyncio.get_event_loop().run_in_executor(
                    None, self.demand_predictor.train_models, demand_data
                )
            
            # Initialize revenue forecasting
            if 'revenue' in historical_data:
                revenue_data = historical_data['revenue']
                await asyncio.get_event_loop().run_in_executor(
                    None, self.revenue_forecaster.analyze_revenue_patterns, revenue_data
                )
            
            # Initialize customer behavior analysis
            if 'customers' in historical_data:
                customer_data = historical_data['customers']
                await asyncio.get_event_loop().run_in_executor(
                    None, self.behavior_predictor.analyze_customer_segments, customer_data
                )
            
            logger.info("Predictive analytics models initialized successfully!")
            
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            raise
    
    async def predict_movie_demand(self, movie_id: str, theater_id: str, 
                                 prediction_date: datetime, 
                                 context_data: Dict[str, Any] = None) -> DemandForecast:
        """Predict demand for specific movie at specific theater"""
        
        try:
            # Create prediction data
            prediction_data = pd.DataFrame([{
                'movie_id': movie_id,
                'theater_id': theater_id,
                'date': prediction_date,
                **context_data
            }])
            
            # Get prediction
            demand_prediction = self.demand_predictor.predict_demand(prediction_data)[0]
            
            # Calculate confidence interval
            lower_bound, upper_bound = self.demand_predictor.calculate_prediction_confidence(
                prediction_data, np.array([demand_prediction])
            )
            
            # Determine factors analyzed
            factors_analyzed = list(context_data.keys()) if context_data else []
            factors_analyzed.extend(['date', 'day_of_week', 'seasonality'])
            
            # Get best model name
            best_model = max(
                self.demand_predictor.model_performance['prediction_accuracy'].items(),
                key=lambda x: x[1]
            )[0]
            
            # Calculate accuracy score
            accuracy_score = self.demand_predictor.model_performance['prediction_accuracy'][best_model]
            
            forecast = DemandForecast(
                forecast_id=f"forecast_{movie_id}_{theater_id}_{prediction_date.strftime('%Y%m%d')}",
                movie_id=movie_id,
                theater_id=theater_id,
                prediction_date=prediction_date,
                forecasted_demand=max(0, demand_prediction),  # Ensure non-negative
                confidence_interval=(max(0, lower_bound[0]), upper_bound[0]),
                confidence_level=0.95,
                factors_analyzed=factors_analyzed,
                model_used=best_model,
                accuracy_score=accuracy_score,
                generated_at=datetime.now()
            )
            
            return forecast
            
        except Exception as e:
            logger.error(f"Demand prediction failed for movie {movie_id}: {e}")
            raise
    
    async def forecast_revenue(self, forecast_period_days: int = 30) -> List[RevenueProjection]:
        """Forecast revenue for specified period"""
        
        try:
            revenue_forecasts = await asyncio.get_event_loop().run_in_executor(
                None, self.revenue_forecaster.forecast_revenue, forecast_period_days
            )
            
            return revenue_forecasts
            
        except Exception as e:
            logger.error(f"Revenue forecasting failed: {e}")
            return []
    
    async def analyze_customer_behavior(self, user_id: str) -> CustomerBehaviorInsight:
        """Analyze and predict customer behavior"""
        
        try:
            behavior_insight = await asyncio.get_event_loop().run_in_executor(
                None, self.behavior_predictor.predict_customer_behavior, user_id
            )
            
            return behavior_insight
            
        except Exception as e:
            logger.error(f"Customer behavior analysis failed for {user_id}: {e}")
            raise
    
    async def get_churn_risk_analysis(self, user_id: str) -> Dict[str, Any]:
        """Get customer churn risk analysis"""
        
        try:
            churn_analysis = await asyncio.get_event_loop().run_in_executor(
                None, self.behavior_predictor.predict_churn_risk, user_id
            )
            
            return churn_analysis
            
        except Exception as e:
            logger.error(f"Churn risk analysis failed for {user_id}: {e}")
            return {
                'churn_risk': 'unknown',
                'probability': 0.5,
                'risk_factors': ['analysis_error'],
                'retention_strategies': ['manual_review_needed']
            }
    
    async def generate_business_insights(self, analysis_period_days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive business insights"""
        
        try:
            insights = {
                'period_analyzed': f'{analysis_period_days} days',
                'generated_at': datetime.now().isoformat(),
                'demand_insights': {},
                'revenue_insights': {},
                'customer_insights': {},
                'recommendations': []
            }
            
            # Demand insights
            if hasattr(self.demand_predictor, 'feature_importance'):
                top_demand_factors = {}
                for model_name, importance_dict in self.demand_predictor.feature_importance.items():
                    if importance_dict:
                        top_factor = max(importance_dict.items(), key=lambda x: x[1])
                        top_demand_factors[model_name] = top_factor
                
                insights['demand_insights'] = {
                    'top_factors': top_demand_factors,
                    'model_performance': self.demand_predictor.model_performance['prediction_accuracy']
                }
            
            # Revenue insights
            if hasattr(self.revenue_forecaster, 'revenue_statistics'):
                revenue_stats = self.revenue_forecaster.revenue_statistics
                insights['revenue_insights'] = {
                    'trend_direction': revenue_stats.get('trend_direction', 'unknown'),
                    'average_daily_revenue': revenue_stats.get('mean_daily_revenue', 0),
                    'revenue_volatility': revenue_stats.get('volatility', 0)
                }
            
            # Customer insights
            if self.behavior_predictor.customer_segments:
                segment_counts = {}
                for user_data in self.behavior_predictor.customer_segments.values():
                    segment = user_data['segment']
                    segment_counts[segment] = segment_counts.get(segment, 0) + 1
                
                insights['customer_insights'] = {
                    'segment_distribution': segment_counts,
                    'total_analyzed_customers': len(self.behavior_predictor.customer_segments)
                }
            
            # Generate recommendations
            recommendations = []
            
            # Demand-based recommendations
            if 'weekend_capacity_interaction' in str(self.demand_predictor.feature_importance):
                recommendations.append("Focus marketing efforts on weekend shows for higher demand")
            
            # Revenue-based recommendations
            if hasattr(self.revenue_forecaster, 'revenue_statistics'):
                if self.revenue_forecaster.revenue_statistics.get('trend_direction') == 'decreasing':
                    recommendations.append("Implement revenue recovery strategies due to declining trend")
            
            # Customer-based recommendations
            if self.behavior_predictor.customer_segments:
                at_risk_customers = sum(
                    1 for data in self.behavior_predictor.customer_segments.values()
                    if data['segment'] == 'at_risk_customer'
                )
                total_customers = len(self.behavior_predictor.customer_segments)
                
                if at_risk_customers / total_customers > 0.2:
                    recommendations.append("High churn risk detected - implement retention campaigns")
            
            insights['recommendations'] = recommendations
            
            return insights
            
        except Exception as e:
            logger.error(f"Business insights generation failed: {e}")
            return {
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

# Global predictive analytics service
predictive_analytics_service = PredictiveAnalyticsService()

# Utility functions
async def predict_movie_demand_next_week(movie_id: str, theater_id: str) -> List[DemandForecast]:
    """Predict movie demand for the next 7 days"""
    
    forecasts = []
    
    for day in range(1, 8):
        prediction_date = datetime.now() + timedelta(days=day)
        
        # Mock context data (would come from your systems)
        context_data = {
            'genre': 'Action',
            'rating': 'PG-13',
            'star_rating': 4.2,
            'theater_capacity': 300,
            'marketing_spend': 50000
        }
        
        forecast = await predictive_analytics_service.predict_movie_demand(
            movie_id, theater_id, prediction_date, context_data
        )
        forecasts.append(forecast)
    
    return forecasts

async def get_revenue_forecast_monthly() -> List[RevenueProjection]:
    """Get 30-day revenue forecast"""
    return await predictive_analytics_service.forecast_revenue(30)

async def analyze_customer_lifetime_value(user_id: str) -> Dict[str, Any]:
    """Analyze customer lifetime value and behavior"""
    
    behavior_insight = await predictive_analytics_service.analyze_customer_behavior(user_id)
    churn_risk = await predictive_analytics_service.get_churn_risk_analysis(user_id)
    
    return {
        'behavior_prediction': asdict(behavior_insight),
        'churn_analysis': churn_risk,
        'lifetime_value_estimate': behavior_insight.expected_value * (1 - churn_risk['probability']),
        'engagement_priority': 'high' if churn_risk['probability'] > 0.6 else 'medium' if churn_risk['probability'] > 0.3 else 'low'
    }

async def get_business_intelligence_report() -> Dict[str, Any]:
    """Generate comprehensive business intelligence report"""
    return await predictive_analytics_service.generate_business_insights()