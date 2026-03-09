"""
Boucle agentic multi-provider (tool use loop) avec streaming WebSocket.
Supporte: Anthropic Claude, OpenAI, Ollama, Google Gemini.
Le provider actif est déterminé par la variable d'env PROVIDER (défaut: anthropic).
"""
import json
from typing import List, Dict, Any, Optional, Callable, Awaitable

from core.config import get_settings
from ai.system_prompt import SYSTEM_PROMPT
from ai.tool_definitions import TOOLS
from ai.providers import get_provider
from ai.providers.base import LLMProvider, ToolCall

settings = get_settings()

# Provider singleton — chargé au démarrage selon PROVIDER dans .env
_provider: Optional[LLMProvider] = None


def _get_provider() -> LLMProvider:
    """Retourne le provider LLM actif (singleton)."""
    global _provider
    if _provider is None:
        _provider = get_provider(settings)
    return _provider


async def run_conversation(
    messages: List[Dict[str, Any]],
    on_text: Optional[Callable[[str], Awaitable[None]]] = None,
    on_tool_start: Optional[Callable[[str, Dict], Awaitable[None]]] = None,
    on_tool_end: Optional[Callable[[str, Any], Awaitable[None]]] = None,
    on_thinking: Optional[Callable[[str], Awaitable[None]]] = None,
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Boucle agentic principale — agnostique au provider LLM.

    Args:
        messages: Historique de conversation (format normalisé interne)
        on_text: Callback pour chaque token de texte (streaming)
        on_tool_start: Callback quand un outil est appelé (avant exécution)
        on_tool_end: Callback quand l'outil a répondu (après exécution)
        on_thinking: Callback pour les blocs de réflexion (Claude only)

    Returns:
        (final_text, updated_messages)
    """
    from ai.tool_executor import execute_tool

    provider = _get_provider()
    final_text = ""
    current_messages = list(messages)
    max_iterations = 10  # Évite les boucles infinies (surtout avec Ollama)
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        # ── Appel LLM (streaming si supporté) ─────────────────────────────────
        result = await provider.run_turn(
            messages=current_messages,
            tools=TOOLS,
            system=SYSTEM_PROMPT,
            on_text=on_text,
            on_thinking=on_thinking,
        )

        if result.text:
            final_text = result.text

        # ── Ajouter la réponse de l'assistant à l'historique ──────────────────
        current_messages = provider.add_assistant_turn(current_messages, result)

        # ── Si pas d'appels d'outils → fin de la boucle ───────────────────────
        if result.stop_reason == "end_turn" or not result.tool_calls:
            break

        # ── Notifier le début des appels d'outils ─────────────────────────────
        if on_tool_start:
            for tc in result.tool_calls:
                await on_tool_start(tc.name, tc.input)

        # ── Exécuter les outils en parallèle si possible ──────────────────────
        tool_results: List[Dict[str, Any]] = []
        executed_tool_calls: List[ToolCall] = []

        for tc in result.tool_calls:
            try:
                tool_result = await execute_tool(tc.name, tc.input)
                result_content = json.dumps(tool_result, ensure_ascii=False, default=str)
                is_error = False
            except Exception as e:
                result_content = f"Erreur lors de l'exécution de {tc.name}: {str(e)}"
                is_error = True

            if on_tool_end:
                await on_tool_end(
                    tc.name,
                    tool_result if not is_error else result_content
                )

            tool_results.append({"content": result_content, "is_error": is_error})
            executed_tool_calls.append(tc)

        # ── Ajouter les résultats à l'historique ──────────────────────────────
        current_messages = provider.add_tool_results(
            current_messages,
            executed_tool_calls,
            tool_results,
        )

    if iteration >= max_iterations and not final_text:
        final_text = "⚠️ Limite d'itérations atteinte — le modèle n'a pas convergé."

    return final_text, current_messages


def serialize_messages_for_db(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Prépare les messages pour le stockage en DB via le provider actif."""
    provider = _get_provider()
    return provider.serialize_for_db(messages)


def deserialize_messages_from_db(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Recharge les messages depuis la DB (format normalisé interne)."""
    return messages
