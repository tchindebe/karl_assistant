"""
Provider Anthropic (Claude).
Supporte: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5.
Thinking adaptatif activé sur Opus et Sonnet 4.6.
"""
import json
import anthropic
from typing import List, Dict, Any, Optional, Callable, Awaitable

from ai.providers.base import LLMProvider, ProviderResult, ToolCall

# Modèles supportant adaptive thinking
_THINKING_MODELS = {"claude-opus-4-6", "claude-sonnet-4-6"}


class AnthropicProvider(LLMProvider):

    def __init__(self, api_key: str, model: str = "claude-opus-4-6"):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model(self) -> str:
        return self._model

    async def run_turn(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system: str,
        on_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_thinking: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> ProviderResult:
        # Adaptive thinking uniquement sur les modèles qui le supportent
        use_thinking = self._model in _THINKING_MODELS
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "max_tokens": 8192,
            "system": system,
            "tools": tools,  # Format Anthropic natif
            "messages": messages,
        }
        if use_thinking:
            kwargs["thinking"] = {"type": "adaptive"}

        accumulated_text = ""
        accumulated_thinking = ""
        tool_calls: List[ToolCall] = []
        current_tool_input_json = ""
        current_tool_name = ""
        current_tool_id = ""
        in_tool_input = False

        async with self._client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    block = event.content_block
                    if block.type == "tool_use":
                        current_tool_name = block.name
                        current_tool_id = block.id
                        current_tool_input_json = ""
                        in_tool_input = True

                elif event.type == "content_block_delta":
                    delta = event.delta
                    if delta.type == "text_delta":
                        accumulated_text += delta.text
                        if on_text:
                            await on_text(delta.text)
                    elif delta.type == "thinking_delta":
                        accumulated_thinking += delta.thinking
                        if on_thinking:
                            await on_thinking(delta.thinking)
                    elif delta.type == "input_json_delta":
                        current_tool_input_json += delta.partial_json

                elif event.type == "content_block_stop":
                    if in_tool_input and current_tool_name:
                        try:
                            tool_input = json.loads(current_tool_input_json) if current_tool_input_json else {}
                        except json.JSONDecodeError:
                            tool_input = {}
                        tool_calls.append(ToolCall(
                            id=current_tool_id,
                            name=current_tool_name,
                            input=tool_input,
                        ))
                        in_tool_input = False
                        current_tool_name = ""

            final_message = await stream.get_final_message()

        # Stocker le contenu brut pour pouvoir le ré-injecter dans l'historique
        self._last_raw_content = final_message.content

        return ProviderResult(
            text=accumulated_text,
            tool_calls=tool_calls,
            stop_reason=final_message.stop_reason or "end_turn",
            thinking=accumulated_thinking or None,
        )

    def add_assistant_turn(
        self,
        messages: List[Dict[str, Any]],
        result: ProviderResult,
    ) -> List[Dict[str, Any]]:
        # Anthropic exige le contenu brut (blocs) pour les tool_use
        return messages + [{"role": "assistant", "content": self._last_raw_content}]

    def add_tool_results(
        self,
        messages: List[Dict[str, Any]],
        tool_calls: List[ToolCall],
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
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
