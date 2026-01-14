"""
Gemini AI client with connection pooling and retry logic for high concurrency.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Async Gemini client with connection pooling, retry logic, and rate limiting.
    Designed for high concurrency production use.
    """
    
    _instance: Optional["GeminiClient"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        """Singleton pattern for connection reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.settings = get_settings()
        self._initialized = True
        self._semaphore = asyncio.Semaphore(50)  # Max concurrent requests
        self._retry_count = 3
        self._retry_delay = 1.0
        
        # Configure Gemini
        genai.configure(api_key=self.settings.gemini_api_key)
        
        # Create model with safety settings
        self.model = genai.GenerativeModel(
            model_name=self.settings.ai_model,
            generation_config=GenerationConfig(
                max_output_tokens=self.settings.ai_max_tokens,
                temperature=self.settings.ai_temperature,
            )
        )
        
        logger.info(f"Gemini client initialized with model: {self.settings.ai_model}")
    
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: str = "text"
    ) -> str:
        """
        Generate text response from Gemini.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system context
            temperature: Override default temperature
            max_tokens: Override default max tokens
            response_format: "text" or "json"
        
        Returns:
            Generated text response
        """
        async with self._semaphore:
            return await self._generate_with_retry(
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
    
    async def _generate_with_retry(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: str = "text"
    ) -> str:
        """Generate with retry logic."""
        last_error = None
        
        for attempt in range(self._retry_count):
            try:
                # Build complete prompt
                full_prompt = prompt
                if system_instruction:
                    full_prompt = f"{system_instruction}\n\n{prompt}"
                
                if response_format == "json":
                    full_prompt += "\n\nRespond with valid JSON only, no markdown."
                
                # Create generation config override if needed
                config = None
                if temperature is not None or max_tokens is not None:
                    config = GenerationConfig(
                        temperature=temperature or self.settings.ai_temperature,
                        max_output_tokens=max_tokens or self.settings.ai_max_tokens,
                    )
                
                # Generate response (run sync in executor for true async)
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(
                        full_prompt,
                        generation_config=config
                    )
                )
                
                result = response.text.strip()
                
                # Clean JSON if needed
                if response_format == "json":
                    result = self._clean_json_response(result)
                
                return result
                
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Gemini request failed (attempt {attempt + 1}/{self._retry_count}): {e}"
                )
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))
        
        logger.error(f"Gemini request failed after {self._retry_count} attempts")
        raise last_error
    
    async def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response.
        
        Args:
            prompt: User prompt
            system_instruction: Optional system context
            schema: Optional JSON schema hint
        
        Returns:
            Parsed JSON dictionary
        """
        enhanced_prompt = prompt
        if schema:
            enhanced_prompt += f"\n\nExpected JSON schema: {json.dumps(schema)}"
        
        response = await self.generate(
            prompt=enhanced_prompt,
            system_instruction=system_instruction,
            response_format="json"
        )
        
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from AI: {e}")
    
    async def generate_with_context(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Generate response with conversation history context.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."} dicts
            system_instruction: Optional system context
        
        Returns:
            Generated response
        """
        # Build context string
        context_parts = []
        for msg in messages[-10:]:  # Last 10 messages for context
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context_parts.append(f"{role.upper()}: {content}")
        
        prompt = "\n".join(context_parts)
        
        if system_instruction:
            prompt = f"{system_instruction}\n\nConversation:\n{prompt}\n\nASSISTANT:"
        else:
            prompt = f"Conversation:\n{prompt}\n\nASSISTANT:"
        
        return await self.generate(prompt)
    
    def _clean_json_response(self, text: str) -> str:
        """Clean JSON response from markdown formatting."""
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            response = await self.generate(
                "Respond with exactly: OK",
                max_tokens=10
            )
            return "OK" in response.upper()
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            return False


# Global client instance with lazy initialization
_client: Optional[GeminiClient] = None


async def get_gemini_client() -> GeminiClient:
    """Get or create Gemini client instance."""
    global _client
    if _client is None:
        async with asyncio.Lock():
            if _client is None:
                _client = GeminiClient()
    return _client
