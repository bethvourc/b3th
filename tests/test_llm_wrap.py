from types import SimpleNamespace
from b3th.llm import chat_completion

def test_chat_completion_wraps_string_prompt(monkeypatch):
    """String prompts should be converted into a single user message."""
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        # Minimal OpenAI-compatible success payload
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": "ok"}}]},
            text="OK",
        )

    monkeypatch.setenv("GROQ_API_KEY", "dummy")
    monkeypatch.setenv("GROQ_API_BASE", "https://api.groq.com")
    monkeypatch.setenv("GROQ_MODEL_ID", "llama-3.3-70b-versatile")
    monkeypatch.setattr("b3th.llm.requests.post", fake_post, raising=True)

    out = chat_completion("hello world")  # pass a plain string
    assert out == "ok"
    assert isinstance(captured["json"]["messages"], list)
    assert captured["json"]["messages"][0]["role"] == "user"
    assert captured["json"]["messages"][0]["content"] == "hello world"
