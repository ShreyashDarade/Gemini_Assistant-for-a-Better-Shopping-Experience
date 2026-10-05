"""
Chat request/response schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    context: dict[str, Any] | None = Field(default=None, description="Optional additional context")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "I need a laptop for programming",
                "context": {"budget": "medium"},
            }
        }
    )


class ProductSummaryResponse(BaseModel):
    """Product summary in chat response."""

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


class MediaItemResponse(BaseModel):
    """Media item in chat response."""

    id: int
    title: str
    type: str
    category: str
    url: str
    thumbnail_url: str | None = None
    duration_seconds: int | None = None


class ComparisonResponse(BaseModel):
    """Product comparison in chat response."""

    products: list[dict[str, Any]]
    comparison_fields: list[str]
    comparison_data: dict[str, dict[str, Any]]


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""

    success: bool = True
    session_id: str
    message: str
    intent: str
    intent_confidence: float
    products: list[ProductSummaryResponse] = []
    media: list[MediaItemResponse] = []
    comparison: ComparisonResponse | None = None
    suggestions: list[str] = []
    processing_time_ms: int = 0

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "session_id": "abc123",
                "message": "I found some great laptops for programming!",
                "intent": "product_search",
                "intent_confidence": 0.95,
                "products": [
                    {
                        "id": 1,
                        "name": 'MacBook Pro 14"',
                        "brand": "Apple",
                        "category": "laptops",
                        "price": 1999.00,
                        "rating": 4.8,
                        "review_count": 1250,
                        "in_stock": True,
                    }
                ],
                "suggestions": ["Compare products", "Filter by price"],
                "processing_time_ms": 450,
            }
        }
    )


class MessageSchema(BaseModel):
    """Schema for conversation message."""

    id: int | None = None
    role: str
    content: str
    intent: str | None = None
    intent_confidence: float | None = None
    entities: dict[str, Any] = {}
    products_shown: list[int] = []
    media_shown: list[int] = []
    timestamp: datetime | None = None


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""

    session_id: str
    messages: list[MessageSchema]
    preferences: dict[str, Any] = {}
    discussed_products: list[int] = []


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: str
    error_code: str | None = None
    details: dict[str, Any] | None = None
