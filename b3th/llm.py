"""
Groq LLM wrapper.

Call ``chat_completion()`` with either a prompt *string* or a full list of
OpenAI-style message dicts; the helper will do the right thing.
"""

from __future__ import annotations

import os
import time
from typing import Any

import requests

from .config import ConfigError, get_groq_key


class LLMError(RuntimeError):
    """Raised when the Groq API returns an error or an unexpected payload."""


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _api_key() -> str:
    try:
        return get_groq_key(required=True)  # loads from env/.env or TOML
    except ConfigError as e:
        raise LLMError(str(e)) from e


def _api_base() -> str:
    # Allow override; default to public Groq endpoint
    return os.getenv("GROQ_API_BASE", "https://api.groq.com").rstrip("/")


def _default_model() -> str:
    # Sensible default; overridable via env
    return os.getenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")


def _extract_error_text(resp: requests.Response) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict):
            # Groq/OpenAI style: {"error": {"message": "..."}}
            err = data.get("error")
            if isinstance(err, dict) and "message" in err:
                return str(err["message"])
            # Sometimes errors are nested differently
            if "message" in data:
                return str(data["message"])
        return resp.text
    except Exception:
        return resp.text


# --------------------------------------------------------------------------- #
# Public function
# --------------------------------------------------------------------------- #
def chat_completion(
    messages: str | list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 512,
    stream: bool = False,
    system: str | None = None,
    timeout: int = 30,
    retries: int = 1,
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
        Whether to request a streaming response (this wrapper returns the full text).
    system
        Optional system prompt to prepend.
    timeout
        Request timeout in seconds (per attempt).
    retries
        Number of additional attempts on transient errors (HTTP 429/5xx).

    Returns
    -------
    str
        The assistant's response content.
    """
    # Coerce prompt into the required list-of-dicts format
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    if system:
        messages = [{"role": "system", "content": system}] + messages

    url = f"{_api_base()}/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model or _default_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,  # we request it if asked, but still return a single string
    }

    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.RequestException as exc:
            if attempt <= retries:
                time.sleep(min(2**attempt, 8))  # simple backoff
                continue
            raise LLMError(f"Network error calling Groq: {exc}") from exc

        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMError(f"Malformed Groq response: {data}") from exc

        # Retry on transient errors
        if resp.status_code in (429, 500, 502, 503, 504) and attempt <= retries:
            time.sleep(min(2**attempt, 8))
            continue

        # Non-retriable or out of retries
        err_text = _extract_error_text(resp)
        raise LLMError(f"Groq API error {resp.status_code}: {err_text}")
