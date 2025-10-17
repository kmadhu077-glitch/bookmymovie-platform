"""
Third-Party Integration Test Suite
Comprehensive testing for payment gateways, external APIs, and communication services
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from typing import Dict, Any, List

# Import integration services
from payment_gateway_service import (
    PaymentGatewayService, PaymentProvider, PaymentRequest, PaymentStatus,
    StripePaymentProcessor, PayPalPaymentProcessor, RazorpayPaymentProcessor
)
from external_movie_database_service import (
    MovieDatabaseService, TMDBService, OMDBService, MovieProvider
)
from communication_services import (
    CommunicationService, SendGridService, TwilioService, FirebaseCloudMessagingService,
    MessageType, MessageRequest, MessageStatus
)
from social_media_integration import (
    SocialMediaService, FacebookService, TwitterService, SocialPlatform, SocialPost, PostType
)
from bi_tool_connectors import (
    BIIntegrationService, TableauService, PowerBIService, BIPlatform
)

class TestPaymentGatewayIntegration:
    """Test payment gateway integrations"""
    
    @pytest.fixture
    def payment_service(self):
        return PaymentGatewayService()
    
    @pytest.fixture
    def sample_payment_request(self):
        return PaymentRequest(
            amount=25.99,
            currency="USD",
            customer_id="test_customer_123",
            payment_method_id="pm_test_card",
            description="Movie ticket booking",
            metadata={"booking_id": "B12345", "movie_title": "Test Movie"}
        )
    
    @pytest.mark.asyncio
    async def test_stripe_payment_processing(self, payment_service, sample_payment_request):
        """Test Stripe payment processing"""
        with patch('stripe.PaymentIntent.create') as mock_stripe:
            # Mock successful Stripe response
            mock_stripe.return_value = MagicMock(
                id="pi_test_123",
                status="succeeded",
                amount=2599,
                currency="usd",
                client_secret="pi_test_123_secret"
            )
            
            result = await payment_service.process_payment(
                PaymentProvider.STRIPE, 
                sample_payment_request
            )
            
            assert result.success is True
            assert result.transaction_id == "pi_test_123"
            assert result.status == PaymentStatus.COMPLETED
            assert result.amount == 25.99
            
            # Verify Stripe was called with correct parameters
            mock_stripe.assert_called_once()
            call_args = mock_stripe.call_args[1]
            assert call_args['amount'] == 2599
            assert call_args['currency'] == 'usd'
            assert call_args['payment_method'] == 'pm_test_card'
    
    @pytest.mark.asyncio
    async def test_paypal_payment_processing(self, payment_service, sample_payment_request):
        """Test PayPal payment processing"""
        with patch('paypalrestsdk.Payment.create') as mock_paypal:
            # Mock successful PayPal response
            mock_payment = MagicMock()
            mock_payment.create.return_value = True
            mock_payment.id = "PAY-test123"
            mock_payment.state = "approved"
            mock_paypal.return_value = mock_payment
            
            result = await payment_service.process_payment(
                PaymentProvider.PAYPAL, 
                sample_payment_request
            )
            
            assert result.success is True
            assert result.transaction_id == "PAY-test123"
            assert result.status == PaymentStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_razorpay_payment_processing(self, payment_service, sample_payment_request):
        """Test Razorpay payment processing"""
        with patch('razorpay.Client') as mock_razorpay_client:
            # Mock Razorpay client and order creation
            mock_client = MagicMock()
            mock_client.order.create.return_value = {
                'id': 'order_test123',
                'status': 'created',
                'amount': 2599,
                'currency': 'USD'
            }
            mock_razorpay_client.return_value = mock_client
            
            # Update request for INR currency (Razorpay requirement)
            sample_payment_request.currency = "INR"
            sample_payment_request.amount = 1999.50
            
            result = await payment_service.process_payment(
                PaymentProvider.RAZORPAY, 
                sample_payment_request
            )
            
            assert result.success is True
            assert result.transaction_id == "order_test123"
    
    @pytest.mark.asyncio
    async def test_payment_failure_handling(self, payment_service, sample_payment_request):
        """Test payment failure scenarios"""
        with patch('stripe.PaymentIntent.create') as mock_stripe:
            # Mock Stripe failure
            mock_stripe.side_effect = Exception("Card declined")
            
            result = await payment_service.process_payment(
                PaymentProvider.STRIPE, 
                sample_payment_request
            )
            
            assert result.success is False
            assert result.status == PaymentStatus.FAILED
            assert "Card declined" in result.error_message
    
    @pytest.mark.asyncio
    async def test_refund_processing(self, payment_service):
        """Test refund processing"""
        with patch('stripe.Refund.create') as mock_stripe_refund:
            # Mock successful refund
            mock_stripe_refund.return_value = MagicMock(
                id="re_test123",
                status="succeeded",
                amount=2599
            )
            
            result = await payment_service.process_refund(
                PaymentProvider.STRIPE,
                transaction_id="pi_test_123",
                amount=25.99,
                reason="Customer requested cancellation"
            )
            
            assert result.success is True
            assert result.refund_id == "re_test123"
            assert result.amount == 25.99
    
    @pytest.mark.asyncio
    async def test_fraud_detection(self, payment_service, sample_payment_request):
        """Test fraud detection system"""
        # Test with suspicious transaction patterns
        suspicious_request = PaymentRequest(
            amount=9999.99,  # High amount
            currency="USD",
            customer_id="new_customer",  # New customer
            payment_method_id="pm_suspicious",
            description="Bulk ticket purchase",
            metadata={"ip_address": "suspicious_ip", "user_agent": "bot"}
        )
        
        fraud_score = await payment_service.calculate_fraud_score(suspicious_request)
        
        # High amount + new customer + suspicious metadata should trigger high fraud score
        assert fraud_score >= 70  # Assuming 70+ is high risk
    
    @pytest.mark.asyncio
    async def test_webhook_verification(self, payment_service):
        """Test webhook signature verification"""
        # Mock webhook payload
        webhook_payload = json.dumps({
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test123",
                    "status": "succeeded"
                }
            }
        })
        
        # Test Stripe webhook verification
        with patch('stripe.Webhook.construct_event') as mock_verify:
            mock_verify.return_value = json.loads(webhook_payload)
            
            is_valid = payment_service.verify_webhook_signature(
                PaymentProvider.STRIPE,
                webhook_payload,
                "test_signature",
                "webhook_secret"
            )
            
            assert is_valid is True


class TestExternalMovieDatabase:
    """Test external movie database integrations"""
    
    @pytest.fixture
    def movie_service(self):
        return MovieDatabaseService()
    
    @pytest.mark.asyncio
    async def test_tmdb_movie_search(self, movie_service):
        """Test TMDB movie search functionality"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock TMDB API response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "results": [
                    {
                        "id": 550,
                        "title": "Fight Club",
                        "overview": "A ticking-time-bomb insomniac...",
                        "release_date": "1999-10-15",
                        "vote_average": 8.4,
                        "poster_path": "/bptfVGEQuv6vDTIMVCHjJ9Dz8PX.jpg"
                    }
                ],
                "total_results": 1
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with movie_service as service:
                results = await service.search_movies("Fight Club", provider=MovieProvider.TMDB)
            
            assert len(results['results']) == 1
            assert results['results'][0]['title'] == "Fight Club"
            assert results['results'][0]['id'] == 550
    
    @pytest.mark.asyncio
    async def test_omdb_movie_details(self, movie_service):
        """Test OMDB movie details retrieval"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock OMDB API response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                "Title": "The Matrix",
                "Year": "1999",
                "imdbID": "tt0133093",
                "Type": "movie",
                "Poster": "https://example.com/poster.jpg",
                "Plot": "A computer hacker learns...",
                "Director": "Lana Wachowski, Lilly Wachowski",
                "Actors": "Keanu Reeves, Laurence Fishburne",
                "imdbRating": "8.7",
                "Response": "True"
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with movie_service as service:
                movie_details = await service.get_movie_details(
                    movie_id=None,
                    imdb_id="tt0133093",
                    provider=MovieProvider.OMDB
                )
            
            assert movie_details is not None
            assert movie_details.title == "The Matrix"
            assert movie_details.external_id == "tt0133093"
            assert movie_details.rating == 8.7
    
    @pytest.mark.asyncio
    async def test_cross_reference_movie_data(self, movie_service):
        """Test cross-referencing movie data from multiple providers"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock responses for both TMDB and OMDB
            responses = [
                # TMDB response
                AsyncMock(status=200, json=AsyncMock(return_value={
                    "id": 550,
                    "title": "Fight Club",
                    "overview": "Test overview",
                    "vote_average": 8.4
                })),
                # OMDB response  
                AsyncMock(status=200, json=AsyncMock(return_value={
                    "Title": "Fight Club",
                    "imdbID": "tt0137523",
                    "imdbRating": "8.8",
                    "Response": "True"
                }))
            ]
            
            mock_get.return_value.__aenter__.side_effect = responses
            
            async with movie_service as service:
                cross_ref_data = await service.cross_reference_movie(
                    tmdb_id="550",
                    imdb_id="tt0137523",
                    title="Fight Club"
                )
            
            assert 'tmdb' in cross_ref_data
            assert 'omdb' in cross_ref_data
            assert cross_ref_data['tmdb'].provider == MovieProvider.TMDB
            assert cross_ref_data['omdb'].provider == MovieProvider.OMDB


class TestCommunicationServices:
    """Test communication service integrations"""
    
    @pytest.fixture
    def comm_service(self):
        return CommunicationService()
    
    @pytest.mark.asyncio
    async def test_sendgrid_email_sending(self, comm_service):
        """Test SendGrid email functionality"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful SendGrid response
            mock_response = AsyncMock()
            mock_response.status = 202
            mock_response.headers = {'X-Message-Id': 'test_message_123'}
            mock_post.return_value.__aenter__.return_value = mock_response
            
            message_request = MessageRequest(
                recipient="test@example.com",
                subject="Test Email",
                content="<h1>Test Content</h1>",
                message_type=MessageType.EMAIL
            )
            
            async with comm_service.email_service as service:
                result = await service.send_email(message_request)
            
            assert result.success is True
            assert result.message_id == 'test_message_123'
            assert result.status == MessageStatus.SENT
    
    @pytest.mark.asyncio
    async def test_twilio_sms_sending(self, comm_service):
        """Test Twilio SMS functionality"""
        with patch('twilio.rest.Client') as mock_twilio:
            # Mock Twilio client and message creation
            mock_client = MagicMock()
            mock_message = MagicMock()
            mock_message.sid = 'SM_test_123'
            mock_message.status = 'sent'
            mock_client.messages.create.return_value = mock_message
            mock_twilio.return_value = mock_client
            
            message_request = MessageRequest(
                recipient="+1234567890",
                content="Your booking confirmation for Movie XYZ",
                message_type=MessageType.SMS
            )
            
            result = await comm_service.sms_service.send_sms(message_request)
            
            assert result.success is True
            assert result.message_id == 'SM_test_123'
            assert result.status == MessageStatus.SENT
    
    @pytest.mark.asyncio
    async def test_fcm_push_notification(self, comm_service):
        """Test Firebase Cloud Messaging push notifications"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful FCM response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'multicast_id': 123456789,
                'success': 1,
                'failure': 0,
                'results': [{'message_id': 'fcm_msg_123'}]
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            message_request = MessageRequest(
                recipient="device_token_123",
                subject="Booking Confirmation",
                content="Your tickets are ready!",
                message_type=MessageType.PUSH
            )
            
            async with comm_service.push_service as service:
                result = await service.send_push_notification(message_request)
            
            assert result.success is True
            assert result.message_id == "123456789"
            assert result.status == MessageStatus.SENT
    
    @pytest.mark.asyncio
    async def test_multi_channel_notification(self, comm_service):
        """Test sending notifications across multiple channels"""
        with patch.multiple(
            'aiohttp.ClientSession',
            post=AsyncMock(return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=AsyncMock(
                    status=202,
                    headers={'X-Message-Id': 'email_123'},
                    json=AsyncMock(return_value={'success': 1, 'multicast_id': 'push_123'})
                ))
            ))
        ), patch('twilio.rest.Client') as mock_twilio:
            # Setup mocks
            mock_client = MagicMock()
            mock_message = MagicMock(sid='sms_123', status='sent')
            mock_client.messages.create.return_value = mock_message
            mock_twilio.return_value = mock_client
            
            # Send multi-channel notification
            results = await comm_service.send_multi_channel_notification(
                user_id="user123",
                template_name="booking_confirmation",
                template_data={
                    "user_name": "John Doe",
                    "movie_title": "Test Movie",
                    "show_date": "2024-01-15",
                    "show_time": "7:30 PM",
                    "cinema_name": "Test Cinema",
                    "seats": "A1, A2",
                    "booking_id": "B123456"
                },
                channels=[MessageType.EMAIL, MessageType.SMS, MessageType.PUSH]
            )
            
            assert MessageType.EMAIL in results
            assert MessageType.SMS in results
            assert MessageType.PUSH in results
            assert results[MessageType.EMAIL].success is True
            assert results[MessageType.SMS].success is True
            assert results[MessageType.PUSH].success is True


class TestSocialMediaIntegration:
    """Test social media integration services"""
    
    @pytest.fixture
    def social_service(self):
        return SocialMediaService()
    
    @pytest.mark.asyncio
    async def test_facebook_page_posting(self, social_service):
        """Test Facebook page posting"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful Facebook response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'id': '123456789_987654321'
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            post = SocialPost(
                content="Now showing: Test Movie! Book your tickets now 🎬",
                post_type=PostType.TEXT,
                hashtags=["Movies", "Cinema", "BookMyMovie"],
                link_url="https://bookmymovie.com/movie/test-movie"
            )
            
            async with social_service.facebook_service as service:
                result = await service.post_to_page(post)
            
            assert result.success is True
            assert result.post_id == '123456789_987654321'
            assert result.platform == SocialPlatform.FACEBOOK
    
    @pytest.mark.asyncio
    async def test_twitter_posting(self, social_service):
        """Test Twitter posting"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful Twitter response
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json.return_value = {
                'data': {
                    'id': '1234567890123456789',
                    'text': 'Now showing: Test Movie! 🎬 #Movies #Cinema'
                }
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            post = SocialPost(
                content="Now showing: Test Movie! 🎬",
                post_type=PostType.TEXT,
                hashtags=["Movies", "Cinema"],
                link_url="https://bookmymovie.com/movie/test-movie"
            )
            
            async with social_service.twitter_service as service:
                result = await service.post_tweet(post)
            
            assert result.success is True
            assert result.post_id == '1234567890123456789'
            assert result.platform == SocialPlatform.TWITTER
    
    @pytest.mark.asyncio
    async def test_movie_promotion_campaign(self, social_service):
        """Test automated movie promotion across platforms"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful responses for both platforms
            responses = [
                # Facebook response
                AsyncMock(status=200, json=AsyncMock(return_value={'id': 'fb_post_123'})),
                # Twitter response
                AsyncMock(status=201, json=AsyncMock(return_value={'data': {'id': 'tw_post_123'}}))
            ]
            mock_post.return_value.__aenter__.side_effect = responses
            
            movie_data = {
                'title': 'Awesome New Movie',
                'booking_link': 'https://bookmymovie.com/movie/awesome-new-movie',
                'poster_url': 'https://example.com/poster.jpg',
                'discount': '25'
            }
            
            results = await social_service.create_movie_promotion_post(
                movie_data,
                platforms=[SocialPlatform.FACEBOOK, SocialPlatform.TWITTER]
            )
            
            assert SocialPlatform.FACEBOOK in results
            assert SocialPlatform.TWITTER in results
            assert results[SocialPlatform.FACEBOOK].success is True
            assert results[SocialPlatform.TWITTER].success is True


class TestBIIntegration:
    """Test Business Intelligence tool integrations"""
    
    @pytest.fixture
    def bi_service(self):
        return BIIntegrationService()
    
    @pytest.mark.asyncio
    async def test_tableau_authentication(self, bi_service):
        """Test Tableau Server authentication"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful Tableau auth response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'credentials': {
                    'token': 'tableau_auth_token_123',
                    'site': {'id': 'site_123'}
                }
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            async with bi_service.tableau_service as service:
                assert service.auth_token == 'tableau_auth_token_123'
                assert service.site_id_actual == 'site_123'
    
    @pytest.mark.asyncio
    async def test_powerbi_dataset_creation(self, bi_service):
        """Test Power BI dataset creation"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock successful Power BI responses
            auth_response = AsyncMock(status=200, json=AsyncMock(return_value={
                'access_token': 'powerbi_token_123'
            }))
            dataset_response = AsyncMock(status=201, json=AsyncMock(return_value={
                'id': 'dataset_123',
                'name': 'BookMyMovie_Test'
            }))
            
            mock_post.return_value.__aenter__.side_effect = [auth_response, dataset_response]
            
            dataset_config = {
                'name': 'BookMyMovie_Test',
                'tables': [{
                    'name': 'test_bookings',
                    'columns': [
                        {'name': 'booking_id', 'type': 'string'},
                        {'name': 'amount', 'type': 'decimal'}
                    ]
                }]
            }
            
            async with bi_service.powerbi_service as service:
                result = await service.create_dataset(dataset_config)
            
            assert result.get('id') == 'dataset_123'
            assert result.get('name') == 'BookMyMovie_Test'
    
    @pytest.mark.asyncio
    async def test_data_sync_to_powerbi(self, bi_service):
        """Test syncing data to Power BI"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock auth and data push responses
            auth_response = AsyncMock(status=200, json=AsyncMock(return_value={
                'access_token': 'powerbi_token_123'
            }))
            data_push_response = AsyncMock(status=200, json=AsyncMock(return_value={}))
            
            mock_post.return_value.__aenter__.side_effect = [auth_response, data_push_response]
            
            sample_data = [
                {
                    'booking_id': 'B001',
                    'user_id': 'U123',
                    'movie_id': 'M456',
                    'total_amount': 45.50,
                    'booking_date': '2024-01-15T19:30:00'
                }
            ]
            
            result = await bi_service.sync_data_to_bi_platform(
                BIPlatform.POWER_BI,
                'bookings',
                sample_data
            )
            
            assert result.get('success') is True
            assert result.get('rows_added') == 1
    
    @pytest.mark.asyncio
    async def test_executive_report_generation(self, bi_service):
        """Test executive report generation"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Mock Google Analytics response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'reports': [{
                    'data': {
                        'rows': [
                            {'dimensions': ['20240115'], 'metrics': [{'values': ['150', '250', '1200', '45.2']}]}
                        ]
                    }
                }]
            }
            mock_get.return_value.__aenter__.return_value = mock_response
            
            date_range = {
                'start_date': '2024-01-08',
                'end_date': '2024-01-15'
            }
            
            report = await bi_service.generate_executive_report('weekly', date_range)
            
            assert report['report_type'] == 'weekly'
            assert 'generated_at' in report
            assert 'metrics' in report
            assert 'insights' in report
            assert len(report['insights']) > 0


class TestIntegrationOrchestration:
    """Test integration between multiple third-party services"""
    
    @pytest.mark.asyncio
    async def test_complete_booking_flow_integration(self):
        """Test complete booking flow with all integrations"""
        
        # Simulate a complete booking process involving:
        # 1. Payment processing
        # 2. Notification sending
        # 3. Social media sharing
        # 4. BI data sync
        
        booking_data = {
            'booking_id': 'B123456',
            'user_id': 'U789',
            'movie_title': 'Integration Test Movie',
            'cinema_name': 'Test Cinema',
            'show_date': '2024-01-15',
            'show_time': '7:30 PM',
            'seats': 'A1, A2',
            'total_amount': 29.98,
            'user_name': 'Test User',
            'user_email': 'test@example.com',
            'user_phone': '+1234567890'
        }
        
        # Mock all external service calls
        with patch.multiple(
            'stripe.PaymentIntent.create',
            create=MagicMock(return_value=MagicMock(
                id='pi_test123', 
                status='succeeded',
                amount=2998,
                currency='usd'
            ))
        ), patch('aiohttp.ClientSession.post') as mock_http_post, \
           patch('twilio.rest.Client') as mock_twilio:
            
            # Setup HTTP mocks for email and social media
            mock_http_post.return_value.__aenter__.return_value = AsyncMock(
                status=202,
                headers={'X-Message-Id': 'email_123'},
                json=AsyncMock(return_value={'id': 'social_post_123'})
            )
            
            # Setup SMS mock
            mock_client = MagicMock()
            mock_message = MagicMock(sid='sms_123', status='sent')
            mock_client.messages.create.return_value = mock_message
            mock_twilio.return_value = mock_client
            
            # Execute complete integration flow
            payment_service = PaymentGatewayService()
            comm_service = CommunicationService()
            social_service = SocialMediaService()
            
            # 1. Process payment
            payment_request = PaymentRequest(
                amount=booking_data['total_amount'],
                currency="USD",
                customer_id=booking_data['user_id'],
                payment_method_id="pm_test_card",
                description=f"Booking for {booking_data['movie_title']}",
                metadata={'booking_id': booking_data['booking_id']}
            )
            
            payment_result = await payment_service.process_payment(
                PaymentProvider.STRIPE, 
                payment_request
            )
            
            # 2. Send confirmation notifications
            notification_results = await comm_service.send_multi_channel_notification(
                user_id=booking_data['user_id'],
                template_name='booking_confirmation',
                template_data=booking_data,
                channels=[MessageType.EMAIL, MessageType.SMS]
            )
            
            # 3. Create social media post (optional user sharing)
            social_post = SocialPost(
                content=f"Just booked tickets for {booking_data['movie_title']}! 🎬",
                post_type=PostType.TEXT,
                hashtags=['Movies', 'BookMyMovie']
            )
            
            social_results = await social_service.post_to_all_platforms(
                social_post,
                platforms=[SocialPlatform.FACEBOOK, SocialPlatform.TWITTER]
            )
            
            # Verify all integrations succeeded
            assert payment_result.success is True
            assert payment_result.transaction_id == 'pi_test123'
            
            assert MessageType.EMAIL in notification_results
            assert MessageType.SMS in notification_results
            assert notification_results[MessageType.EMAIL].success is True
            assert notification_results[MessageType.SMS].success is True
            
            assert SocialPlatform.FACEBOOK in social_results
            assert SocialPlatform.TWITTER in social_results
    
    @pytest.mark.asyncio
    async def test_error_handling_and_rollback(self):
        """Test error handling and rollback scenarios"""
        
        # Test scenario where payment succeeds but notifications fail
        with patch('stripe.PaymentIntent.create') as mock_stripe, \
             patch('aiohttp.ClientSession.post') as mock_http:
            
            # Payment succeeds
            mock_stripe.return_value = MagicMock(
                id='pi_test123',
                status='succeeded',
                amount=2998
            )
            
            # But email service fails
            mock_http.return_value.__aenter__.return_value = AsyncMock(
                status=500,
                text=AsyncMock(return_value="Service unavailable")
            )
            
            payment_service = PaymentGatewayService()
            comm_service = CommunicationService()
            
            # Process payment
            payment_request = PaymentRequest(
                amount=29.98,
                currency="USD",
                customer_id="test_user",
                payment_method_id="pm_test_card"
            )
            
            payment_result = await payment_service.process_payment(
                PaymentProvider.STRIPE,
                payment_request
            )
            
            # Try to send notification (should fail)
            message_request = MessageRequest(
                recipient="test@example.com",
                subject="Test",
                content="Test content",
                message_type=MessageType.EMAIL
            )
            
            async with comm_service.email_service as service:
                notification_result = await service.send_email(message_request)
            
            # Payment should succeed, notification should fail
            assert payment_result.success is True
            assert notification_result.success is False
            assert notification_result.status == MessageStatus.FAILED
            
            # In a real scenario, you would implement compensation logic here
            # such as queuing the notification for retry or initiating a refund


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])