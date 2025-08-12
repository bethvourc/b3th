from unittest.mock import MagicMock, patch

import pytest

from b3th import llm


def test_chat_completion_success(monkeypatch):
    """Happy-path: wrapper returns content string and issues one HTTP call."""
    monkeypatch.setenv("GROQ_API_KEY", "test_key")

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": "Hello from Groq!"}}]
    }

    with patch("requests.post", return_value=fake_resp) as mock_post:
        reply = llm.chat_completion(
            [{"role": "user", "content": "Hi"}], model="dummy-model"
        )

    assert reply == "Hello from Groq!"
    mock_post.assert_called_once()
    # Endpoint sanity check
    assert "/openai/v1/chat/completions" in mock_post.call_args.args[0]


def test_chat_completion_no_key(monkeypatch):
    """Wrapper should raise LLMError when the API key is missing."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(llm.LLMError):
        llm.chat_completion([{"role": "user", "content": "Hi"}])
