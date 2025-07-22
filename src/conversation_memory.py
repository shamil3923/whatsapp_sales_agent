"""
Conversation Memory System for WhatsApp Sales Agent
Handles user conversation history and context-aware responses
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConversationMessage:
    """Single message in conversation"""
    timestamp: str
    role: str  # 'user' or 'assistant'
    content: str
    message_type: str = "text"  # text, currency_conversion, product_inquiry
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class UserProfile:
    """User profile and preferences"""
    phone_number: str
    name: Optional[str] = None
    preferred_currency: str = "USD"
    interests: List[str] = None
    last_interaction: Optional[str] = None
    total_interactions: int = 0
    
    def __post_init__(self):
        if self.interests is None:
            self.interests = []

@dataclass
class ConversationSession:
    """Complete conversation session for a user"""
    user_profile: UserProfile
    messages: List[ConversationMessage]
    session_summary: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

class ConversationMemory:
    """Manages conversation memory and context"""
    
    def __init__(self, storage_dir: str = "data/conversations"):
        self.storage_dir = storage_dir
        self.sessions: Dict[str, ConversationSession] = {}
        self.max_messages_per_session = 50  # Keep last 50 messages
        self.session_timeout_hours = 24  # Reset context after 24 hours
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
        # Load existing sessions
        self._load_sessions()
    
    def _get_session_file(self, phone_number: str) -> str:
        """Get file path for user session"""
        safe_number = phone_number.replace("+", "").replace("-", "").replace(" ", "")
        return os.path.join(self.storage_dir, f"session_{safe_number}.json")
    
    def _load_sessions(self):
        """Load all existing sessions from storage"""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.startswith("session_") and filename.endswith(".json"):
                    phone_number = filename.replace("session_", "").replace(".json", "")
                    phone_number = f"+{phone_number}"  # Add + back
                    self._load_session(phone_number)
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
    
    def _load_session(self, phone_number: str):
        """Load specific user session"""
        try:
            session_file = self._get_session_file(phone_number)
            if os.path.exists(session_file):
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert dict back to dataclasses
                user_profile = UserProfile(**data['user_profile'])
                messages = [ConversationMessage(**msg) for msg in data['messages']]
                
                session = ConversationSession(
                    user_profile=user_profile,
                    messages=messages,
                    session_summary=data.get('session_summary'),
                    created_at=data.get('created_at'),
                    updated_at=data.get('updated_at')
                )
                
                self.sessions[phone_number] = session
                logger.info(f"Loaded session for {phone_number} with {len(messages)} messages")
                
        except Exception as e:
            logger.error(f"Error loading session for {phone_number}: {e}")
    
    def _save_session(self, phone_number: str):
        """Save user session to storage"""
        try:
            if phone_number not in self.sessions:
                return
            
            session = self.sessions[phone_number]
            session.updated_at = datetime.now().isoformat()
            
            # Convert to dict for JSON serialization
            data = {
                'user_profile': asdict(session.user_profile),
                'messages': [asdict(msg) for msg in session.messages],
                'session_summary': session.session_summary,
                'created_at': session.created_at,
                'updated_at': session.updated_at
            }
            
            session_file = self._get_session_file(phone_number)
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved session for {phone_number}")
            
        except Exception as e:
            logger.error(f"Error saving session for {phone_number}: {e}")
    
    def get_or_create_session(self, phone_number: str) -> ConversationSession:
        """Get existing session or create new one"""
        if phone_number not in self.sessions:
            # Create new session
            user_profile = UserProfile(phone_number=phone_number)
            session = ConversationSession(
                user_profile=user_profile,
                messages=[]
            )
            self.sessions[phone_number] = session
            logger.info(f"Created new session for {phone_number}")
        
        return self.sessions[phone_number]
    
    def add_message(self, phone_number: str, role: str, content: str, 
                   message_type: str = "text", metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        session = self.get_or_create_session(phone_number)
        
        message = ConversationMessage(
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            message_type=message_type,
            metadata=metadata or {}
        )
        
        session.messages.append(message)
        session.user_profile.total_interactions += 1
        session.user_profile.last_interaction = message.timestamp
        
        # Keep only recent messages
        if len(session.messages) > self.max_messages_per_session:
            session.messages = session.messages[-self.max_messages_per_session:]
        
        # Save to storage
        self._save_session(phone_number)
        
        logger.debug(f"Added {role} message for {phone_number}: {content[:50]}...")
    
    def get_conversation_context(self, phone_number: str, last_n_messages: int = 10) -> str:
        """Get conversation context for AI prompt"""
        session = self.get_or_create_session(phone_number)
        
        if not session.messages:
            return "This is a new conversation with the user."
        
        # Get recent messages
        recent_messages = session.messages[-last_n_messages:]
        
        context_parts = [
            f"User Profile: {session.user_profile.name or 'Unknown'} ({phone_number})",
            f"Preferred Currency: {session.user_profile.preferred_currency}",
            f"Total Interactions: {session.user_profile.total_interactions}",
            f"Interests: {', '.join(session.user_profile.interests) if session.user_profile.interests else 'None yet'}",
            "",
            "Recent Conversation History:"
        ]
        
        for msg in recent_messages:
            timestamp = datetime.fromisoformat(msg.timestamp).strftime("%H:%M")
            context_parts.append(f"[{timestamp}] {msg.role.upper()}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def update_user_preferences(self, phone_number: str, **kwargs):
        """Update user preferences"""
        session = self.get_or_create_session(phone_number)
        
        for key, value in kwargs.items():
            if hasattr(session.user_profile, key):
                setattr(session.user_profile, key, value)
                logger.info(f"Updated {key} for {phone_number}: {value}")
        
        self._save_session(phone_number)
    
    def add_user_interest(self, phone_number: str, interest: str):
        """Add user interest"""
        session = self.get_or_create_session(phone_number)
        
        if interest.lower() not in [i.lower() for i in session.user_profile.interests]:
            session.user_profile.interests.append(interest)
            self._save_session(phone_number)
            logger.info(f"Added interest '{interest}' for {phone_number}")
    
    def get_user_summary(self, phone_number: str) -> Dict[str, Any]:
        """Get user summary for analytics"""
        session = self.get_or_create_session(phone_number)
        
        return {
            "phone_number": phone_number,
            "name": session.user_profile.name,
            "total_interactions": session.user_profile.total_interactions,
            "preferred_currency": session.user_profile.preferred_currency,
            "interests": session.user_profile.interests,
            "last_interaction": session.user_profile.last_interaction,
            "total_messages": len(session.messages),
            "session_created": session.created_at
        }
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """Clean up old inactive sessions"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for phone_number, session in list(self.sessions.items()):
            if session.user_profile.last_interaction:
                last_interaction = datetime.fromisoformat(session.user_profile.last_interaction)
                if last_interaction < cutoff_date:
                    # Archive or delete old session
                    session_file = self._get_session_file(phone_number)
                    if os.path.exists(session_file):
                        os.remove(session_file)
                    del self.sessions[phone_number]
                    logger.info(f"Cleaned up old session for {phone_number}")
    
    def get_all_users_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all users"""
        return [self.get_user_summary(phone) for phone in self.sessions.keys()]
