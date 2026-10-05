"""
Response generator that creates AI responses based on intent and context.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.services.context_manager import ConversationContext
from app.services.entity_extractor import ExtractedEntities
from app.services.gemini_client import get_gemini_client
from app.services.intent_classifier import IntentType
from app.services.media_service import get_media_service
from app.services.product_service import ProductSearchResult, get_product_service

logger = logging.getLogger(__name__)


@dataclass
class AssistantResponse:
    """Structured response from the assistant."""

    message: str
    intent: IntentType
    intent_confidence: float
    products: list[dict[str, Any]] = field(default_factory=list)
    media: list[dict[str, Any]] = field(default_factory=list)
    comparison: dict[str, Any] | None = None
    suggestions: list[str] = field(default_factory=list)
    processing_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message": self.message,
            "intent": self.intent.value,
            "intent_confidence": self.intent_confidence,
            "products": self.products,
            "media": self.media,
            "comparison": self.comparison,
            "suggestions": self.suggestions,
            "processing_time_ms": self.processing_time_ms,
        }


class ResponseGenerator:
    """
    Generates contextual responses based on intent and extracted entities.
    Orchestrates product search, recommendations, and AI-generated text.
    """

    SYSTEM_INSTRUCTION = """You are a helpful shopping assistant. Be concise, friendly, and informative.
Focus on helping the customer find what they need. When showing products, highlight key features and value.
For troubleshooting, provide clear step-by-step guidance.
Keep responses under 150 words unless more detail is needed."""

    RESPONSE_PROMPTS = {
        IntentType.PRODUCT_SEARCH: """Generate a helpful response for a product search.
User query: {query}
Found {count} products matching: {filters}
Top products: {products}

Write a brief, friendly response introducing these products. Highlight key differences and value propositions.
Keep it under 100 words.""",
        IntentType.PRODUCT_COMPARE: """Generate a product comparison response.
User query: {query}
Products being compared: {products}
Comparison data: {comparison}

Write a helpful comparison summary highlighting key differences, pros and cons.
Help the user make an informed decision. Keep it under 150 words.""",
        IntentType.PRODUCT_RECOMMEND: """Generate personalized product recommendations.
User query: {query}
User preferences: {preferences}
Recommended products: {products}

Write a friendly response explaining why these products are recommended.
Be personal and helpful. Keep it under 100 words.""",
        IntentType.TROUBLESHOOT: """Generate a troubleshooting response.
User query: {query}
Issue: {issue}
Available tutorials: {tutorials}

Provide helpful troubleshooting steps. If tutorials are available, mention them.
Be clear and reassuring. Keep it under 150 words.""",
        IntentType.GENERAL_QUERY: """Generate a helpful response to a general question.
User query: {query}
Context: {context}

Provide a helpful, accurate response. Keep it under 100 words.""",
        IntentType.GREETING: """Generate a friendly greeting for a shopping assistant.
User message: {query}

Respond warmly and offer to help with shopping needs. Keep it brief and welcoming.""",
        IntentType.FAREWELL: """Generate a friendly farewell response.
User message: {query}

Thank them and invite them to return. Keep it brief and warm.""",
    }

    def __init__(self):
        self._client = None
        self._product_service = None
        self._media_service = None

    async def _get_client(self):
        if self._client is None:
            self._client = await get_gemini_client()
        return self._client

    async def _get_product_service(self):
        if self._product_service is None:
            self._product_service = get_product_service()
        return self._product_service

    async def _get_media_service(self):
        if self._media_service is None:
            self._media_service = get_media_service()
        return self._media_service

    async def generate(
        self,
        query: str,
        intent: IntentType,
        intent_confidence: float,
        entities: ExtractedEntities,
        context: ConversationContext,
    ) -> AssistantResponse:
        """
        Generate a response based on intent and context.

        Args:
            query: User's query
            intent: Classified intent
            intent_confidence: Intent confidence score
            entities: Extracted entities
            context: Conversation context

        Returns:
            AssistantResponse with message, products, and media
        """
        start_time = time.time()

        try:
            if intent == IntentType.PRODUCT_SEARCH:
                response = await self._handle_product_search(
                    query, entities, context, intent_confidence
                )
            elif intent == IntentType.PRODUCT_COMPARE:
                response = await self._handle_product_compare(
                    query, entities, context, intent_confidence
                )
            elif intent == IntentType.PRODUCT_RECOMMEND:
                response = await self._handle_product_recommend(
                    query, entities, context, intent_confidence
                )
            elif intent == IntentType.TROUBLESHOOT:
                response = await self._handle_troubleshoot(
                    query, entities, context, intent_confidence
                )
            elif intent == IntentType.GREETING:
                response = await self._handle_greeting(query, intent_confidence)
            elif intent == IntentType.FAREWELL:
                response = await self._handle_farewell(query, intent_confidence)
            else:
                response = await self._handle_general_query(query, context, intent_confidence)

            response.processing_time_ms = int((time.time() - start_time) * 1000)
            return response

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return AssistantResponse(
                message="I apologize, but I encountered an issue processing your request. Could you please try rephrasing your question?",
                intent=intent,
                intent_confidence=intent_confidence,
                suggestions=[
                    "Try a different search",
                    "Ask for recommendations",
                    "Get help with a product",
                ],
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

    async def _handle_product_search(
        self,
        query: str,
        entities: ExtractedEntities,
        context: ConversationContext,
        confidence: float,
    ) -> AssistantResponse:
        """Handle product search intent."""
        product_service = await self._get_product_service()

        # Search products
        result = await product_service.search(
            query=query if not entities.has_search_filters() else None,
            entities=entities,
            page_size=5,
        )

        if not result.products:
            return AssistantResponse(
                message="I couldn't find any products matching your criteria. Would you like to try different filters or browse our categories?",
                intent=IntentType.PRODUCT_SEARCH,
                intent_confidence=confidence,
                suggestions=["Show all laptops", "Browse categories", "Get recommendations"],
            )

        # Generate AI message
        client = await self._get_client()
        prompt = self.RESPONSE_PROMPTS[IntentType.PRODUCT_SEARCH].format(
            query=query,
            count=result.total_count,
            filters=result.filters_applied,
            products=[p.to_summary() for p in result.products[:3]],
        )

        message = await client.generate(prompt=prompt, system_instruction=self.SYSTEM_INSTRUCTION)

        return AssistantResponse(
            message=message,
            intent=IntentType.PRODUCT_SEARCH,
            intent_confidence=confidence,
            products=[p.to_summary() for p in result.products],
            suggestions=self._generate_search_suggestions(entities, result),
        )

    async def _handle_product_compare(
        self,
        query: str,
        entities: ExtractedEntities,
        context: ConversationContext,
        confidence: float,
    ) -> AssistantResponse:
        """Handle product comparison intent."""
        product_service = await self._get_product_service()

        # Get products to compare
        products_to_compare = []

        if entities.comparison_items:
            # Search for mentioned products
            for item in entities.comparison_items[:4]:
                result = await product_service.search(query=item, page_size=1)
                if result.products:
                    products_to_compare.append(result.products[0])

        if len(products_to_compare) < 2 and context.discussed_products:
            # Use previously discussed products
            additional = await product_service.get_by_ids(context.discussed_products[-4:])
            products_to_compare.extend(additional)
            products_to_compare = products_to_compare[:4]

        if len(products_to_compare) < 2:
            return AssistantResponse(
                message="I need at least two products to compare. Could you specify which products you'd like to compare?",
                intent=IntentType.PRODUCT_COMPARE,
                intent_confidence=confidence,
                suggestions=[
                    "Compare iPhone 15 vs Samsung S24",
                    "Show me similar products",
                    "Search for products first",
                ],
            )

        # Get comparison
        comparison = await product_service.compare([p.id for p in products_to_compare])

        # Generate AI message
        client = await self._get_client()
        prompt = self.RESPONSE_PROMPTS[IntentType.PRODUCT_COMPARE].format(
            query=query,
            products=[p.name for p in products_to_compare],
            comparison=comparison.comparison_data,
        )

        message = await client.generate(prompt=prompt, system_instruction=self.SYSTEM_INSTRUCTION)

        return AssistantResponse(
            message=message,
            intent=IntentType.PRODUCT_COMPARE,
            intent_confidence=confidence,
            products=[p.to_dict() for p in products_to_compare],
            comparison=comparison.to_dict(),
            suggestions=["Show more details", "Find similar products", "Ready to buy?"],
        )

    async def _handle_product_recommend(
        self,
        query: str,
        entities: ExtractedEntities,
        context: ConversationContext,
        confidence: float,
    ) -> AssistantResponse:
        """Handle product recommendation intent."""
        product_service = await self._get_product_service()

        # Build preferences from entities and context
        preferences = {
            **context.preferences,
            "categories": entities.categories or context.preferences.get("categories", []),
            "brands": entities.brands or context.preferences.get("brands", []),
            "max_price": entities.max_price or context.preferences.get("max_price"),
            "min_rating": 4.0,  # Recommend good products
        }

        recommendations = await product_service.get_recommendations(
            preferences=preferences, discussed_products=context.discussed_products, limit=5
        )

        if not recommendations:
            # Fallback to top-rated products
            result = await product_service.search(min_rating=4.0, sort_by="rating", page_size=5)
            recommendations = result.products

        if not recommendations:
            return AssistantResponse(
                message="I'm having trouble finding recommendations. Could you tell me more about what you're looking for?",
                intent=IntentType.PRODUCT_RECOMMEND,
                intent_confidence=confidence,
                suggestions=[
                    "What categories interest you?",
                    "Any brand preferences?",
                    "What's your budget?",
                ],
            )

        # Generate AI message
        client = await self._get_client()
        prompt = self.RESPONSE_PROMPTS[IntentType.PRODUCT_RECOMMEND].format(
            query=query,
            preferences=preferences,
            products=[p.to_summary() for p in recommendations[:3]],
        )

        message = await client.generate(prompt=prompt, system_instruction=self.SYSTEM_INSTRUCTION)

        return AssistantResponse(
            message=message,
            intent=IntentType.PRODUCT_RECOMMEND,
            intent_confidence=confidence,
            products=[p.to_summary() for p in recommendations],
            suggestions=["Compare these products", "Show more like this", "Different budget?"],
        )

    async def _handle_troubleshoot(
        self,
        query: str,
        entities: ExtractedEntities,
        context: ConversationContext,
        confidence: float,
    ) -> AssistantResponse:
        """Handle troubleshooting intent."""
        media_service = await self._get_media_service()

        # Find relevant tutorials
        tutorials = await media_service.find_tutorials(
            issue=entities.issue_description or query,
            product_id=context.discussed_products[-1] if context.discussed_products else None,
            limit=3,
        )

        # Generate AI troubleshooting response
        client = await self._get_client()
        prompt = self.RESPONSE_PROMPTS[IntentType.TROUBLESHOOT].format(
            query=query,
            issue=entities.issue_description or query,
            tutorials=[t.to_summary() for t in tutorials]
            if tutorials
            else "No specific tutorials found",
        )

        message = await client.generate(prompt=prompt, system_instruction=self.SYSTEM_INSTRUCTION)

        return AssistantResponse(
            message=message,
            intent=IntentType.TROUBLESHOOT,
            intent_confidence=confidence,
            media=[t.to_summary() for t in tutorials],
            suggestions=["Contact support", "Find more guides", "Search for parts"],
        )

    async def _handle_greeting(self, query: str, confidence: float) -> AssistantResponse:
        """Handle greeting intent."""
        client = await self._get_client()

        message = await client.generate(
            prompt=self.RESPONSE_PROMPTS[IntentType.GREETING].format(query=query),
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        return AssistantResponse(
            message=message,
            intent=IntentType.GREETING,
            intent_confidence=confidence,
            suggestions=["Search for products", "Get recommendations", "Browse categories"],
        )

    async def _handle_farewell(self, query: str, confidence: float) -> AssistantResponse:
        """Handle farewell intent."""
        client = await self._get_client()

        message = await client.generate(
            prompt=self.RESPONSE_PROMPTS[IntentType.FAREWELL].format(query=query),
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        return AssistantResponse(
            message=message,
            intent=IntentType.FAREWELL,
            intent_confidence=confidence,
        )

    async def _handle_general_query(
        self, query: str, context: ConversationContext, confidence: float
    ) -> AssistantResponse:
        """Handle general queries."""
        client = await self._get_client()

        message = await client.generate(
            prompt=self.RESPONSE_PROMPTS[IntentType.GENERAL_QUERY].format(
                query=query, context=context.get_context_summary()
            ),
            system_instruction=self.SYSTEM_INSTRUCTION,
        )

        return AssistantResponse(
            message=message,
            intent=IntentType.GENERAL_QUERY,
            intent_confidence=confidence,
            suggestions=["Search for products", "Get recommendations", "Need help with something?"],
        )

    def _generate_search_suggestions(
        self, entities: ExtractedEntities, result: ProductSearchResult
    ) -> list[str]:
        """Generate contextual search suggestions."""
        suggestions = []

        if not entities.max_price:
            suggestions.append("Filter by price")

        if not entities.brands and result.products:
            brands = list({p.brand for p in result.products[:3]})
            if brands:
                suggestions.append(f"Filter by {brands[0]}")

        suggestions.append("Compare products")
        suggestions.append("Get recommendations")

        return suggestions[:3]


# Singleton instance
_response_generator: ResponseGenerator | None = None


def get_response_generator() -> ResponseGenerator:
    """Get or create response generator instance."""
    global _response_generator
    if _response_generator is None:
        _response_generator = ResponseGenerator()
    return _response_generator
