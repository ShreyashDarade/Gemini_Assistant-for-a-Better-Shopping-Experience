"""
Intent classification service using Gemini AI.
Classifies user queries into shopping intents.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Shopping assistant intent types."""
    PRODUCT_SEARCH = "product_search"
    PRODUCT_COMPARE = "product_compare"
    PRODUCT_RECOMMEND = "product_recommend"
    TROUBLESHOOT = "troubleshoot"
    ORDER_STATUS = "order_status"
    GENERAL_QUERY = "general_query"
    GREETING = "greeting"
    FAREWELL = "farewell"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""
    intent: IntentType
    confidence: float
    sub_intent: Optional[str] = None
    reasoning: Optional[str] = None


class IntentClassifier:
    """
    Classifies user queries into shopping intents using Gemini AI.
    Optimized for high concurrency with caching.
    """
    
    SYSTEM_INSTRUCTION = """You are an intent classifier for a shopping assistant.
Classify user queries into one of these categories:

- product_search: User wants to find specific products (e.g., "show me laptops", "find blue shoes")
- product_compare: User wants to compare products (e.g., "compare iPhone vs Samsung", "which is better")
- product_recommend: User wants personalized recommendations (e.g., "what phone should I buy", "suggest a gift")
- troubleshoot: User needs help with a product issue (e.g., "my laptop won't start", "how to set up")
- order_status: User asking about orders (e.g., "where is my order", "track my package")
- general_query: General questions (e.g., "what's your return policy", "store hours")
- greeting: User is greeting (e.g., "hi", "hello", "good morning")
- farewell: User is saying goodbye (e.g., "bye", "thanks", "that's all")
- unknown: Cannot determine intent

Consider conversation context when classifying. Be concise and accurate."""

    CLASSIFICATION_PROMPT = """Classify this user query:

Query: "{query}"
{context_section}

Respond with JSON ONLY:
{{
    "intent": "<intent_type>",
    "confidence": <0.0-1.0>,
    "sub_intent": "<optional specific sub-intent>",
    "reasoning": "<brief explanation>"
}}"""

    def __init__(self):
        self._client = None
    
    async def _get_client(self):
        """Lazy load Gemini client."""
        if self._client is None:
            self._client = await get_gemini_client()
        return self._client
    
    async def classify(
        self,
        query: str,
        context: Optional[dict] = None,
        previous_intent: Optional[str] = None
    ) -> ClassifiedIntent:
        """
        Classify user query into a shopping intent.
        
        Args:
            query: User's query text
            context: Conversation context (preferences, history)
            previous_intent: Previous turn's intent for context
        
        Returns:
            ClassifiedIntent with type, confidence, and reasoning
        """
        # Build context section
        context_section = ""
        if context:
            context_section = f"\nContext: {context}"
        if previous_intent:
            context_section += f"\nPrevious intent: {previous_intent}"
        
        prompt = self.CLASSIFICATION_PROMPT.format(
            query=query,
            context_section=context_section
        )
        
        try:
            client = await self._get_client()
            response = await client.generate_json(
                prompt=prompt,
                system_instruction=self.SYSTEM_INSTRUCTION
            )
            
            intent_str = response.get("intent", "unknown").lower()
            
            # Map to enum
            try:
                intent = IntentType(intent_str)
            except ValueError:
                logger.warning(f"Unknown intent returned: {intent_str}")
                intent = IntentType.UNKNOWN
            
            return ClassifiedIntent(
                intent=intent,
                confidence=float(response.get("confidence", 0.5)),
                sub_intent=response.get("sub_intent"),
                reasoning=response.get("reasoning")
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            # Fallback to basic keyword matching
            return self._fallback_classify(query)
    
    def _fallback_classify(self, query: str) -> ClassifiedIntent:
        """Fallback classification using keywords when AI fails."""
        query_lower = query.lower()
        
        # Greeting patterns
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        if any(g in query_lower for g in greetings):
            return ClassifiedIntent(intent=IntentType.GREETING, confidence=0.8)
        
        # Farewell patterns
        farewells = ["bye", "goodbye", "thanks", "thank you", "that's all"]
        if any(f in query_lower for f in farewells):
            return ClassifiedIntent(intent=IntentType.FAREWELL, confidence=0.8)
        
        # Search patterns
        search_words = ["find", "search", "show", "looking for", "need", "want", "buy"]
        if any(s in query_lower for s in search_words):
            return ClassifiedIntent(intent=IntentType.PRODUCT_SEARCH, confidence=0.7)
        
        # Compare patterns
        compare_words = ["compare", "vs", "versus", "difference", "which is better"]
        if any(c in query_lower for c in compare_words):
            return ClassifiedIntent(intent=IntentType.PRODUCT_COMPARE, confidence=0.7)
        
        # Recommend patterns
        recommend_words = ["recommend", "suggest", "advice", "should i buy", "best"]
        if any(r in query_lower for r in recommend_words):
            return ClassifiedIntent(intent=IntentType.PRODUCT_RECOMMEND, confidence=0.7)
        
        # Troubleshoot patterns
        trouble_words = ["help", "problem", "issue", "broken", "not working", "how to", "setup"]
        if any(t in query_lower for t in trouble_words):
            return ClassifiedIntent(intent=IntentType.TROUBLESHOOT, confidence=0.7)
        
        # Order patterns
        order_words = ["order", "delivery", "shipping", "track", "package"]
        if any(o in query_lower for o in order_words):
            return ClassifiedIntent(intent=IntentType.ORDER_STATUS, confidence=0.7)
        
        return ClassifiedIntent(intent=IntentType.GENERAL_QUERY, confidence=0.5)
    
    async def batch_classify(
        self,
        queries: list[str],
        context: Optional[dict] = None
    ) -> list[ClassifiedIntent]:
        """Classify multiple queries concurrently."""
        import asyncio
        
        tasks = [
            self.classify(query, context)
            for query in queries
        ]
        return await asyncio.gather(*tasks)


# Singleton instance
_classifier: Optional[IntentClassifier] = None


async def get_intent_classifier() -> IntentClassifier:
    """Get or create intent classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier
