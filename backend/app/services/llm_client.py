"""
LLM client for AI operations.
Supports OpenAI and Anthropic models with unified interface.
"""
from typing import Literal

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    Provides async interface for AI operations.
    """

    def __init__(self):
        """Initialize LLM clients."""
        settings = get_settings()

        self.openai_client = AsyncOpenAI(
            api_key=settings.openai_api_key
        ) if settings.openai_api_key else None

        self.anthropic_client = AsyncAnthropic(
            api_key=settings.anthropic_api_key
        ) if settings.anthropic_api_key else None

        self.default_model = settings.openai_model

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: Literal["openai", "anthropic"] = "openai",
    ) -> str:
        """
        Generate completion from LLM.

        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            provider: LLM provider to use

        Returns:
            Generated completion text

        Raises:
            ValueError: If provider not configured
        """
        if provider == "openai":
            return await self._complete_openai(
                prompt, system_prompt, temperature, max_tokens
            )
        elif provider == "anthropic":
            return await self._complete_anthropic(
                prompt, system_prompt, temperature, max_tokens
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def _complete_openai(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """OpenAI completion implementation."""
        if not self.openai_client:
            raise ValueError("OpenAI client not configured")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.openai_client.chat.completions.create(
            model=self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content

    async def _complete_anthropic(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Anthropic completion implementation."""
        if not self.anthropic_client:
            raise ValueError("Anthropic client not configured")

        response = await self.anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text

    async def embed(
        self,
        text: str,
        model: str = "text-embedding-3-small"
    ) -> list[float]:
        """
        Generate embeddings for text.

        Args:
            text: Text to embed
            model: Embedding model to use

        Returns:
            Embedding vector

        Raises:
            ValueError: If OpenAI client not configured
        """
        if not self.openai_client:
            raise ValueError("OpenAI client not configured for embeddings")

        response = await self.openai_client.embeddings.create(
            model=model,
            input=text,
        )

        return response.data[0].embedding


# Global LLM client instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """
    Get LLM client instance.

    Returns:
        LLM client instance
    """
    global _llm_client

    if _llm_client is None:
        _llm_client = LLMClient()
        logger.info("LLM client initialized")

    return _llm_client
