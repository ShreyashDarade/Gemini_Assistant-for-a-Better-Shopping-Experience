"""
Media schemas for API requests/responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MediaSummary(BaseModel):
    """Minimal media representation."""
    
    id: int
    title: str
    type: str
    category: str
    url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None


class MediaSchema(BaseModel):
    """Full media representation."""
    
    id: int
    title: str
    description: Optional[str] = None
    type: str
    category: str
    url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    product_ids: List[int] = []
    tags: List[str] = []
    keywords: List[str] = []
    related_issues: List[str] = []
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class MediaSearchRequest(BaseModel):
    """Request schema for media search."""
    
    query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Search query"
    )
    type: Optional[str] = Field(
        default=None,
        pattern="^(image|video|document|audio)$",
        description="Media type filter"
    )
    category: Optional[str] = Field(
        default=None,
        description="Media category filter"
    )
    product_id: Optional[int] = Field(
        default=None,
        description="Associated product ID"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum results"
    )


class MediaSearchResponse(BaseModel):
    """Response schema for media search."""
    
    media: List[MediaSummary]
    total_count: int


class TutorialSearchRequest(BaseModel):
    """Request schema for tutorial search."""
    
    issue: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Issue or topic to search for"
    )
    product_id: Optional[int] = Field(
        default=None,
        description="Product ID for product-specific tutorials"
    )
    category: Optional[str] = Field(
        default=None,
        description="Product category"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum results"
    )


class MediaCategoryResponse(BaseModel):
    """Media category with count."""
    
    category: str
    count: int
