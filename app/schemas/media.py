"""
Media schemas for API requests/responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MediaSummary(BaseModel):
    """Minimal media representation."""

    id: int
    title: str
    type: str
    category: str
    url: str
    thumbnail_url: str | None = None
    duration_seconds: int | None = None


class MediaSchema(BaseModel):
    """Full media representation."""

    id: int
    title: str
    description: str | None = None
    type: str
    category: str
    url: str
    thumbnail_url: str | None = None
    duration_seconds: int | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    product_ids: list[int] = []
    tags: list[str] = []
    keywords: list[str] = []
    related_issues: list[str] = []
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MediaSearchRequest(BaseModel):
    """Request schema for media search."""

    query: str | None = Field(default=None, max_length=200, description="Search query")
    type: str | None = Field(
        default=None, pattern="^(image|video|document|audio)$", description="Media type filter"
    )
    category: str | None = Field(default=None, description="Media category filter")
    product_id: int | None = Field(default=None, description="Associated product ID")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")


class MediaSearchResponse(BaseModel):
    """Response schema for media search."""

    media: list[MediaSummary]
    total_count: int


class TutorialSearchRequest(BaseModel):
    """Request schema for tutorial search."""

    issue: str | None = Field(
        default=None, max_length=500, description="Issue or topic to search for"
    )
    product_id: int | None = Field(
        default=None, description="Product ID for product-specific tutorials"
    )
    category: str | None = Field(default=None, description="Product category")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum results")


class MediaCategoryResponse(BaseModel):
    """Media category with count."""

    category: str
    count: int
