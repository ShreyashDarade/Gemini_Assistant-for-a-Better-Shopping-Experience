"""
Product model for the shopping assistant.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


class Product(Base):
    """Product model with full-text search support."""
    
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Pricing
    price: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    
    # Rating and Reviews
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Inventory
    stock: Mapped[int] = mapped_column(Integer, default=0)
    sku: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True)
    
    # Media
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    gallery_urls: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    
    # Metadata
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    specifications: Mapped[dict] = mapped_column(JSON, default=dict)
    features: Mapped[List[str]] = mapped_column(JSON, default=list)
    
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
    
    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_product_category_price", "category", "price"),
        Index("idx_product_brand_category", "brand", "category"),
        Index("idx_product_rating", "rating", "review_count"),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "subcategory": self.subcategory,
            "brand": self.brand,
            "price": self.price,
            "original_price": self.original_price,
            "currency": self.currency,
            "rating": self.rating,
            "review_count": self.review_count,
            "stock": self.stock,
            "sku": self.sku,
            "image_url": self.image_url,
            "thumbnail_url": self.thumbnail_url,
            "video_url": self.video_url,
            "gallery_urls": self.gallery_urls or [],
            "tags": self.tags or [],
            "specifications": self.specifications or {},
            "features": self.features or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def to_summary(self) -> dict:
        """Convert to summary representation (for lists)."""
        discount = None
        if self.original_price and self.original_price > self.price:
            discount = round((1 - self.price / self.original_price) * 100)
        
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand,
            "category": self.category,
            "price": self.price,
            "original_price": self.original_price,
            "currency": self.currency,
            "discount_percent": discount,
            "rating": self.rating,
            "review_count": self.review_count,
            "image_url": self.image_url,
            "in_stock": self.stock > 0,
        }
