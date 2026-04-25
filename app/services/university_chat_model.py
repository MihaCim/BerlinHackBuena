from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from typing import Any, Literal

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult


class UniversityChatModel(BaseChatModel):
    api_key: str
    api_base: str = "https://ki-toolbox.tu-braunschweig.de"
    endpoint: str = "/api/v1/chat/send"
    model_name: str = "gpt-5.4-mini"
    custom_instructions: str = ""
    hide_custom_instructions: bool = True
    timeout: int = 120
    disable_streaming: bool | Literal["tool_calling"] = "tool_calling"

    @property
    def _llm_type(self) -> str:
        return "tub-chatbot"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "api_base": self.api_base,
            "endpoint": self.endpoint,
            "model_name": self.model_name,
        }

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
        del stop, run_manager
        tools = list(kwargs.get("tools") or [])
        prompt = self._build_prompt(messages, tools, kwargs.get("tool_choice"))
        with httpx.Client(timeout=self.timeout) as client, client.stream(
            "POST",
            f"{self.api_base}{self.endpoint}",
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "thread": None,
                "prompt": prompt,
                "model": self.model_name,
                "customInstructions": self.custom_instructions,
                "hideCustomInstructions": self.hide_custom_instructions,
            },
        ) as response:
            response.raise_for_status()
            message = self._read_streaming_message(response, tools)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _read_streaming_message(self, response: httpx.Response, tools: Sequence[Any]) -> AIMessage:
        text = ""
        thread_id = None
        usage_metadata = None

        for line in response.iter_lines():
            if not line:
                continue
            event = json.loads(line)
            event_type = event.get("type")
            if event_type == "start":
                thread_id = event.get("conversationThread")
            elif event_type == "chunk":
                text += event.get("content", "")
            elif event_type == "done":
                text = event.get("response", text)
                thread_id = event.get("conversationThread", thread_id)
                usage_metadata = {
                    "input_tokens": event.get("promptTokens"),
                    "output_tokens": event.get("responseTokens"),
                    "total_tokens": event.get("totalTokens"),
                }

        return self._to_ai_message(text, tools, thread_id, usage_metadata)

    def _build_prompt(
        self,
        messages: Sequence[BaseMessage],
        tools: Sequence[Any],
        tool_choice: str | None,
    ) -> str:
        parts = ["You are a helpful assistant."]
        if tools:
            parts.extend(
                [
                    "Tools are available.",
                    "Respond with valid JSON only.",
                    "If you need a tool, return exactly this shape:",
                    '{"type":"tool_call","name":"<tool_name>","arguments":{}}',
                    "If you can answer the user, return exactly this shape:",
                    '{"type":"final","content":"<answer>"}',
                    f"Tool choice mode: {tool_choice or 'auto'}",
                    "Available tools:",
                    self._render_tools(tools),
                ]
            )
        parts.append("Conversation:")
        parts.extend(self._render_message(message) for message in messages)
        return "\n\n".join(parts)

    def _render_tools(self, tools: Sequence[Any]) -> str:
        rendered = []
        for tool in tools:
            rendered.append(
                json.dumps(
                    {
                        "name": getattr(tool, "name", "unknown_tool"),
                        "description": getattr(tool, "description", ""),
                        "arguments": getattr(tool, "args", {}),
                    },
                    ensure_ascii=True,
                )
            )
        return "\n".join(rendered)

    def _render_message(self, message: BaseMessage) -> str:
        if isinstance(message, SystemMessage):
            return f"system: {message.content}"
        if isinstance(message, HumanMessage):
            return f"user: {message.content}"
        if isinstance(message, ToolMessage):
            return f"tool[{message.name}][{message.tool_call_id}]: {message.content}"
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            return f"assistant_tool_call: {json.dumps(tool_calls, ensure_ascii=True)}"
        return f"assistant: {message.content}"

    def _to_ai_message(
        self,
        text: str,
        tools: Sequence[Any],
        thread_id: str | None,
        usage_metadata: dict[str, Any] | None,
    ) -> AIMessage:
        parsed = self._parse_json_object(text)
        tool_names = {getattr(tool, "name", None) for tool in tools}
        if isinstance(parsed, dict) and parsed.get("type") == "tool_call":
            tool_name = parsed.get("name")
            arguments = parsed.get("arguments", {})
            if tool_name in tool_names and isinstance(arguments, dict):
                return AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": tool_name,
                            "args": arguments,
                            "id": f"call_{uuid.uuid4().hex}",
                            "type": "tool_call",
                        }
                    ],
                    additional_kwargs={"thread": thread_id} if thread_id else {},
                    usage_metadata=usage_metadata,
                )
        if isinstance(parsed, dict) and parsed.get("type") == "final":
            text = str(parsed.get("content", ""))
        return AIMessage(
            content=text,
            additional_kwargs={"thread": thread_id} if thread_id else {},
            usage_metadata=usage_metadata,
        )

    def _parse_json_object(self, text: str) -> dict[str, Any] | None:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```")
            if cleaned.startswith("json"):
                cleaned = cleaned.removeprefix("json")
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
