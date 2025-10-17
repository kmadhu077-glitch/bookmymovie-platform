"""
WebSocket Client Test for BookMyMovie Real-time Features
Test script to demonstrate live seat updates and notifications
"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime

class BookMyMovieWebSocketClient:
    def __init__(self, base_url="ws://127.0.0.1:8006"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        
    async def test_seat_updates(self, showtime_id=1):
        """Test real-time seat availability updates"""
        uri = f"{self.base_url}/ws/seats/{showtime_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                print(f"✅ Connected to seat updates for showtime {showtime_id}")
                
                # Simulate seat selection
                seat_selection = {
                    "action": "select_seats",
                    "seats": [
                        {"row": "D", "number": 5},
                        {"row": "D", "number": 6}
                    ],
                    "session_id": self.session_id
                }
                
                print("📍 Selecting seats D5 and D6...")
                await websocket.send(json.dumps(seat_selection))
                
                # Listen for updates for 30 seconds
                timeout = 30
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        print(f"🔄 Received seat update: {data}")
                        
                        # Simulate releasing seats after 10 seconds
                        if (asyncio.get_event_loop().time() - start_time) > 10 and data.get("type") == "seat_selection":
                            seat_release = {
                                "action": "release_seats",
                                "seats": [
                                    {"row": "D", "number": 5},
                                    {"row": "D", "number": 6}
                                ],
                                "session_id": self.session_id
                            }
                            print("🔄 Releasing seats...")
                            await websocket.send(json.dumps(seat_release))
                        
                    except asyncio.TimeoutError:
                        continue
                
        except Exception as e:
            print(f"❌ Error in seat updates test: {e}")
    
    async def test_booking_updates(self, user_id=1):
        """Test real-time booking updates"""
        uri = f"{self.base_url}/ws/bookings/{user_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                print(f"✅ Connected to booking updates for user {user_id}")
                
                # Listen for booking updates
                timeout = 20
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        print(f"📝 Received booking update: {data}")
                        
                    except asyncio.TimeoutError:
                        continue
                
        except Exception as e:
            print(f"❌ Error in booking updates test: {e}")
    
    async def test_notifications(self, user_id=1):
        """Test real-time notifications"""
        uri = f"{self.base_url}/ws/notifications/{user_id}"
        
        try:
            async with websockets.connect(uri) as websocket:
                print(f"✅ Connected to notifications for user {user_id}")
                
                # Listen for notifications
                timeout = 20
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        print(f"🔔 Received notification: {data}")
                        
                        # Mark first notification as read
                        if data.get("type") == "new_notification" and data.get("id"):
                            mark_read = {
                                "action": "mark_read",
                                "notification_id": data["id"]
                            }
                            await websocket.send(json.dumps(mark_read))
                            print(f"✅ Marked notification {data['id']} as read")
                        
                    except asyncio.TimeoutError:
                        continue
                
        except Exception as e:
            print(f"❌ Error in notifications test: {e}")

async def main():
    """Run WebSocket client tests"""
    print("🎬 BookMyMovie WebSocket Client Test")
    print("=" * 50)
    
    client = BookMyMovieWebSocketClient()
    
    # Test different WebSocket endpoints concurrently
    tasks = [
        asyncio.create_task(client.test_seat_updates(showtime_id=1)),
        asyncio.create_task(client.test_booking_updates(user_id=1)),
        asyncio.create_task(client.test_notifications(user_id=1))
    ]
    
    print("🚀 Starting WebSocket tests...")
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
        print("✅ All WebSocket tests completed")
        
    except Exception as e:
        print(f"❌ Test error: {e}")

if __name__ == "__main__":
    print("Starting WebSocket client tests...")
    print("Make sure the real-time service is running on port 8006")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")