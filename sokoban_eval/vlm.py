from __future__ import annotations

import json
import urllib.request
from base64 import b64encode
from dataclasses import dataclass
from typing import Any

from sokoban_eval.prompts import SYSTEM_PROMPT, USER_PROMPT

ACTION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "sokoban_action",
        "description": "Choose the next Sokoban action.",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": ["action"],
            "properties": {
                "action": {"type": "string", "enum": ["move", "reset"]},
                "direction": {
                    "type": "string",
                    "enum": ["left", "right", "up", "down"],
                },
            },
        },
    },
}


@dataclass(frozen=True)
class Action:
    action: str
    direction: str | None = None

    @classmethod
    def from_arguments(cls, arguments: str) -> "Action":
        try:
            value = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("Tool arguments are not valid JSON") from exc
        if not isinstance(value, dict) or set(value) - {"action", "direction"}:
            raise ValueError("Tool arguments must contain only action and direction")
        action = value.get("action")
        direction = value.get("direction")
        if action == "move" and direction in {"left", "right", "up", "down"}:
            return cls(action, direction)
        if action == "reset" and direction is None:
            return cls(action)
        raise ValueError("move requires a valid direction; reset accepts no direction")

    def label(self) -> str:
        return "reset" if self.action == "reset" else f"move({self.direction})"


@dataclass(frozen=True)
class Completion:
    action: Action
    assistant_message: dict[str, Any]
    tool_call_id: str


class OAIChatClient:
    """DSRF-style OpenAI chat-completions client for one forced action tool."""

    def __init__(self, base_url: str, *, timeout: float = 120.0, model: str = "") -> None:
        self.endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"
        self.timeout = timeout
        self.model = model
        self._history: list[Completion] = []

    def complete(self, board_png: bytes, last_action: str | None) -> Completion:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for completion in self._history:
            messages.extend((completion.assistant_message, {
                "role": "tool",
                "tool_call_id": completion.tool_call_id,
                "content": "Action completed.",
            }))
        previous = last_action or "none (initial board)"
        text = f"Completed action: {previous}\n\n{USER_PROMPT}"
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": _png_data_url(board_png)}},
            ],
        })
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "tools": [ACTION_TOOL],
            "tool_choice": {"type": "function", "function": {"name": "sokoban_action"}},
            "parallel_tool_calls": False,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            document = json.loads(response.read().decode())
        return _completion_from_response(document)

    def commit(self, completion: Completion) -> None:
        self._history.append(completion)


def _png_data_url(png: bytes) -> str:
    return "data:image/png;base64," + b64encode(png).decode("ascii")


def _completion_from_response(document: object) -> Completion:
    try:
        message = document["choices"][0]["message"]  # type: ignore[index]
        calls = message["tool_calls"]
        call = calls[0]
        function = call["function"]
        tool_id = call["id"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("VLM returned no valid sokoban_action tool call") from exc
    if (
        not isinstance(calls, list)
        or len(calls) != 1
        or not isinstance(call, dict)
        or not isinstance(function, dict)
        or function.get("name") != "sokoban_action"
        or not isinstance(function.get("arguments"), str)
        or not isinstance(tool_id, str)
    ):
        raise RuntimeError("VLM returned an invalid sokoban_action tool call")
    assistant_message: dict[str, Any] = {"role": "assistant", "tool_calls": calls}
    if isinstance(message.get("content"), str):
        assistant_message["content"] = message["content"]
    return Completion(Action.from_arguments(function["arguments"]), assistant_message, tool_id)
