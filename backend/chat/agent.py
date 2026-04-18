"""
Anthropic Messages API with tool_use loop (agentic behavior).
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

from .tools import ANTHROPIC_TOOL_DEFS, run_tool

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOOL_ROUNDS = 6


def anthropic_agent_turn(
    system: str,
    messages: list[dict[str, Any]],
    *,
    session_id: str,
) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    use_tools = os.environ.get("AGENT_TOOLS", "1") == "1"

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    working = [dict(m) for m in messages]
    rounds = 0

    while rounds < MAX_TOOL_ROUNDS:
        rounds += 1
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 2048,
            "system": system,
            "messages": working,
        }
        if use_tools:
            payload["tools"] = ANTHROPIC_TOOL_DEFS

        r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=180)
        try:
            data = r.json()
        except ValueError:
            data = {}
        if not r.ok:
            msg = (data.get("error") or {}).get("message") or r.reason or "Anthropic API error"
            raise RuntimeError(msg)

        stop = data.get("stop_reason")
        content = data.get("content") or []

        if stop == "end_turn" or stop is None:
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text") or "")
            return "".join(parts).strip() or "I'm here with you."

        if stop == "tool_use":
            working.append({"role": "assistant", "content": content})
            tool_results: list[dict[str, Any]] = []
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tid = block.get("id")
                name = block.get("name")
                inp = block.get("input") or {}
                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except json.JSONDecodeError:
                        inp = {}
                result_text = run_tool(name, inp if isinstance(inp, dict) else {}, session_id=session_id)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tid,
                        "content": result_text,
                    }
                )
            if not tool_results:
                return "Tool loop failed (no tool_use blocks parsed)."
            working.append({"role": "user", "content": tool_results})
            continue

        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
        return "".join(parts).strip() or "I'm here with you."

    return "I need to pause — too many tool steps. Try asking one thing at a time."
