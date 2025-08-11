from unittest.mock import patch

import pytest

from b3th import commit_message as cm

FAKE_DIFF = """
diff --git a/foo.py b/foo.py
index 0000000..1111111 100644
--- a/foo.py
+++ b/foo.py
@@
-print("hello")
+print("hello world")
"""


def test_generate_commit_message_success(monkeypatch):
    """Happy path: returns subject/body parsed from LLM reply."""
    monkeypatch.setenv("GROQ_API_KEY", "dummy")

    # Stub the staged diff
    monkeypatch.setattr(
        cm.git_utils, "get_staged_diff", lambda _: FAKE_DIFF, raising=True
    )

    fake_reply = (
        "feat(foo): improve greeting\n\n"
        "Expand the greeting in foo.py from a single word to a full phrase. "
        "This clarifies program output for end users and brings consistency "
        "with other modules."
    )

    # Stub the LLM call
    with patch.object(cm.llm, "chat_completion", return_value=fake_reply):
        subject, body = cm.generate_commit_message(".")

    assert subject == "feat(foo): improve greeting"
    assert "Expand the greeting" in body


def test_generate_commit_message_no_diff(monkeypatch):
    """Should raise CommitMessageError when nothing is staged."""
    monkeypatch.setattr(cm.git_utils, "get_staged_diff", lambda _: "", raising=True)

    with pytest.raises(cm.CommitMessageError):
        cm.generate_commit_message(".")
