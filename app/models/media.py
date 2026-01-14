"""
Media model for visual aids, tutorials, and product media.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class MediaType(str, Enum):
    """Type of media content."""
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


class MediaCategory(str, Enum):
    """Category of media usage."""
    PRODUCT = "product"
    TUTORIAL = "tutorial"
    TROUBLESHOOT = "troubleshoot"
    PROMOTIONAL = "promotional"
    GUIDE = "guide"


class Media(Base):
    """Media asset model."""
    
    __tablename__ = "media"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Basic info
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Type and category
    type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # URLs
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Metadata
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Associations
    product_ids: Mapped[List[int]] = mapped_column(JSON, default=list)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # For troubleshooting content
    related_issues: Mapped[List[str]] = mapped_column(JSON, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        Index("idx_media_type_category", "type", "category"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "product_ids": self.product_ids or [],
            "tags": self.tags or [],
            "keywords": self.keywords or [],
            "related_issues": self.related_issues or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    def to_summary(self) -> dict:
        """Convert to summary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "category": self.category,
            "url": self.url,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
        }
