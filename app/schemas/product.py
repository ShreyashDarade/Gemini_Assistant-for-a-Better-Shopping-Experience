"""
Product schemas for API requests/responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProductSummary(BaseModel):
    """Minimal product representation for lists."""
    
    id: int
    name: str
    brand: str
    category: str
    price: float
    original_price: Optional[float] = None
    currency: str = "USD"
    discount_percent: Optional[int] = None
    rating: float
    review_count: int
    image_url: Optional[str] = None
    in_stock: bool


class ProductSchema(BaseModel):
    """Full product representation."""
    
    id: int
    name: str
    description: str
    category: str
    subcategory: Optional[str] = None
    brand: str
    price: float
    original_price: Optional[float] = None
    currency: str = "USD"
    rating: float
    review_count: int
    stock: int
    sku: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    gallery_urls: List[str] = []
    tags: List[str] = []
    specifications: Dict[str, Any] = {}
    features: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductSearchRequest(BaseModel):
    """Request schema for product search."""
    
    query: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Search query text"
    )
    category: Optional[str] = Field(
        default=None,
        description="Filter by category"
    )
    brand: Optional[str] = Field(
        default=None,
        description="Filter by brand"
    )
    min_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Minimum price filter"
    )
    max_price: Optional[float] = Field(
        default=None,
        ge=0,
        description="Maximum price filter"
    )
    min_rating: Optional[float] = Field(
        default=None,
        ge=0,
        le=5,
        description="Minimum rating filter"
    )
    in_stock_only: bool = Field(
        default=False,
        description="Only show in-stock items"
    )
    sort_by: str = Field(
        default="relevance",
        pattern="^(relevance|price_asc|price_desc|rating|newest)$",
        description="Sort order"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number"
    )
    page_size: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Results per page"
    )


class ProductSearchResponse(BaseModel):
    """Response schema for product search."""
    
    products: List[ProductSummary]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters_applied: Dict[str, Any] = {}


class ProductCompareRequest(BaseModel):
    """Request schema for product comparison."""
    
    product_ids: List[int] = Field(
        ...,
        min_length=2,
        max_length=4,
        description="Product IDs to compare (2-4 products)"
    )


class ProductCompareResponse(BaseModel):
    """Response schema for product comparison."""
    
    products: List[ProductSchema]
    comparison_fields: List[str]
    comparison_data: Dict[str, Dict[str, Any]]


class CategoryResponse(BaseModel):
    """Category with product count."""
    
    category: str
    count: int


class BrandResponse(BaseModel):
    """Brand with product count."""
    
    brand: str
    count: int
