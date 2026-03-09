"""
Provider OpenAI — supporte aussi Ollama (OpenAI-compatible).
Modèles: gpt-4o, gpt-4o-mini, o1, o3-mini, o3...
Ollama: llama3.1, mistral, qwen2.5, deepseek-r1, etc.
"""
import json
from typing import List, Dict, Any, Optional, Callable, Awaitable

try:
    import openai
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

from ai.providers.base import LLMProvider, ProviderResult, ToolCall


def _anthropic_tools_to_openai(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convertit le format Anthropic → format OpenAI."""
    converted = []
    for t in tools:
        converted.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
            },
        })
    return converted


def _normalize_messages_for_openai(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalise l'historique (qui peut contenir des tool_result blocks Anthropic)
    vers le format OpenAI.
    """
    normalized = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if isinstance(content, str):
            normalized.append({"role": role, "content": content})

        elif isinstance(content, list):
            # Vérifier si c'est un message tool_result (format Anthropic)
            if any(
                (isinstance(b, dict) and b.get("type") == "tool_result")
                for b in content
            ):
                # → Convertir en messages "tool" OpenAI
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        normalized.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block.get("content", ""),
                        })
            else:
                # Message assistant avec tool_calls
                text_parts = []
                openai_tool_calls = []
                for block in content:
                    b = block if isinstance(block, dict) else (block.model_dump() if hasattr(block, "model_dump") else {})
                    if b.get("type") == "text":
                        text_parts.append(b.get("text", ""))
                    elif b.get("type") == "tool_use":
                        openai_tool_calls.append({
                            "id": b["id"],
                            "type": "function",
                            "function": {
                                "name": b["name"],
                                "arguments": json.dumps(b.get("input", {})),
                            },
                        })
                    elif b.get("type") == "thinking":
                        pass  # Ignorer les blocs thinking

                assistant_msg: Dict[str, Any] = {"role": "assistant"}
                if text_parts:
                    assistant_msg["content"] = " ".join(text_parts)
                if openai_tool_calls:
                    assistant_msg["tool_calls"] = openai_tool_calls
                if "content" not in assistant_msg:
                    assistant_msg["content"] = None
                normalized.append(assistant_msg)
        else:
            normalized.append({"role": role, "content": str(content)})

    return normalized


class OpenAIProvider(LLMProvider):
    """
    Provider pour OpenAI et tout endpoint compatible (Ollama, LM Studio, etc.).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        base_url: Optional[str] = None,
    ):
        if not _OPENAI_AVAILABLE:
            raise ImportError(
                "openai package non installé. Exécuter: pip install openai"
            )
        self._model = model
        self._client = openai.AsyncOpenAI(
            api_key=api_key or "ollama",  # Ollama n'exige pas de vrai token
            base_url=base_url,
            timeout=600.0,  # 10 min max (Ollama: chargement modèle peut être très lent)
        )
        self._last_response_tool_calls: List[Any] = []
        self._last_response_content: Optional[str] = None

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    async def run_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: str,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_thinking: Optional[Callable[[str], Awaitable[None]]] = None,  # noqa: unused — OpenAI/Ollama n'a pas de thinking blocks
    ) -> ProviderResult:
        openai_messages = [{"role": "system", "content": system}]
        openai_messages += _normalize_messages_for_openai(messages)
        openai_tools = _anthropic_tools_to_openai(tools)

        # Streaming
        accumulated_text = ""
        tool_call_buffers: Dict[int, Dict] = {}

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=openai_messages,
            tools=openai_tools if openai_tools else openai.NOT_GIVEN,
            stream=True,
        )

        finish_reason = "stop"
        async for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta

            # Texte
            if delta.content:
                accumulated_text += delta.content
                if on_text:
                    await on_text(delta.content)

            # Tool calls (streamed)
            if delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }
                    buf = tool_call_buffers[idx]
                    if tc_delta.id:
                        buf["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            buf["name"] += tc_delta.function.name
                        if tc_delta.function.arguments:
                            buf["arguments"] += tc_delta.function.arguments

        # Construire les ToolCall normalisés
        tool_calls: List[ToolCall] = []
        for buf in tool_call_buffers.values():
            try:
                input_data = json.loads(buf["arguments"]) if buf["arguments"] else {}
            except json.JSONDecodeError:
                input_data = {}
            tool_calls.append(ToolCall(id=buf["id"], name=buf["name"], input=input_data))

        self._last_response_content = accumulated_text
        self._last_response_tool_calls = list(tool_call_buffers.values())

        # Normaliser stop_reason
        stop_reason = "tool_use" if tool_calls else "end_turn"
        if finish_reason in ("length",):
            stop_reason = "max_tokens"

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
        """
        Ajoute la réponse assistant avec les tool_calls OpenAI.
        On stocke en format "mixte" qui sera normalisé par _normalize_messages_for_openai.
        """
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
        # Stocker au format Anthropic tool_result (la normalisation fera le reste)
        tool_result_blocks = [
            {
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": r["content"],
                "is_error": r["is_error"],
            }
            for tc, r in zip(tool_calls, results)
        ]
        return messages + [{"role": "user", "content": tool_result_blocks}]
