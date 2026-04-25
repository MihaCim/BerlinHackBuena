from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Literal

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class OpenRouterChatModel(BaseChatModel):
    api_key: str
    model_name: str = "xiaomi/mimo-v2-flash"
    api_base: str = "https://openrouter.ai/api/v1"
    timeout: int = 120
    disable_streaming: bool | Literal["tool_calling"] = "tool_calling"

    @property
    def _llm_type(self) -> str:
        return "openrouter"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"api_base": self.api_base, "model_name": self.model_name}

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Any:
        return self.bind(tools=list(tools), tool_choice=tool_choice, **kwargs)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        del run_manager
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [message_to_openrouter(message) for message in messages],
        }
        if stop:
            payload["stop"] = stop

        tools = list(kwargs.get("tools") or [])
        if tools:
            payload["tools"] = [tool_to_openrouter(tool) for tool in tools]
            if kwargs.get("tool_choice"):
                payload["tool_choice"] = kwargs["tool_choice"]

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        ai_message = openrouter_message_to_ai_message(message, data.get("usage"))
        return ChatResult(generations=[ChatGeneration(message=ai_message)])


def message_to_openrouter(message: BaseMessage) -> dict[str, Any]:
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": str(message.content)}
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    if isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "content": str(message.content),
            "tool_call_id": message.tool_call_id,
        }

    tool_calls = getattr(message, "tool_calls", None) or []
    payload: dict[str, Any] = {"role": "assistant", "content": str(message.content or "")}
    if tool_calls:
        payload["tool_calls"] = [langchain_tool_call_to_openrouter(call) for call in tool_calls]
    return payload


def langchain_tool_call_to_openrouter(call: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": call.get("id"),
        "type": "function",
        "function": {
            "name": call.get("name"),
            "arguments": json.dumps(call.get("args", {}), ensure_ascii=False),
        },
    }


def tool_to_openrouter(tool: Any) -> dict[str, Any]:
    if isinstance(tool, dict) and tool.get("type") == "function":
        return tool

    name = getattr(tool, "name", "unknown_tool")
    description = getattr(tool, "description", "")
    parameters = getattr(tool, "args", None) or {"type": "object", "properties": {}}
    if "type" not in parameters:
        parameters = {"type": "object", "properties": parameters}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def openrouter_message_to_ai_message(
    message: dict[str, Any], usage: dict[str, Any] | None
) -> AIMessage:
    tool_calls = []
    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function", {})
        tool_calls.append(
            {
                "name": function.get("name", ""),
                "args": parse_arguments(function.get("arguments", "{}")),
                "id": tool_call.get("id"),
                "type": "tool_call",
            }
        )

    usage_metadata = None
    if usage:
        usage_metadata = {
            "input_tokens": usage.get("prompt_tokens"),
            "output_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    return AIMessage(
        content=message.get("content") or "",
        tool_calls=tool_calls,
        usage_metadata=usage_metadata,
    )


def parse_arguments(arguments: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    try:
        parsed = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
