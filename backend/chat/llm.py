"""
LLM backends for /api/chat/. Use Ollama for local open-weights models, or Anthropic API.
"""
from __future__ import annotations

import os
from typing import Any

import requests

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


def complete_anthropic(system: str, messages: list[dict[str, Any]], timeout: int = 120) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to backend/.env or set LLM_PROVIDER=ollama."
        )
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
    r = requests.post(
        ANTHROPIC_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={
            "model": model,
            "max_tokens": 1000,
            "system": system,
            "messages": messages,
        },
        timeout=timeout,
    )
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not r.ok:
        msg = (data.get("error") or {}).get("message") or r.reason or "Anthropic API error"
        raise RuntimeError(msg)
    parts = []
    for block in data.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text") or "")
    return "".join(parts)


def complete_ollama(system: str, messages: list[dict[str, Any]], timeout: int = 300) -> str:
    base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    ollama_messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            ollama_messages.append({"role": role, "content": content})
    url = f"{base}/api/chat"
    r = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "model": model,
            "messages": ollama_messages,
            "stream": False,
        },
        timeout=timeout,
    )
    try:
        data = r.json()
    except ValueError:
        data = {}
    if not r.ok:
        err = data.get("error") if isinstance(data.get("error"), str) else str(data.get("error"))
        msg = err or r.reason or "Ollama error"
        raise RuntimeError(msg)
    msg = data.get("message") or {}
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        return content
    return ""


def complete(system: str, messages: list[dict[str, Any]]) -> str:
    provider = (os.environ.get("LLM_PROVIDER") or "anthropic").strip().lower()
    if provider == "ollama":
        return complete_ollama(system, messages)
    if provider == "anthropic":
        return complete_anthropic(system, messages)
    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. Use 'anthropic' or 'ollama'."
    )
