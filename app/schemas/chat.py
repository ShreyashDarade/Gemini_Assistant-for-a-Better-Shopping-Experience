"""
Chat request/response schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's message"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional context"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I need a laptop for programming",
                "context": {"budget": "medium"}
            }
        }


class ProductSummaryResponse(BaseModel):
    """Product summary in chat response."""
    
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


class MediaItemResponse(BaseModel):
    """Media item in chat response."""
    
    id: int
    title: str
    type: str
    category: str
    url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None


class ComparisonResponse(BaseModel):
    """Product comparison in chat response."""
    
    products: List[Dict[str, Any]]
    comparison_fields: List[str]
    comparison_data: Dict[str, Dict[str, Any]]


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    
    success: bool = True
    session_id: str
    message: str
    intent: str
    intent_confidence: float
    products: List[ProductSummaryResponse] = []
    media: List[MediaItemResponse] = []
    comparison: Optional[ComparisonResponse] = None
    suggestions: List[str] = []
    processing_time_ms: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "session_id": "abc123",
                "message": "I found some great laptops for programming!",
                "intent": "product_search",
                "intent_confidence": 0.95,
                "products": [
                    {
                        "id": 1,
                        "name": "MacBook Pro 14\"",
                        "brand": "Apple",
                        "category": "laptops",
                        "price": 1999.00,
                        "rating": 4.8,
                        "review_count": 1250,
                        "in_stock": True
                    }
                ],
                "suggestions": ["Compare products", "Filter by price"],
                "processing_time_ms": 450
            }
        }


class MessageSchema(BaseModel):
    """Schema for conversation message."""
    
    id: Optional[int] = None
    role: str
    content: str
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    entities: Dict[str, Any] = {}
    products_shown: List[int] = []
    media_shown: List[int] = []
    timestamp: Optional[datetime] = None


class ConversationHistoryResponse(BaseModel):
    """Response schema for conversation history."""
    
    session_id: str
    messages: List[MessageSchema]
    preferences: Dict[str, Any] = {}
    discussed_products: List[int] = []


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
