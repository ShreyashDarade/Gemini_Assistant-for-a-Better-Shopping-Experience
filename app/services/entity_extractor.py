"""
Entity extraction service using Gemini AI.
Extracts structured data from user queries.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.gemini_client import get_gemini_client
from app.services.intent_classifier import IntentType

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntities:
    """Structured entities extracted from user query."""

    # Product-related
    product_names: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    brands: list[str] = field(default_factory=list)

    # Price-related
    min_price: float | None = None
    max_price: float | None = None
    currency: str = "USD"

    # Attributes
    colors: list[str] = field(default_factory=list)
    sizes: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)

    # Quantity
    quantity: int | None = None

    # User preferences
    sort_preference: str | None = None  # price_asc, price_desc, rating, newest

    # For comparisons
    comparison_items: list[str] = field(default_factory=list)

    # For troubleshooting
    issue_description: str | None = None
    product_model: str | None = None

    # Raw attributes for flexibility
    raw_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "product_names": self.product_names,
            "categories": self.categories,
            "brands": self.brands,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "currency": self.currency,
            "colors": self.colors,
            "sizes": self.sizes,
            "features": self.features,
            "quantity": self.quantity,
            "sort_preference": self.sort_preference,
            "comparison_items": self.comparison_items,
            "issue_description": self.issue_description,
            "product_model": self.product_model,
            "raw_attributes": self.raw_attributes,
        }

    def has_search_filters(self) -> bool:
        """Check if any search filters are present."""
        return bool(
            self.product_names
            or self.categories
            or self.brands
            or self.min_price is not None
            or self.max_price is not None
            or self.features
        )


class EntityExtractor:
    """
    Extracts structured entities from shopping queries using Gemini AI.
    """

    SYSTEM_INSTRUCTION = """You are an entity extractor for a shopping assistant.
Extract structured information from user queries about products, prices, features, and preferences.
Be precise and only extract what is explicitly mentioned or clearly implied."""

    EXTRACTION_PROMPT = """Extract entities from this shopping query:

Query: "{query}"
Intent: {intent}
{context_section}

Extract and return as JSON:
{{
    "product_names": ["specific product names mentioned"],
    "categories": ["product categories like 'laptop', 'phone', 'shoes'"],
    "brands": ["brand names like 'Apple', 'Nike', 'Samsung'"],
    "min_price": <minimum price as number or null>,
    "max_price": <maximum price as number or null>,
    "currency": "<currency code, default USD>",
    "colors": ["color preferences"],
    "sizes": ["size preferences"],
    "features": ["desired features like '16GB RAM', 'waterproof'"],
    "quantity": <number or null>,
    "sort_preference": "<price_asc|price_desc|rating|newest or null>",
    "comparison_items": ["items to compare if intent is compare"],
    "issue_description": "<problem description if troubleshooting>",
    "product_model": "<specific model number/name>"
}}

Only include fields with actual values. Use null for missing values."""

    def __init__(self):
        self._client = None

    async def _get_client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            self._client = await get_gemini_client()
        return self._client

    async def extract(
        self, query: str, intent: IntentType, context: dict[str, Any] | None = None
    ) -> ExtractedEntities:
        """
        Extract structured entities from user query.

        Args:
            query: User's query text
            intent: Classified intent type
            context: Conversation context

        Returns:
            ExtractedEntities with all extracted information
        """
        context_section = ""
        if context:
            # Include relevant context
            if context.get("preferences"):
                context_section = f"\nUser preferences: {context.get('preferences')}"
            if context.get("previous_products"):
                context_section += f"\nPreviously discussed: {context.get('previous_products')}"

        prompt = self.EXTRACTION_PROMPT.format(
            query=query, intent=intent.value, context_section=context_section
        )

        try:
            client = await self._get_client()
            response = await client.generate_json(
                prompt=prompt, system_instruction=self.SYSTEM_INSTRUCTION
            )

            return self._parse_response(response)

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            # Return basic extraction from keywords
            return self._fallback_extract(query, intent)

    def _parse_response(self, response: dict[str, Any]) -> ExtractedEntities:
        """Parse JSON response into ExtractedEntities."""
        return ExtractedEntities(
            product_names=response.get("product_names", []) or [],
            categories=response.get("categories", []) or [],
            brands=response.get("brands", []) or [],
            min_price=response.get("min_price"),
            max_price=response.get("max_price"),
            currency=response.get("currency", "USD"),
            colors=response.get("colors", []) or [],
            sizes=response.get("sizes", []) or [],
            features=response.get("features", []) or [],
            quantity=response.get("quantity"),
            sort_preference=response.get("sort_preference"),
            comparison_items=response.get("comparison_items", []) or [],
            issue_description=response.get("issue_description"),
            product_model=response.get("product_model"),
            raw_attributes=response,
        )

    def _fallback_extract(self, query: str, intent: IntentType) -> ExtractedEntities:
        """Basic keyword-based entity extraction as fallback."""
        entities = ExtractedEntities()
        query_lower = query.lower()

        # Extract price ranges
        import re

        # Pattern: under/below $X
        under_match = re.search(
            r"(?:under|below|less than)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", query_lower
        )
        if under_match:
            entities.max_price = float(under_match.group(1).replace(",", ""))

        # Pattern: over/above $X
        over_match = re.search(
            r"(?:over|above|more than)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)", query_lower
        )
        if over_match:
            entities.min_price = float(over_match.group(1).replace(",", ""))

        # Pattern: $X - $Y or $X to $Y
        range_match = re.search(
            r"\$?(\d+(?:,\d{3})*)\s*(?:-|to)\s*\$?(\d+(?:,\d{3})*)", query_lower
        )
        if range_match:
            entities.min_price = float(range_match.group(1).replace(",", ""))
            entities.max_price = float(range_match.group(2).replace(",", ""))

        # Common categories
        categories = {
            "laptop": ["laptop", "laptops", "notebook", "macbook"],
            "phone": ["phone", "phones", "smartphone", "mobile", "iphone", "android"],
            "tablet": ["tablet", "tablets", "ipad"],
            "headphones": ["headphones", "earbuds", "earphones", "airpods"],
            "shoes": ["shoes", "sneakers", "boots", "sandals"],
            "clothing": ["shirt", "pants", "dress", "jacket", "coat"],
            "electronics": ["tv", "television", "camera", "speaker"],
        }

        for category, keywords in categories.items():
            if any(kw in query_lower for kw in keywords):
                entities.categories.append(category)

        # Common brands
        brands = [
            "apple",
            "samsung",
            "google",
            "sony",
            "nike",
            "adidas",
            "microsoft",
            "dell",
            "hp",
            "lenovo",
        ]
        for brand in brands:
            if brand in query_lower:
                entities.brands.append(brand.title())

        # Colors
        colors = ["red", "blue", "green", "black", "white", "silver", "gold", "pink", "purple"]
        for color in colors:
            if color in query_lower:
                entities.colors.append(color)

        return entities


# Singleton instance
_extractor: EntityExtractor | None = None


async def get_entity_extractor() -> EntityExtractor:
    """Get or create entity extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = EntityExtractor()
    return _extractor
