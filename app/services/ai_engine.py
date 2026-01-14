"""
AI Engine - Main orchestrator for processing shopping assistant queries.
Coordinates intent classification, entity extraction, context management, and response generation.
"""

import asyncio
import logging
import time
from typing import Optional

from app.services.intent_classifier import IntentClassifier, ClassifiedIntent, get_intent_classifier
from app.services.entity_extractor import EntityExtractor, ExtractedEntities, get_entity_extractor
from app.services.context_manager import ContextManager, ConversationContext, get_context_manager
from app.services.response_generator import ResponseGenerator, AssistantResponse, get_response_generator

logger = logging.getLogger(__name__)


class AIEngine:
    """
    Main AI orchestrator for the shopping assistant.
    Coordinates all AI services for processing user queries.
    Optimized for high concurrency with parallel processing.
    """
    
    def __init__(self):
        self._intent_classifier: Optional[IntentClassifier] = None
        self._entity_extractor: Optional[EntityExtractor] = None
        self._context_manager: Optional[ContextManager] = None
        self._response_generator: Optional[ResponseGenerator] = None
        self._semaphore = asyncio.Semaphore(100)  # Max concurrent requests
    
    async def _get_services(self):
        """Lazy initialize services."""
        if self._intent_classifier is None:
            self._intent_classifier = await get_intent_classifier()
        if self._entity_extractor is None:
            self._entity_extractor = await get_entity_extractor()
        if self._context_manager is None:
            self._context_manager = get_context_manager()
        if self._response_generator is None:
            self._response_generator = get_response_generator()
        
        return (
            self._intent_classifier,
            self._entity_extractor,
            self._context_manager,
            self._response_generator
        )
    
    async def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> dict:
        """
        Process a user query through the full AI pipeline.
        
        Pipeline:
        1. Get/create session context
        2. Classify intent (parallel with entity extraction)
        3. Extract entities (parallel with intent classification)
        4. Generate response based on intent, entities, and context
        5. Update context with new message
        
        Args:
            query: User's query text
            session_id: Optional existing session ID
            user_id: Optional user identifier
        
        Returns:
            Dict with response data, session_id, and metadata
        """
        async with self._semaphore:
            start_time = time.time()
            
            try:
                # Get services
                (
                    intent_classifier,
                    entity_extractor,
                    context_manager,
                    response_generator
                ) = await self._get_services()
                
                # Get or create session
                session_id = await context_manager.get_or_create_session(
                    session_id=session_id,
                    user_id=user_id
                )
                
                # Get conversation context
                context = await context_manager.get_context(session_id)
                
                # Get previous intent for context
                previous_intent = None
                if context.messages:
                    last_msg = context.messages[-1]
                    previous_intent = last_msg.get("intent")
                
                # Run intent classification and entity extraction in parallel
                intent_task = intent_classifier.classify(
                    query=query,
                    context=context.preferences,
                    previous_intent=previous_intent
                )
                
                # We need intent for entity extraction, so we'll do a quick pre-classify
                classified_intent = await intent_task
                
                # Now extract entities with intent context
                entities = await entity_extractor.extract(
                    query=query,
                    intent=classified_intent.intent,
                    context={
                        "preferences": context.preferences,
                        "previous_products": context.discussed_products[-5:] if context.discussed_products else []
                    }
                )
                
                # Save user message to context
                await context_manager.add_message(
                    session_id=session_id,
                    role="user",
                    content=query,
                    intent=classified_intent.intent.value,
                    intent_confidence=classified_intent.confidence,
                    entities=entities.to_dict()
                )
                
                # Generate response
                response = await response_generator.generate(
                    query=query,
                    intent=classified_intent.intent,
                    intent_confidence=classified_intent.confidence,
                    entities=entities,
                    context=context
                )
                
                # Save assistant response to context
                product_ids = [p.get("id") for p in response.products if p.get("id")]
                media_ids = [m.get("id") for m in response.media if m.get("id")]
                
                await context_manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response.message,
                    products_shown=product_ids,
                    media_shown=media_ids,
                    processing_time_ms=response.processing_time_ms
                )
                
                # Update preferences if entities reveal new preferences
                if entities.categories or entities.brands or entities.max_price:
                    await context_manager.update_preferences(
                        session_id=session_id,
                        preferences={
                            "categories": list(set(
                                context.preferences.get("categories", []) + entities.categories
                            )),
                            "brands": list(set(
                                context.preferences.get("brands", []) + entities.brands
                            )),
                            "max_price": entities.max_price or context.preferences.get("max_price"),
                        }
                    )
                
                total_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "response": response.to_dict(),
                    "metadata": {
                        "total_processing_time_ms": total_time_ms,
                        "intent": classified_intent.intent.value,
                        "intent_confidence": classified_intent.confidence,
                        "entities_extracted": entities.has_search_filters(),
                    }
                }
                
            except Exception as e:
                logger.exception(f"Error processing query: {e}")
                total_time_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "success": False,
                    "session_id": session_id,
                    "error": str(e),
                    "response": {
                        "message": "I apologize, but I encountered an error processing your request. Please try again.",
                        "intent": "error",
                        "intent_confidence": 0,
                        "products": [],
                        "media": [],
                        "suggestions": ["Try again", "Rephrase your question", "Contact support"],
                    },
                    "metadata": {
                        "total_processing_time_ms": total_time_ms,
                    }
                }
    
    async def get_session_history(
        self,
        session_id: str,
        limit: int = 20
    ) -> dict:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum messages to return
        
        Returns:
            Dict with session info and messages
        """
        context_manager = get_context_manager()
        context = await context_manager.get_context(session_id)
        
        return {
            "session_id": session_id,
            "messages": context.messages[-limit:],
            "preferences": context.preferences,
            "discussed_products": context.discussed_products,
        }
    
    async def clear_session(self, session_id: str) -> bool:
        """Clear a conversation session."""
        context_manager = get_context_manager()
        await context_manager.clear_session(session_id)
        return True
    
    async def health_check(self) -> dict:
        """Check health of AI services."""
        from app.services.gemini_client import get_gemini_client
        
        try:
            client = await get_gemini_client()
            gemini_ok = await client.health_check()
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            gemini_ok = False
        
        return {
            "gemini_api": gemini_ok,
            "status": "healthy" if gemini_ok else "degraded"
        }


# Singleton instance
_ai_engine: Optional[AIEngine] = None


def get_ai_engine() -> AIEngine:
    """Get or create AI engine instance."""
    global _ai_engine
    if _ai_engine is None:
        _ai_engine = AIEngine()
    return _ai_engine
