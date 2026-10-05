"""
Product schemas for API requests/responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductSummary(BaseModel):
    """Minimal product representation for lists."""

    id: int
    name: str
    brand: str
    category: str
    price: float
    original_price: float | None = None
    currency: str = "USD"
    discount_percent: int | None = None
    rating: float
    review_count: int
    image_url: str | None = None
    in_stock: bool


class ProductSchema(BaseModel):
    """Full product representation."""

    id: int
    name: str
    description: str
    category: str
    subcategory: str | None = None
    brand: str
    price: float
    original_price: float | None = None
    currency: str = "USD"
    rating: float
    review_count: int
    stock: int
    sku: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    video_url: str | None = None
    gallery_urls: list[str] = []
    tags: list[str] = []
    specifications: dict[str, Any] = {}
    features: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductSearchRequest(BaseModel):
    """Request schema for product search."""

    query: str | None = Field(default=None, max_length=200, description="Search query text")
    category: str | None = Field(default=None, description="Filter by category")
    brand: str | None = Field(default=None, description="Filter by brand")
    min_price: float | None = Field(default=None, ge=0, description="Minimum price filter")
    max_price: float | None = Field(default=None, ge=0, description="Maximum price filter")
    min_rating: float | None = Field(default=None, ge=0, le=5, description="Minimum rating filter")
    in_stock_only: bool = Field(default=False, description="Only show in-stock items")
    sort_by: str = Field(
        default="relevance",
        pattern="^(relevance|price_asc|price_desc|rating|newest)$",
        description="Sort order",
    )
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=50, description="Results per page")


class ProductSearchResponse(BaseModel):
    """Response schema for product search."""

    products: list[ProductSummary]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters_applied: dict[str, Any] = {}


class ProductCompareRequest(BaseModel):
    """Request schema for product comparison."""

    product_ids: list[int] = Field(
        ..., min_length=2, max_length=4, description="Product IDs to compare (2-4 products)"
    )


class ProductCompareResponse(BaseModel):
    """Response schema for product comparison."""

    products: list[ProductSchema]
    comparison_fields: list[str]
    comparison_data: dict[str, dict[str, Any]]


class CategoryResponse(BaseModel):
    """Category with product count."""

    category: str
    count: int


class BrandResponse(BaseModel):
    """Brand with product count."""

    brand: str
    count: int
