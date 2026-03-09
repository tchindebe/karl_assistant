"""
Provider Google Gemini — via google-generativeai SDK.
Modèles: gemini-2.0-flash, gemini-1.5-pro, gemini-1.5-flash, etc.
"""
import json
from typing import List, Dict, Any, Optional, Callable, Awaitable

try:
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig, FunctionDeclaration, Tool as GeminiTool
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

from ai.providers.base import LLMProvider, ProviderResult, ToolCall


def _strip_unsupported_schema_fields(schema: Any) -> Any:
    """Supprime récursivement les champs non supportés par Gemini (additionalProperties, etc.)."""
    if not isinstance(schema, dict):
        return schema
    unsupported = {"additionalProperties", "exclusiveMinimum", "exclusiveMaximum", "$schema"}
    cleaned = {k: v for k, v in schema.items() if k not in unsupported}
    if "properties" in cleaned and isinstance(cleaned["properties"], dict):
        cleaned["properties"] = {
            k: _strip_unsupported_schema_fields(v)
            for k, v in cleaned["properties"].items()
        }
    if "items" in cleaned:
        cleaned["items"] = _strip_unsupported_schema_fields(cleaned["items"])
    return cleaned


def _anthropic_tools_to_gemini(tools: List[Dict[str, Any]]) -> List[Any]:
    """Convertit le format Anthropic → format Gemini FunctionDeclaration."""
    if not _GEMINI_AVAILABLE:
        return []
    declarations = []
    for t in tools:
        schema = t.get("input_schema", {"type": "object", "properties": {}})
        schema = _strip_unsupported_schema_fields(schema)
        declarations.append(
            FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters=schema,
            )
        )
    return declarations


def _normalize_messages_for_gemini(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convertit l'historique normalisé vers le format Gemini (Contents).
    Gemini utilise: role="user"|"model" et parts=[{"text":...}|{"function_call":...}|{"function_response":...}]
    """
    gemini_messages = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        gemini_role = "model" if role == "assistant" else "user"

        if isinstance(content, str):
            gemini_messages.append({"role": gemini_role, "parts": [{"text": content}]})

        elif isinstance(content, list):
            # Vérifier si c'est un message tool_result (format Anthropic)
            if any(
                isinstance(b, dict) and b.get("type") == "tool_result"
                for b in content
            ):
                # → Convertir en messages function_response Gemini
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            # Extraire le texte des blocs
                            result_content = " ".join(
                                b.get("text", "") for b in result_content
                                if isinstance(b, dict) and b.get("type") == "text"
                            )
                        parts.append({
                            "function_response": {
                                "name": block.get("tool_name", "unknown"),  # nom stocké
                                "response": {
                                    "content": result_content,
                                    "is_error": block.get("is_error", False),
                                },
                            }
                        })
                if parts:
                    gemini_messages.append({"role": "user", "parts": parts})
            else:
                # Message assistant avec tool_calls et/ou texte
                parts = []
                for block in content:
                    b = block if isinstance(block, dict) else (
                        block.model_dump() if hasattr(block, "model_dump") else {}
                    )
                    if b.get("type") == "text" and b.get("text"):
                        parts.append({"text": b["text"]})
                    elif b.get("type") == "tool_use":
                        parts.append({
                            "function_call": {
                                "name": b["name"],
                                "args": b.get("input", {}),
                            }
                        })
                    elif b.get("type") == "thinking":
                        pass  # Ignorer
                if parts:
                    gemini_messages.append({"role": "model", "parts": parts})
        else:
            gemini_messages.append({"role": gemini_role, "parts": [{"text": str(content)}]})

    return gemini_messages


class GeminiProvider(LLMProvider):
    """
    Provider pour Google Gemini via le SDK google-generativeai.
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not _GEMINI_AVAILABLE:
            raise ImportError(
                "google-generativeai non installé. Exécuter: pip install google-generativeai"
            )
        genai.configure(api_key=api_key)
        self._model_name = model
        self._last_tool_calls: List[Dict] = []

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model_name

    async def run_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: str,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_thinking: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> ProviderResult:
        import asyncio

        gemini_messages = _normalize_messages_for_gemini(messages)
        gemini_tools = _anthropic_tools_to_gemini(tools) if tools else None

        # Construire le modèle avec instructions système
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
            tools=[GeminiTool(function_declarations=gemini_tools)] if gemini_tools else None,
        )

        # Lancer en executor pour ne pas bloquer l'event loop
        def _call_gemini():
            chat = model.start_chat(history=gemini_messages[:-1] if gemini_messages else [])
            last_msg = gemini_messages[-1] if gemini_messages else {"parts": [{"text": ""}]}
            # Extraire le texte du dernier message
            last_text = ""
            for part in last_msg.get("parts", []):
                if "text" in part:
                    last_text += part["text"]

            response = chat.send_message(
                last_text,
                generation_config=GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=8192,
                ),
                stream=False,
            )
            return response

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, _call_gemini)

        # Parser la réponse
        accumulated_text = ""
        tool_calls: List[ToolCall] = []

        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    accumulated_text += part.text
                    if on_text:
                        await on_text(part.text)
                elif hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    # Générer un ID unique
                    import uuid
                    tc_id = f"gemini_{uuid.uuid4().hex[:8]}"
                    # Convertir MapComposite → dict
                    args = dict(fc.args) if fc.args else {}
                    tool_calls.append(ToolCall(
                        id=tc_id,
                        name=fc.name,
                        input=args,
                    ))

        self._last_tool_calls = [
            {"id": tc.id, "name": tc.name, "args": tc.input}
            for tc in tool_calls
        ]

        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ProviderResult(
            text=accumulated_text,
            tool_calls=tool_calls,
            stop_reason=stop_reason,
        )

    def add_assistant_turn(
        self,
        messages: List[Dict[str, Any]],
        result: ProviderResult,
    ) -> List[Dict[str, Any]]:
        """Ajoute la réponse assistant au format interne normalisé."""
        assistant_content: List[Dict] = []
        if result.text:
            assistant_content.append({"type": "text", "text": result.text})
        for tc in result.tool_calls:
            assistant_content.append({
                "type": "tool_use",
                "id": tc.id,
                "name": tc.name,
                "input": tc.input,
            })
        return messages + [{"role": "assistant", "content": assistant_content}]

    def add_tool_results(
        self,
        messages: List[Dict[str, Any]],
        tool_calls: List[ToolCall],
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Ajoute les tool_results au format interne.
        Gemini a besoin du nom de l'outil dans function_response,
        on le stocke dans le bloc tool_result pour _normalize_messages_for_gemini.
        """
        tool_result_blocks = [
            {
                "type": "tool_result",
                "tool_use_id": tc.id,
                "tool_name": tc.name,  # Extra: nécessaire pour Gemini function_response
                "content": r["content"],
                "is_error": r["is_error"],
            }
            for tc, r in zip(tool_calls, results)
        ]
        return messages + [{"role": "user", "content": tool_result_blocks}]
