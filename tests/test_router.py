"""Tests for the Alexa – BlackRoad OS request router.

All @ triggers must resolve to the local Ollama backend.
No external provider (ChatGPT, Copilot, Claude …) should ever be called.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest

from src.router import Router


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_router(tmp_path, extra_triggers: list[str] | None = None) -> Router:
    """Return a Router backed by a temporary config file."""
    triggers = [
        "@ollama",
        "@copilot.",
        "@lucidia",
        "@blackboxprogramming.",
    ]
    if extra_triggers:
        triggers.extend(extra_triggers)
    config_text = f"""
ollama:
  base_url: "http://localhost:11434"
  default_model: "llama3"
  timeout: 10

ollama_triggers:
{chr(10).join("  - " + repr(t) for t in triggers)}
"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(config_text)
    return Router(config_path=str(config_file))


# ---------------------------------------------------------------------------
# Trigger detection
# ---------------------------------------------------------------------------

class TestIsTrigger:
    def test_ollama_trigger(self, tmp_path):
        router = _make_router(tmp_path)
        assert router.is_ollama_request("@ollama tell me a joke")

    def test_copilot_trigger(self, tmp_path):
        router = _make_router(tmp_path)
        assert router.is_ollama_request("@copilot. refactor this code")

    def test_lucidia_trigger(self, tmp_path):
        router = _make_router(tmp_path)
        assert router.is_ollama_request("@lucidia what's the weather?")

    def test_blackboxprogramming_trigger(self, tmp_path):
        router = _make_router(tmp_path)
        assert router.is_ollama_request("@blackboxprogramming. explain recursion")

    def test_case_insensitive(self, tmp_path):
        router = _make_router(tmp_path)
        assert router.is_ollama_request("@OLLAMA Hello")
        assert router.is_ollama_request("@Copilot. Hello")

    def test_trigger_anywhere_in_message(self, tmp_path):
        router = _make_router(tmp_path)
        assert router.is_ollama_request("Hey @ollama can you help?")

    def test_no_trigger_returns_false(self, tmp_path):
        router = _make_router(tmp_path)
        assert not router.is_ollama_request("just a normal message")

    def test_external_providers_not_triggers(self, tmp_path):
        router = _make_router(tmp_path)
        for msg in ["@chatgpt hello", "@claude help", "@openai answer"]:
            assert not router.is_ollama_request(msg)


# ---------------------------------------------------------------------------
# Routing – all triggers must reach Ollama, never an external provider
# ---------------------------------------------------------------------------

class TestRouting:
    def _patched_router(self, tmp_path):
        """Return a router whose OllamaClient.chat is mocked."""
        router = _make_router(tmp_path)
        router._client.chat = MagicMock(return_value="mocked response")
        return router

    def test_ollama_trigger_routes_to_ollama(self, tmp_path):
        router = self._patched_router(tmp_path)
        result = router.handle("@ollama what is 2+2?")
        router._client.chat.assert_called_once()
        assert result == "mocked response"

    def test_copilot_routes_to_ollama(self, tmp_path):
        router = self._patched_router(tmp_path)
        result = router.handle("@copilot. write a function")
        router._client.chat.assert_called_once()
        assert result == "mocked response"

    def test_lucidia_routes_to_ollama(self, tmp_path):
        router = self._patched_router(tmp_path)
        result = router.handle("@lucidia explain AI")
        router._client.chat.assert_called_once()
        assert result == "mocked response"

    def test_blackboxprogramming_routes_to_ollama(self, tmp_path):
        router = self._patched_router(tmp_path)
        result = router.handle("@blackboxprogramming. fix my bug")
        router._client.chat.assert_called_once()
        assert result == "mocked response"

    def test_unknown_trigger_raises_value_error(self, tmp_path):
        router = self._patched_router(tmp_path)
        with pytest.raises(ValueError, match="No recognised @ trigger"):
            router.handle("just a plain message")

    def test_prompt_stripped_of_trigger(self, tmp_path):
        router = self._patched_router(tmp_path)
        router.handle("@ollama explain black holes")
        call_args = router._client.chat.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        # The trigger itself should not appear in the prompt sent to Ollama
        assert "@ollama" not in prompt.lower()
        assert "explain black holes" in prompt


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

class TestStreaming:
    def test_stream_yields_tokens(self, tmp_path):
        router = _make_router(tmp_path)
        router._client.chat_stream = MagicMock(return_value=iter(["hello", " ", "world"]))
        tokens = list(router.handle_stream("@ollama hi"))
        assert tokens == ["hello", " ", "world"]

    def test_stream_raises_for_unknown_trigger(self, tmp_path):
        router = _make_router(tmp_path)
        with pytest.raises(ValueError):
            list(router.handle_stream("no trigger here"))


# ---------------------------------------------------------------------------
# OllamaClient
# ---------------------------------------------------------------------------

class TestOllamaClient:
    def test_is_available_true(self, tmp_path):
        from src.ollama_client import OllamaClient

        client = OllamaClient()
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            assert client.is_available() is True

    def test_is_available_false_on_connection_error(self, tmp_path):
        import requests as req

        from src.ollama_client import OllamaClient

        client = OllamaClient()
        with patch("requests.get", side_effect=req.exceptions.ConnectionError):
            assert client.is_available() is False

    def test_chat_blocking_returns_content(self, tmp_path):
        from src.ollama_client import OllamaClient

        client = OllamaClient()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "42"}}
        mock_resp.raise_for_status = MagicMock()
        with patch("requests.post", return_value=mock_resp):
            result = client.chat("what is 6x7?", stream=False)
        assert result == "42"
