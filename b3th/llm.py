"""
Groq LLM wrapper.

Call ``chat_completion()`` with either a prompt *string* or a full list of
OpenAI-style message dicts; the helper will do the right thing.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Union, Optional

import requests


class LLMError(RuntimeError):
    """Raised when the Groq API returns an error or an unexpected payload."""



# Internal helpers
def _api_key() -> str:
    key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_TOKEN")
    if not key:
        raise LLMError(
            "Environment variable GROQ_API_KEY (or GROQ_API_TOKEN) is not set."
        )
    return key


def _api_base() -> str:
    return os.getenv("GROQ_API_BASE", "https://api.groq.com").rstrip("/")


def _default_model() -> str:
    return os.getenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")



# Public function
def chat_completion(
    messages: Union[str, List[Dict[str, str]]],
    *,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
    stream: bool = False,
) -> str:
    """
    Submit a chat-completion request to Groq and return the assistant's content.

    Parameters
    ----------
    messages
        Either a **prompt string** *or* a list of role/content dictionaries
        following the OpenAI schema.
    model
        Groq model ID. Defaults to ``GROQ_MODEL_ID`` or a sensible fallback.
    temperature
        Sampling temperature.
    max_tokens
        Maximum tokens in the reply.
    stream
        Whether to request a streaming response (ignored by this wrapper).

    Returns
    -------
    str
        The assistant's response content.
    """
    # Coerce prompt into the required list-of-dicts format
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

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
        raise LLMError(f"Malformed Groq response: {data}") from exc

