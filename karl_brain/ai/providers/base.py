"""
Interface abstraite pour tous les providers LLM.
Chaque provider traduit son format natif vers/depuis le format interne normalisé.

Format normalisé des messages:
  user    : {"role": "user",      "content": str | list[dict]}
  assistant: {"role": "assistant", "content": str | list[dict]}

Format normalisé d'un tool_call:
  {"id": str, "name": str, "input": dict}

Format normalisé d'un tool_result (à ajouter dans messages):
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": str, "content": str, "is_error": bool}]}
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, List, Dict, Optional


@dataclass
class ToolCall:
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class ProviderResult:
    text: str
    tool_calls: List[ToolCall]
    stop_reason: str  # "end_turn" | "tool_use" | "stop" | "max_tokens"
    thinking: Optional[str] = None


class LLMProvider(ABC):
    """
    Interface commune pour tous les providers LLM.
    Implémentation minimale: `run_turn()` + `add_tool_results()`.
    """

    @abstractmethod
    async def run_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: str,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_thinking: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> ProviderResult:
        """
        Exécute un tour de conversation.
        - messages: historique normalisé
        - tools: outils au format Anthropic (chaque provider adapte)
        - system: prompt système
        - Retourne ProviderResult (text + tool_calls + stop_reason)
        """

    @abstractmethod
    def add_assistant_turn(
        self,
        messages: List[Dict[str, Any]],
        result: ProviderResult,
    ) -> List[Dict[str, Any]]:
        """
        Ajoute la réponse assistant à l'historique (format propre au provider).
        """

    @abstractmethod
    def add_tool_results(
        self,
        messages: List[Dict[str, Any]],
        tool_calls: List[ToolCall],
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Ajoute les résultats d'outils à l'historique (format propre au provider).
        results[i] = {"content": str, "is_error": bool}
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifiant du provider (ex: 'anthropic', 'openai', 'gemini', 'ollama')"""

    @property
    @abstractmethod
    def model(self) -> str:
        """Modèle actif."""

    def serialize_for_db(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prépare les messages pour le stockage DB (override si nécessaire)."""
        serialized = []
        for msg in messages:
            content = msg["content"]
            if isinstance(content, list):
                blocks = []
                for b in content:
                    if hasattr(b, "model_dump"):
                        blocks.append(b.model_dump())
                    else:
                        blocks.append(b)
                serialized.append({"role": msg["role"], "content": blocks})
            else:
                serialized.append({"role": msg["role"], "content": str(content)})
        return serialized
