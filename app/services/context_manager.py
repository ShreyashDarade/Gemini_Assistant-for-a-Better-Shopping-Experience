"""
Context manager for multi-turn conversation state.
Maintains conversation history and extracted preferences.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.conversation import Conversation, Message
from app.models.database import get_db_context

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationContext:
    """Container for conversation context."""
    
    def __init__(
        self,
        session_id: str,
        messages: List[Dict[str, Any]] = None,
        preferences: Dict[str, Any] = None,
        discussed_products: List[int] = None,
        metadata: Dict[str, Any] = None
    ):
        self.session_id = session_id
        self.messages = messages or []
        self.preferences = preferences or {}
        self.discussed_products = discussed_products or []
        self.metadata = metadata or {}
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent messages for context."""
        return self.messages[-limit:] if self.messages else []
    
    def get_context_summary(self) -> str:
        """Generate a text summary of context for AI prompts."""
        parts = []
        
        if self.preferences:
            parts.append(f"User preferences: {self.preferences}")
        
        if self.discussed_products:
            parts.append(f"Previously discussed product IDs: {self.discussed_products[-5:]}")
        
        if self.messages:
            recent = self.get_recent_messages(5)
            msg_summary = "; ".join([
                f"{m.get('role', 'user')}: {m.get('content', '')[:100]}"
                for m in recent
            ])
            parts.append(f"Recent conversation: {msg_summary}")
        
        return " | ".join(parts) if parts else "No prior context"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "preferences": self.preferences,
            "discussed_products": self.discussed_products,
            "metadata": self.metadata,
        }


class ContextManager:
    """
    Manages conversation context with persistence.
    Optimized for high concurrency with in-memory caching.
    """
    
    def __init__(self):
        self._cache: Dict[str, ConversationContext] = {}
        self._cache_lock = asyncio.Lock()
        self._max_cache_size = 1000
        self._cache_ttl = timedelta(minutes=settings.session_timeout_minutes)
    
    async def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Get existing session or create new one."""
        if session_id:
            # Check if session exists
            async with get_db_context() as db:
                result = await db.execute(
                    select(Conversation).where(Conversation.id == session_id)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return session_id
        
        # Create new session
        new_id = str(uuid.uuid4())
        async with get_db_context() as db:
            conversation = Conversation(
                id=new_id,
                user_id=user_id,
                context={},
                preferences={},
                discussed_products=[],
            )
            db.add(conversation)
            await db.commit()
        
        return new_id
    
    async def get_context(self, session_id: str) -> ConversationContext:
        """
        Get conversation context, from cache or database.
        
        Args:
            session_id: Conversation session ID
        
        Returns:
            ConversationContext with history and preferences
        """
        # Check cache first
        async with self._cache_lock:
            if session_id in self._cache:
                return self._cache[session_id]
        
        # Load from database
        async with get_db_context() as db:
            result = await db.execute(
                select(Conversation).where(Conversation.id == session_id)
            )
            conversation = result.scalar_one_or_none()
            
            if not conversation:
                # Create new context
                context = ConversationContext(session_id=session_id)
                await self._cache_context(session_id, context)
                return context
            
            # Load messages
            msg_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == session_id)
                .order_by(Message.created_at.desc())
                .limit(settings.max_conversation_history)
            )
            messages = msg_result.scalars().all()
            
            context = ConversationContext(
                session_id=session_id,
                messages=[
                    {
                        "role": m.role,
                        "content": m.content,
                        "intent": m.intent,
                        "entities": m.entities,
                        "timestamp": m.created_at.isoformat() if m.created_at else None,
                    }
                    for m in reversed(messages)
                ],
                preferences=conversation.preferences or {},
                discussed_products=conversation.discussed_products or [],
                metadata=conversation.metadata or {},
            )
            
            await self._cache_context(session_id, context)
            return context
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        intent_confidence: Optional[float] = None,
        entities: Optional[Dict[str, Any]] = None,
        products_shown: Optional[List[int]] = None,
        media_shown: Optional[List[int]] = None,
        processing_time_ms: Optional[int] = None
    ) -> None:
        """
        Add a message to conversation history.
        
        Args:
            session_id: Conversation session ID
            role: "user" or "assistant"
            content: Message content
            intent: Classified intent (for user messages)
            intent_confidence: Intent confidence score
            entities: Extracted entities
            products_shown: Product IDs shown (for assistant messages)
            media_shown: Media IDs shown
            processing_time_ms: Response processing time
        """
        async with get_db_context() as db:
            # Create message
            message = Message(
                conversation_id=session_id,
                role=role,
                content=content,
                intent=intent,
                intent_confidence=intent_confidence,
                entities=entities or {},
                products_shown=products_shown or [],
                media_shown=media_shown or [],
                processing_time_ms=processing_time_ms,
            )
            db.add(message)
            
            # Update conversation last_active
            result = await db.execute(
                select(Conversation).where(Conversation.id == session_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                conversation.last_active = datetime.utcnow()
                
                # Update discussed products
                if products_shown:
                    existing = conversation.discussed_products or []
                    conversation.discussed_products = list(set(existing + products_shown))[-50:]
            
            await db.commit()
        
        # Update cache
        async with self._cache_lock:
            if session_id in self._cache:
                self._cache[session_id].messages.append({
                    "role": role,
                    "content": content,
                    "intent": intent,
                    "entities": entities or {},
                    "timestamp": datetime.utcnow().isoformat(),
                })
                # Trim to max history
                if len(self._cache[session_id].messages) > settings.max_conversation_history:
                    self._cache[session_id].messages = self._cache[session_id].messages[-settings.max_conversation_history:]
    
    async def update_preferences(
        self,
        session_id: str,
        preferences: Dict[str, Any]
    ) -> None:
        """Update user preferences in context."""
        async with get_db_context() as db:
            result = await db.execute(
                select(Conversation).where(Conversation.id == session_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                existing = conversation.preferences or {}
                existing.update(preferences)
                conversation.preferences = existing
                await db.commit()
        
        # Update cache
        async with self._cache_lock:
            if session_id in self._cache:
                self._cache[session_id].preferences.update(preferences)
    
    async def clear_session(self, session_id: str) -> None:
        """Clear conversation history."""
        async with get_db_context() as db:
            # Delete messages
            await db.execute(
                delete(Message).where(Message.conversation_id == session_id)
            )
            # Delete conversation
            await db.execute(
                delete(Conversation).where(Conversation.id == session_id)
            )
            await db.commit()
        
        # Remove from cache
        async with self._cache_lock:
            self._cache.pop(session_id, None)
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        cutoff = datetime.utcnow() - self._cache_ttl
        
        async with get_db_context() as db:
            # Get expired session IDs
            result = await db.execute(
                select(Conversation.id).where(Conversation.last_active < cutoff)
            )
            expired_ids = [r[0] for r in result.all()]
            
            if expired_ids:
                # Delete messages
                await db.execute(
                    delete(Message).where(Message.conversation_id.in_(expired_ids))
                )
                # Delete conversations
                await db.execute(
                    delete(Conversation).where(Conversation.id.in_(expired_ids))
                )
                await db.commit()
        
        # Clear from cache
        async with self._cache_lock:
            for sid in expired_ids:
                self._cache.pop(sid, None)
        
        logger.info(f"Cleaned up {len(expired_ids)} expired sessions")
        return len(expired_ids)
    
    async def _cache_context(self, session_id: str, context: ConversationContext) -> None:
        """Add context to cache with size management."""
        async with self._cache_lock:
            # Evict oldest if at capacity
            if len(self._cache) >= self._max_cache_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            
            self._cache[session_id] = context


# Singleton instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
