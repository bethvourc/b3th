"""
Groq LLM wrapper.

This module hides the HTTP details so the rest of the codebase can call
`chat_completion()` and stay decoupled from any specific provider.
"""

from __future__ import annotations

import os
from typing import List, Dict, Any

import requests


class LLMError(RuntimeError):
    """Raised when the Groq API returns an error or cannot be reached."""



# Internal helpers
def _api_key() -> str:
    """Fetch the Groq API key from the environment."""
    key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_TOKEN")
    if not key:
        raise LLMError(
            "Environment variable GROQ_API_KEY (or GROQ_API_TOKEN) is not set."
        )
    return key


def _api_base() -> str:
    """Return the API base URL (override with GROQ_API_BASE if desired)."""
    return os.getenv("GROQ_API_BASE", "https://api.groq.com").rstrip("/")


def _default_model() -> str:
    """
    Return the default model for chat completions.

    You can override it with GROQ_MODEL_ID.
    """
    return os.getenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")


# Public function
def chat_completion(
    messages: List[Dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
    stream: bool = False,
) -> str:
    """
    Submit a chat-completion request to Groq and return the assistant's content.

    Parameters
    ----------
    messages
        A list of message dicts (role/content) compatible with the OpenAI schema.
    model
        Groq model ID. If None, `_default_model()` is used.
    temperature
        Sampling temperature.
    max_tokens
        Maximum tokens for the reply.
    stream
        Whether to request a streaming response (not surfaced by this wrapper).

    Returns
    -------
    The assistant's response content as a string.
    """
    url = f"{_api_base()}/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model or _default_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise LLMError(f"Groq API error {resp.status_code}: {resp.text}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LLMError("Invalid response structure from Groq API") from exc
