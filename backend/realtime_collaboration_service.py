"""
Real-time Collaboration Service
WebSocket-based real-time features for group bookings, live chat, and social features
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Set, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import secrets
import sqlite3

# WebSocket support
import websockets
from websockets.server import WebSocketServerProtocol
import threading
from concurrent.futures import ThreadPoolExecutor

# Real-time events
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Real-time event types"""
    # Chat events
    CHAT_MESSAGE = "chat_message"
    CHAT_TYPING = "chat_typing"
    CHAT_USER_JOINED = "chat_user_joined"
    CHAT_USER_LEFT = "chat_user_left"
    
    # Group booking events
    GROUP_BOOKING_CREATED = "group_booking_created"
    GROUP_BOOKING_UPDATED = "group_booking_updated"
    GROUP_BOOKING_MEMBER_JOINED = "group_booking_member_joined"
    GROUP_BOOKING_MEMBER_LEFT = "group_booking_member_left"
    GROUP_BOOKING_CONFIRMED = "group_booking_confirmed"
    
    # Poll events
    POLL_CREATED = "poll_created"
    POLL_VOTE_CAST = "poll_vote_cast"
    POLL_CLOSED = "poll_closed"
    
    # Social events
    MOVIE_RECOMMENDATION = "movie_recommendation"
    WATCH_PARTY_INVITE = "watch_party_invite"
    FRIEND_ACTIVITY = "friend_activity"
    
    # System events
    NOTIFICATION = "notification"
    PRESENCE_UPDATE = "presence_update"
    SYSTEM_ANNOUNCEMENT = "system_announcement"

class UserPresence(Enum):
    """User presence status"""
    ONLINE = "online"
    AWAY = "away"
    BUSY = "busy"
    OFFLINE = "offline"

@dataclass
class ChatMessage:
    """Chat message structure"""
    message_id: str
    room_id: str
    user_id: str
    username: str
    message: str
    message_type: str = "text"  # text, image, file, system
    timestamp: datetime = None
    reply_to: Optional[str] = None  # Reply to message ID
    edited: bool = False
    edited_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class GroupBooking:
    """Group booking structure"""
    booking_id: str
    movie_id: str
    theater_id: str
    showtime: datetime
    creator_id: str
    title: str
    description: str
    max_members: int
    current_members: List[str]
    status: str = "open"  # open, closed, confirmed, cancelled
    created_at: datetime = None
    booking_deadline: Optional[datetime] = None
    requirements: Dict[str, Any] = None

@dataclass
class Poll:
    """Poll structure for group decisions"""
    poll_id: str
    room_id: str
    creator_id: str
    question: str
    options: List[str]
    votes: Dict[str, str]  # user_id -> option
    allows_multiple: bool = False
    is_anonymous: bool = False
    expires_at: Optional[datetime] = None
    created_at: datetime = None

@dataclass
class RealTimeEvent:
    """Real-time event structure"""
    event_id: str
    event_type: EventType
    room_id: Optional[str]
    user_id: str
    data: Dict[str, Any]
    timestamp: datetime = None
    target_users: Optional[List[str]] = None  # Specific users to send to

@dataclass
class UserConnection:
    """User WebSocket connection"""
    user_id: str
    username: str
    websocket: WebSocketServerProtocol
    presence: UserPresence = UserPresence.ONLINE
    rooms: Set[str] = None
    last_activity: datetime = None
    metadata: Dict[str, Any] = None

class RoomManager:
    """Manage chat rooms and channels"""
    
    def __init__(self):
        self.rooms = {}  # room_id -> room_info
        self.room_members = defaultdict(set)  # room_id -> set of user_ids
        self.user_rooms = defaultdict(set)  # user_id -> set of room_ids
        
        # Room types
        self.room_types = {
            'public_chat': {'max_members': 1000, 'requires_invitation': False},
            'group_booking': {'max_members': 20, 'requires_invitation': True},
            'private_chat': {'max_members': 2, 'requires_invitation': True},
            'watch_party': {'max_members': 50, 'requires_invitation': True}
        }
    
    def create_room(self, room_id: str, room_type: str, creator_id: str, 
                   room_name: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a new room"""
        
        if room_id in self.rooms:
            raise ValueError(f"Room {room_id} already exists")
        
        room_config = self.room_types.get(room_type, self.room_types['public_chat'])
        
        room_info = {
            'room_id': room_id,
            'room_type': room_type,
            'room_name': room_name,
            'creator_id': creator_id,
            'created_at': datetime.now(),
            'max_members': room_config['max_members'],
            'requires_invitation': room_config['requires_invitation'],
            'is_active': True,
            'metadata': metadata or {}
        }
        
        self.rooms[room_id] = room_info
        
        # Add creator to room
        self.add_user_to_room(room_id, creator_id)
        
        logger.info(f"Created room {room_id} of type {room_type}")
        return room_info
    
    def add_user_to_room(self, room_id: str, user_id: str) -> bool:
        """Add user to room"""
        
        if room_id not in self.rooms:
            return False
        
        room_info = self.rooms[room_id]
        
        # Check capacity
        if len(self.room_members[room_id]) >= room_info['max_members']:
            return False
        
        self.room_members[room_id].add(user_id)
        self.user_rooms[user_id].add(room_id)
        
        logger.debug(f"Added user {user_id} to room {room_id}")
        return True
    
    def remove_user_from_room(self, room_id: str, user_id: str) -> bool:
        """Remove user from room"""
        
        if room_id not in self.rooms:
            return False
        
        self.room_members[room_id].discard(user_id)
        self.user_rooms[user_id].discard(room_id)
        
        logger.debug(f"Removed user {user_id} from room {room_id}")
        return True
    
    def get_room_members(self, room_id: str) -> Set[str]:
        """Get room members"""
        return self.room_members.get(room_id, set())
    
    def get_user_rooms(self, user_id: str) -> Set[str]:
        """Get rooms user is in"""
        return self.user_rooms.get(user_id, set())
    
    def is_user_in_room(self, room_id: str, user_id: str) -> bool:
        """Check if user is in room"""
        return user_id in self.room_members.get(room_id, set())

class ChatService:
    """Real-time chat service"""
    
    def __init__(self):
        self.db_path = "chat.db"
        self._init_database()
        self.message_history = defaultdict(deque)  # room_id -> deque of messages
        self.typing_users = defaultdict(set)  # room_id -> set of typing users
        self.typing_timeouts = {}  # user_id -> timeout_time
    
    def _init_database(self):
        """Initialize chat database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                room_id TEXT,
                user_id TEXT,
                username TEXT,
                message TEXT,
                message_type TEXT,
                timestamp TEXT,
                reply_to TEXT,
                edited INTEGER,
                edited_at TEXT,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_rooms (
                room_id TEXT PRIMARY KEY,
                room_type TEXT,
                room_name TEXT,
                creator_id TEXT,
                created_at TEXT,
                is_active INTEGER,
                metadata TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def send_message(self, room_id: str, user_id: str, username: str, 
                          message: str, message_type: str = "text",
                          reply_to: str = None) -> ChatMessage:
        """Send chat message"""
        
        chat_message = ChatMessage(
            message_id=secrets.token_hex(16),
            room_id=room_id,
            user_id=user_id,
            username=username,
            message=message,
            message_type=message_type,
            timestamp=datetime.now(),
            reply_to=reply_to,
            metadata={}
        )
        
        # Store in database
        await self._store_message(chat_message)
        
        # Store in memory for quick access
        self.message_history[room_id].append(chat_message)
        if len(self.message_history[room_id]) > 1000:  # Limit memory usage
            self.message_history[room_id].popleft()
        
        # Clear typing status
        self.typing_users[room_id].discard(user_id)
        
        logger.debug(f"Message sent in room {room_id} by {username}")
        return chat_message
    
    async def _store_message(self, message: ChatMessage):
        """Store message in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO chat_messages 
            (message_id, room_id, user_id, username, message, message_type,
             timestamp, reply_to, edited, edited_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message.message_id,
            message.room_id,
            message.user_id,
            message.username,
            message.message,
            message.message_type,
            message.timestamp.isoformat(),
            message.reply_to,
            int(message.edited),
            message.edited_at.isoformat() if message.edited_at else None,
            json.dumps(message.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def set_typing_status(self, room_id: str, user_id: str, is_typing: bool):
        """Set user typing status"""
        
        if is_typing:
            self.typing_users[room_id].add(user_id)
            # Set timeout for typing status (10 seconds)
            self.typing_timeouts[user_id] = time.time() + 10
        else:
            self.typing_users[room_id].discard(user_id)
            self.typing_timeouts.pop(user_id, None)
    
    def get_typing_users(self, room_id: str) -> Set[str]:
        """Get currently typing users"""
        
        current_time = time.time()
        
        # Remove expired typing statuses
        expired_users = [
            user_id for user_id, timeout in self.typing_timeouts.items()
            if current_time > timeout
        ]
        
        for user_id in expired_users:
            self.typing_timeouts.pop(user_id, None)
            for room in self.typing_users.values():
                room.discard(user_id)
        
        return self.typing_users.get(room_id, set())
    
    async def get_message_history(self, room_id: str, limit: int = 50, 
                                 before_message_id: str = None) -> List[ChatMessage]:
        """Get message history for room"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT message_id, room_id, user_id, username, message, message_type,
                   timestamp, reply_to, edited, edited_at, metadata
            FROM chat_messages 
            WHERE room_id = ?
        """
        params = [room_id]
        
        if before_message_id:
            query += " AND timestamp < (SELECT timestamp FROM chat_messages WHERE message_id = ?)"
            params.append(before_message_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            message = ChatMessage(
                message_id=row[0],
                room_id=row[1],
                user_id=row[2],
                username=row[3],
                message=row[4],
                message_type=row[5],
                timestamp=datetime.fromisoformat(row[6]),
                reply_to=row[7],
                edited=bool(row[8]),
                edited_at=datetime.fromisoformat(row[9]) if row[9] else None,
                metadata=json.loads(row[10]) if row[10] else {}
            )
            messages.append(message)
        
        return list(reversed(messages))  # Return in chronological order

class GroupBookingService:
    """Group booking coordination service"""
    
    def __init__(self):
        self.db_path = "group_bookings.db"
        self._init_database()
        self.active_bookings = {}  # booking_id -> GroupBooking
        self.booking_notifications = defaultdict(list)  # user_id -> notifications
    
    def _init_database(self):
        """Initialize group bookings database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_bookings (
                booking_id TEXT PRIMARY KEY,
                movie_id TEXT,
                theater_id TEXT,
                showtime TEXT,
                creator_id TEXT,
                title TEXT,
                description TEXT,
                max_members INTEGER,
                current_members TEXT,
                status TEXT,
                created_at TEXT,
                booking_deadline TEXT,
                requirements TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def create_group_booking(self, movie_id: str, theater_id: str, showtime: datetime,
                                 creator_id: str, title: str, description: str = "",
                                 max_members: int = 10) -> GroupBooking:
        """Create new group booking"""
        
        booking = GroupBooking(
            booking_id=secrets.token_hex(16),
            movie_id=movie_id,
            theater_id=theater_id,
            showtime=showtime,
            creator_id=creator_id,
            title=title,
            description=description,
            max_members=max_members,
            current_members=[creator_id],
            status="open",
            created_at=datetime.now(),
            booking_deadline=showtime - timedelta(hours=2)  # 2 hours before showtime
        )
        
        # Store in database
        await self._store_booking(booking)
        
        # Store in memory
        self.active_bookings[booking.booking_id] = booking
        
        logger.info(f"Created group booking {booking.booking_id} for {title}")
        return booking
    
    async def join_group_booking(self, booking_id: str, user_id: str) -> bool:
        """Join group booking"""
        
        booking = self.active_bookings.get(booking_id)
        if not booking:
            return False
        
        if booking.status != "open":
            return False
        
        if len(booking.current_members) >= booking.max_members:
            return False
        
        if user_id in booking.current_members:
            return False  # Already a member
        
        booking.current_members.append(user_id)
        
        # Update database
        await self._store_booking(booking)
        
        logger.info(f"User {user_id} joined group booking {booking_id}")
        return True
    
    async def leave_group_booking(self, booking_id: str, user_id: str) -> bool:
        """Leave group booking"""
        
        booking = self.active_bookings.get(booking_id)
        if not booking:
            return False
        
        if user_id not in booking.current_members:
            return False
        
        booking.current_members.remove(user_id)
        
        # If creator leaves, transfer to first member or close booking
        if user_id == booking.creator_id:
            if booking.current_members:
                booking.creator_id = booking.current_members[0]
            else:
                booking.status = "cancelled"
        
        # Update database
        await self._store_booking(booking)
        
        logger.info(f"User {user_id} left group booking {booking_id}")
        return True
    
    async def confirm_group_booking(self, booking_id: str, creator_id: str) -> bool:
        """Confirm group booking (only creator can do this)"""
        
        booking = self.active_bookings.get(booking_id)
        if not booking:
            return False
        
        if booking.creator_id != creator_id:
            return False
        
        if booking.status != "open":
            return False
        
        booking.status = "confirmed"
        
        # Update database
        await self._store_booking(booking)
        
        logger.info(f"Group booking {booking_id} confirmed by {creator_id}")
        return True
    
    async def _store_booking(self, booking: GroupBooking):
        """Store booking in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO group_bookings 
            (booking_id, movie_id, theater_id, showtime, creator_id, title, description,
             max_members, current_members, status, created_at, booking_deadline, requirements)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            booking.booking_id,
            booking.movie_id,
            booking.theater_id,
            booking.showtime.isoformat(),
            booking.creator_id,
            booking.title,
            booking.description,
            booking.max_members,
            json.dumps(booking.current_members),
            booking.status,
            booking.created_at.isoformat(),
            booking.booking_deadline.isoformat() if booking.booking_deadline else None,
            json.dumps(booking.requirements) if booking.requirements else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_bookings(self, user_id: str) -> List[GroupBooking]:
        """Get user's group bookings"""
        
        user_bookings = []
        for booking in self.active_bookings.values():
            if user_id in booking.current_members:
                user_bookings.append(booking)
        
        return user_bookings

class PollService:
    """Live polling service for group decisions"""
    
    def __init__(self):
        self.active_polls = {}  # poll_id -> Poll
        self.poll_history = defaultdict(list)  # room_id -> list of polls
    
    async def create_poll(self, room_id: str, creator_id: str, question: str,
                         options: List[str], allows_multiple: bool = False,
                         is_anonymous: bool = False, duration_minutes: int = None) -> Poll:
        """Create new poll"""
        
        poll = Poll(
            poll_id=secrets.token_hex(16),
            room_id=room_id,
            creator_id=creator_id,
            question=question,
            options=options,
            votes={},
            allows_multiple=allows_multiple,
            is_anonymous=is_anonymous,
            expires_at=datetime.now() + timedelta(minutes=duration_minutes) if duration_minutes else None,
            created_at=datetime.now()
        )
        
        self.active_polls[poll.poll_id] = poll
        self.poll_history[room_id].append(poll)
        
        logger.info(f"Created poll {poll.poll_id} in room {room_id}")
        return poll
    
    async def cast_vote(self, poll_id: str, user_id: str, option: str) -> bool:
        """Cast vote in poll"""
        
        poll = self.active_polls.get(poll_id)
        if not poll:
            return False
        
        # Check if poll is still active
        if poll.expires_at and datetime.now() > poll.expires_at:
            return False
        
        # Check if option is valid
        if option not in poll.options:
            return False
        
        # Check if user already voted (for single-vote polls)
        if not poll.allows_multiple and user_id in poll.votes:
            return False
        
        poll.votes[user_id] = option
        
        logger.debug(f"Vote cast in poll {poll_id} by user {user_id}")
        return True
    
    async def close_poll(self, poll_id: str, creator_id: str) -> Optional[Dict[str, Any]]:
        """Close poll and get results"""
        
        poll = self.active_polls.get(poll_id)
        if not poll:
            return None
        
        if poll.creator_id != creator_id:
            return None
        
        # Count votes
        vote_counts = defaultdict(int)
        for vote in poll.votes.values():
            vote_counts[vote] += 1
        
        results = {
            'poll_id': poll_id,
            'question': poll.question,
            'options': poll.options,
            'vote_counts': dict(vote_counts),
            'total_votes': len(poll.votes),
            'winner': max(vote_counts.items(), key=lambda x: x[1])[0] if vote_counts else None,
            'closed_at': datetime.now().isoformat()
        }
        
        # Remove from active polls
        del self.active_polls[poll_id]
        
        logger.info(f"Poll {poll_id} closed with {len(poll.votes)} votes")
        return results

class WebSocketManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.connections = {}  # user_id -> UserConnection
        self.room_connections = defaultdict(set)  # room_id -> set of user_ids
        self.presence_status = {}  # user_id -> UserPresence
    
    async def connect_user(self, user_id: str, username: str, websocket: WebSocketServerProtocol):
        """Connect user via WebSocket"""
        
        # Disconnect existing connection if any
        if user_id in self.connections:
            await self.disconnect_user(user_id)
        
        connection = UserConnection(
            user_id=user_id,
            username=username,
            websocket=websocket,
            presence=UserPresence.ONLINE,
            rooms=set(),
            last_activity=datetime.now(),
            metadata={}
        )
        
        self.connections[user_id] = connection
        self.presence_status[user_id] = UserPresence.ONLINE
        
        logger.info(f"User {username} ({user_id}) connected via WebSocket")
        
        # Send connection confirmation
        await self.send_to_user(user_id, {
            'type': 'connection_established',
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        })
    
    async def disconnect_user(self, user_id: str):
        """Disconnect user"""
        
        connection = self.connections.get(user_id)
        if not connection:
            return
        
        # Remove from all rooms
        for room_id in list(connection.rooms):
            self.room_connections[room_id].discard(user_id)
        
        # Close WebSocket if still open
        if not connection.websocket.closed:
            await connection.websocket.close()
        
        # Update presence to offline
        self.presence_status[user_id] = UserPresence.OFFLINE
        
        # Remove connection
        del self.connections[user_id]
        
        logger.info(f"User {connection.username} ({user_id}) disconnected")
    
    async def join_room(self, user_id: str, room_id: str):
        """Add user to room"""
        
        connection = self.connections.get(user_id)
        if not connection:
            return False
        
        connection.rooms.add(room_id)
        self.room_connections[room_id].add(user_id)
        
        # Notify room members
        await self.broadcast_to_room(room_id, {
            'type': EventType.CHAT_USER_JOINED.value,
            'room_id': room_id,
            'user_id': user_id,
            'username': connection.username,
            'timestamp': datetime.now().isoformat()
        }, exclude_user=user_id)
        
        return True
    
    async def leave_room(self, user_id: str, room_id: str):
        """Remove user from room"""
        
        connection = self.connections.get(user_id)
        if not connection:
            return False
        
        connection.rooms.discard(room_id)
        self.room_connections[room_id].discard(user_id)
        
        # Notify room members
        await self.broadcast_to_room(room_id, {
            'type': EventType.CHAT_USER_LEFT.value,
            'room_id': room_id,
            'user_id': user_id,
            'username': connection.username,
            'timestamp': datetime.now().isoformat()
        }, exclude_user=user_id)
        
        return True
    
    async def send_to_user(self, user_id: str, data: Dict[str, Any]):
        """Send message to specific user"""
        
        connection = self.connections.get(user_id)
        if not connection or connection.websocket.closed:
            return False
        
        try:
            await connection.websocket.send(json.dumps(data))
            connection.last_activity = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            await self.disconnect_user(user_id)
            return False
    
    async def broadcast_to_room(self, room_id: str, data: Dict[str, Any], exclude_user: str = None):
        """Broadcast message to all users in room"""
        
        room_users = self.room_connections.get(room_id, set())
        
        for user_id in room_users:
            if exclude_user and user_id == exclude_user:
                continue
            
            await self.send_to_user(user_id, data)
    
    async def broadcast_to_all(self, data: Dict[str, Any]):
        """Broadcast message to all connected users"""
        
        for user_id in list(self.connections.keys()):
            await self.send_to_user(user_id, data)
    
    def get_room_users(self, room_id: str) -> List[Dict[str, Any]]:
        """Get users currently in room"""
        
        room_users = self.room_connections.get(room_id, set())
        
        users = []
        for user_id in room_users:
            connection = self.connections.get(user_id)
            if connection:
                users.append({
                    'user_id': user_id,
                    'username': connection.username,
                    'presence': connection.presence.value,
                    'last_activity': connection.last_activity.isoformat()
                })
        
        return users
    
    async def update_presence(self, user_id: str, presence: UserPresence):
        """Update user presence status"""
        
        connection = self.connections.get(user_id)
        if not connection:
            return False
        
        old_presence = connection.presence
        connection.presence = presence
        self.presence_status[user_id] = presence
        
        # Broadcast presence update to user's rooms
        for room_id in connection.rooms:
            await self.broadcast_to_room(room_id, {
                'type': EventType.PRESENCE_UPDATE.value,
                'user_id': user_id,
                'username': connection.username,
                'old_presence': old_presence.value,
                'new_presence': presence.value,
                'timestamp': datetime.now().isoformat()
            }, exclude_user=user_id)
        
        return True

class RealTimeCollaborationService:
    """Main real-time collaboration service"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.websocket_manager = WebSocketManager()
        self.room_manager = RoomManager()
        self.chat_service = ChatService()
        self.group_booking_service = GroupBookingService()
        self.poll_service = PollService()
        
        # WebSocket server
        self.server = None
        self.is_running = False
    
    async def start_server(self):
        """Start WebSocket server"""
        
        self.server = await websockets.serve(
            self.handle_websocket_connection,
            "localhost",
            self.port
        )
        
        self.is_running = True
        logger.info(f"Real-time collaboration server started on port {self.port}")
    
    async def stop_server(self):
        """Stop WebSocket server"""
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.is_running = False
        logger.info("Real-time collaboration server stopped")
    
    async def handle_websocket_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle WebSocket connection"""
        
        user_id = None
        
        try:
            # Wait for authentication message
            auth_message = await websocket.recv()
            auth_data = json.loads(auth_message)
            
            if auth_data.get('type') != 'authenticate':
                await websocket.close(code=4001, reason="Authentication required")
                return
            
            user_id = auth_data.get('user_id')
            username = auth_data.get('username')
            token = auth_data.get('token')
            
            # Validate authentication (simplified)
            if not user_id or not username:
                await websocket.close(code=4002, reason="Invalid authentication")
                return
            
            # Connect user
            await self.websocket_manager.connect_user(user_id, username, websocket)
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_message(user_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from user {user_id}")
                except Exception as e:
                    logger.error(f"Error handling message from user {user_id}: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
        finally:
            if user_id:
                await self.websocket_manager.disconnect_user(user_id)
    
    async def handle_message(self, user_id: str, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        
        message_type = data.get('type')
        connection = self.websocket_manager.connections.get(user_id)
        
        if not connection:
            return
        
        username = connection.username
        
        # Handle different message types
        if message_type == 'join_room':
            await self.handle_join_room(user_id, data)
        
        elif message_type == 'leave_room':
            await self.handle_leave_room(user_id, data)
        
        elif message_type == 'send_chat_message':
            await self.handle_chat_message(user_id, username, data)
        
        elif message_type == 'typing_status':
            await self.handle_typing_status(user_id, data)
        
        elif message_type == 'create_group_booking':
            await self.handle_create_group_booking(user_id, data)
        
        elif message_type == 'join_group_booking':
            await self.handle_join_group_booking(user_id, data)
        
        elif message_type == 'create_poll':
            await self.handle_create_poll(user_id, data)
        
        elif message_type == 'cast_vote':
            await self.handle_cast_vote(user_id, data)
        
        elif message_type == 'update_presence':
            await self.handle_update_presence(user_id, data)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
    
    async def handle_join_room(self, user_id: str, data: Dict[str, Any]):
        """Handle join room request"""
        
        room_id = data.get('room_id')
        if not room_id:
            return
        
        # Add user to room in room manager
        if room_id not in self.room_manager.rooms:
            # Create room if it doesn't exist (public chat)
            self.room_manager.create_room(room_id, 'public_chat', user_id, f"Room {room_id}")
        
        success = self.room_manager.add_user_to_room(room_id, user_id)
        
        if success:
            # Add to WebSocket manager
            await self.websocket_manager.join_room(user_id, room_id)
            
            # Send room info and recent messages
            room_info = self.room_manager.rooms[room_id]
            recent_messages = await self.chat_service.get_message_history(room_id, 50)
            room_users = self.websocket_manager.get_room_users(room_id)
            
            await self.websocket_manager.send_to_user(user_id, {
                'type': 'room_joined',
                'room_id': room_id,
                'room_info': room_info,
                'recent_messages': [asdict(msg) for msg in recent_messages],
                'room_users': room_users
            })
    
    async def handle_leave_room(self, user_id: str, data: Dict[str, Any]):
        """Handle leave room request"""
        
        room_id = data.get('room_id')
        if not room_id:
            return
        
        # Remove from room manager
        self.room_manager.remove_user_from_room(room_id, user_id)
        
        # Remove from WebSocket manager
        await self.websocket_manager.leave_room(user_id, room_id)
    
    async def handle_chat_message(self, user_id: str, username: str, data: Dict[str, Any]):
        """Handle chat message"""
        
        room_id = data.get('room_id')
        message = data.get('message')
        message_type = data.get('message_type', 'text')
        reply_to = data.get('reply_to')
        
        if not room_id or not message:
            return
        
        # Check if user is in room
        if not self.room_manager.is_user_in_room(room_id, user_id):
            return
        
        # Send message
        chat_message = await self.chat_service.send_message(
            room_id, user_id, username, message, message_type, reply_to
        )
        
        # Broadcast to room
        await self.websocket_manager.broadcast_to_room(room_id, {
            'type': EventType.CHAT_MESSAGE.value,
            'message': asdict(chat_message),
            'timestamp': datetime.now().isoformat()
        })
    
    async def handle_typing_status(self, user_id: str, data: Dict[str, Any]):
        """Handle typing status update"""
        
        room_id = data.get('room_id')
        is_typing = data.get('is_typing', False)
        
        if not room_id:
            return
        
        # Update typing status
        self.chat_service.set_typing_status(room_id, user_id, is_typing)
        
        # Get current typing users
        typing_users = list(self.chat_service.get_typing_users(room_id))
        
        # Broadcast typing status
        await self.websocket_manager.broadcast_to_room(room_id, {
            'type': EventType.CHAT_TYPING.value,
            'room_id': room_id,
            'typing_users': typing_users
        }, exclude_user=user_id)
    
    async def handle_create_group_booking(self, user_id: str, data: Dict[str, Any]):
        """Handle create group booking"""
        
        movie_id = data.get('movie_id')
        theater_id = data.get('theater_id')
        showtime_str = data.get('showtime')
        title = data.get('title')
        description = data.get('description', '')
        max_members = data.get('max_members', 10)
        
        if not all([movie_id, theater_id, showtime_str, title]):
            return
        
        try:
            showtime = datetime.fromisoformat(showtime_str)
        except ValueError:
            return
        
        # Create group booking
        booking = await self.group_booking_service.create_group_booking(
            movie_id, theater_id, showtime, user_id, title, description, max_members
        )
        
        # Create dedicated room for the booking
        room_id = f"group_booking_{booking.booking_id}"
        self.room_manager.create_room(room_id, 'group_booking', user_id, title)
        
        # Add creator to room
        await self.websocket_manager.join_room(user_id, room_id)
        
        # Send confirmation
        await self.websocket_manager.send_to_user(user_id, {
            'type': EventType.GROUP_BOOKING_CREATED.value,
            'booking': asdict(booking),
            'room_id': room_id
        })
    
    async def handle_join_group_booking(self, user_id: str, data: Dict[str, Any]):
        """Handle join group booking"""
        
        booking_id = data.get('booking_id')
        if not booking_id:
            return
        
        # Join booking
        success = await self.group_booking_service.join_group_booking(booking_id, user_id)
        
        if success:
            booking = self.group_booking_service.active_bookings[booking_id]
            room_id = f"group_booking_{booking_id}"
            
            # Add to room
            self.room_manager.add_user_to_room(room_id, user_id)
            await self.websocket_manager.join_room(user_id, room_id)
            
            # Broadcast to room
            await self.websocket_manager.broadcast_to_room(room_id, {
                'type': EventType.GROUP_BOOKING_MEMBER_JOINED.value,
                'booking_id': booking_id,
                'user_id': user_id,
                'booking': asdict(booking)
            })
    
    async def handle_create_poll(self, user_id: str, data: Dict[str, Any]):
        """Handle create poll"""
        
        room_id = data.get('room_id')
        question = data.get('question')
        options = data.get('options')
        allows_multiple = data.get('allows_multiple', False)
        is_anonymous = data.get('is_anonymous', False)
        duration_minutes = data.get('duration_minutes')
        
        if not all([room_id, question, options]) or len(options) < 2:
            return
        
        # Check if user is in room
        if not self.room_manager.is_user_in_room(room_id, user_id):
            return
        
        # Create poll
        poll = await self.poll_service.create_poll(
            room_id, user_id, question, options, allows_multiple, is_anonymous, duration_minutes
        )
        
        # Broadcast to room
        await self.websocket_manager.broadcast_to_room(room_id, {
            'type': EventType.POLL_CREATED.value,
            'poll': asdict(poll)
        })
    
    async def handle_cast_vote(self, user_id: str, data: Dict[str, Any]):
        """Handle cast vote"""
        
        poll_id = data.get('poll_id')
        option = data.get('option')
        
        if not all([poll_id, option]):
            return
        
        # Cast vote
        success = await self.poll_service.cast_vote(poll_id, user_id, option)
        
        if success:
            poll = self.poll_service.active_polls[poll_id]
            
            # Broadcast vote update
            await self.websocket_manager.broadcast_to_room(poll.room_id, {
                'type': EventType.POLL_VOTE_CAST.value,
                'poll_id': poll_id,
                'total_votes': len(poll.votes),
                'is_anonymous': poll.is_anonymous,
                'voter': user_id if not poll.is_anonymous else None
            })
    
    async def handle_update_presence(self, user_id: str, data: Dict[str, Any]):
        """Handle presence update"""
        
        presence_str = data.get('presence')
        if not presence_str:
            return
        
        try:
            presence = UserPresence(presence_str)
            await self.websocket_manager.update_presence(user_id, presence)
        except ValueError:
            logger.warning(f"Invalid presence status: {presence_str}")

# Global collaboration service
collaboration_service = RealTimeCollaborationService()

# Utility functions
async def start_collaboration_server(port: int = 8765):
    """Start real-time collaboration server"""
    
    global collaboration_service
    collaboration_service = RealTimeCollaborationService(port)
    await collaboration_service.start_server()

async def stop_collaboration_server():
    """Stop real-time collaboration server"""
    
    await collaboration_service.stop_server()

def create_movie_discussion_room(movie_id: str, creator_id: str) -> str:
    """Create movie discussion room"""
    
    room_id = f"movie_discussion_{movie_id}"
    collaboration_service.room_manager.create_room(
        room_id, 'public_chat', creator_id, f"Movie Discussion: {movie_id}"
    )
    return room_id

async def send_movie_recommendation(from_user_id: str, to_user_id: str, 
                                  movie_id: str, message: str):
    """Send movie recommendation to user"""
    
    await collaboration_service.websocket_manager.send_to_user(to_user_id, {
        'type': EventType.MOVIE_RECOMMENDATION.value,
        'from_user': from_user_id,
        'movie_id': movie_id,
        'message': message,
        'timestamp': datetime.now().isoformat()
    })

async def notify_friend_activity(user_id: str, activity_type: str, activity_data: Dict[str, Any]):
    """Notify friends about user activity"""
    
    # In a real implementation, you would get the user's friends list
    # and send notifications to online friends
    
    notification = {
        'type': EventType.FRIEND_ACTIVITY.value,
        'user_id': user_id,
        'activity_type': activity_type,
        'activity_data': activity_data,
        'timestamp': datetime.now().isoformat()
    }
    
    # For demo, broadcast to all connected users
    await collaboration_service.websocket_manager.broadcast_to_all(notification)