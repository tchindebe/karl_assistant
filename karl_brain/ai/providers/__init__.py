"""
Registry et factory des providers LLM.

Providers disponibles:
  - "anthropic" : Claude (claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5...)
  - "openai"    : OpenAI (gpt-4o, gpt-4o-mini, o1, o3-mini...)
  - "ollama"    : Ollama local (llama3.1, mistral, qwen2.5, deepseek-r1...)
  - "gemini"    : Google Gemini (gemini-2.0-flash, gemini-1.5-pro...)

Usage:
    from ai.providers import get_provider
    provider = get_provider(settings)
"""
from typing import TYPE_CHECKING

from ai.providers.base import LLMProvider, ProviderResult, ToolCall

if TYPE_CHECKING:
    from core.config import Settings


def get_provider(settings: "Settings") -> LLMProvider:
    """
    Factory: crée et retourne le provider configuré dans les settings.

    Sélection par settings.provider:
      - "anthropic" → AnthropicProvider
      - "openai"    → OpenAIProvider (OpenAI officiel)
      - "ollama"    → OpenAIProvider (endpoint Ollama compatible OpenAI)
      - "gemini"    → GeminiProvider
    """
    provider_name = (settings.provider or "anthropic").lower()

    if provider_name == "anthropic":
        from ai.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
        )

    elif provider_name == "openai":
        from ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.openai_api_key or "",
            model=settings.openai_model or "gpt-4o",
            base_url=settings.openai_base_url or None,
        )

    elif provider_name == "ollama":
        from ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key="ollama",  # Ollama n'exige pas de vrai token
            model=settings.ollama_model or "llama3.1",
            base_url=settings.ollama_base_url or "http://localhost:11434/v1",
        )

    elif provider_name == "gemini":
        from ai.providers.gemini_provider import GeminiProvider
        return GeminiProvider(
            api_key=settings.gemini_api_key or "",
            model=settings.gemini_model or "gemini-2.0-flash",
        )

    else:
        raise ValueError(
            f"Provider inconnu: '{provider_name}'. "
            f"Valeurs valides: anthropic, openai, ollama, gemini"
        )


__all__ = [
    "get_provider",
    "LLMProvider",
    "ProviderResult",
    "ToolCall",
]
