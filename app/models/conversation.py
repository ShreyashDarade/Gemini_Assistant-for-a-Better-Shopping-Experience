"""
Conversation and Message models for chat history management.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


class MessageRole(StrEnum):
    """Message sender role."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class IntentType(StrEnum):
    """Classified intent types."""

    PRODUCT_SEARCH = "product_search"
    PRODUCT_COMPARE = "product_compare"
    PRODUCT_RECOMMEND = "product_recommend"
    TROUBLESHOOT = "troubleshoot"
    ORDER_STATUS = "order_status"
    GENERAL_QUERY = "general_query"
    GREETING = "greeting"
    UNKNOWN = "unknown"


class Conversation(Base):
    """Conversation session model."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # User identification (optional)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Context and preferences extracted from conversation
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)

    # Products discussed in this conversation
    discussed_products: Mapped[list[int]] = mapped_column(JSON, default=list)

    # Session metadata
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("idx_conversation_user", "user_id"),
        Index("idx_conversation_active", "last_active"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "context": self.context or {},
            "preferences": self.preferences or {},
            "discussed_products": self.discussed_products or [],
            "message_count": len(self.messages) if self.messages else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
        }

    def get_recent_messages(self, limit: int = 10) -> list["Message"]:
        """Get most recent messages."""
        if not self.messages:
            return []
        return sorted(self.messages, key=lambda m: m.created_at, reverse=True)[:limit]


class Message(Base):
    """Individual message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Message content
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI analysis (for user messages)
    intent: Mapped[str | None] = mapped_column(String(50), nullable=True)
    intent_confidence: Mapped[float | None] = mapped_column(nullable=True)
    entities: Mapped[dict] = mapped_column(JSON, default=dict)

    # Response metadata (for assistant messages)
    products_shown: Mapped[list[int]] = mapped_column(JSON, default=list)
    media_shown: Mapped[list[int]] = mapped_column(JSON, default=list)

    # Processing metadata
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    __table_args__ = (Index("idx_message_conversation_time", "conversation_id", "created_at"),)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "entities": self.entities or {},
            "products_shown": self.products_shown or [],
            "media_shown": self.media_shown or [],
            "processing_time_ms": self.processing_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
