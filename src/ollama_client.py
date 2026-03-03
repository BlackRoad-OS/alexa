"""Ollama HTTP client.

Sends chat/generation requests to a locally running Ollama instance.
No external AI provider is ever contacted.
"""

from __future__ import annotations

import json
from typing import Iterator

import requests


class OllamaClient:
    """Thin wrapper around the Ollama REST API."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def chat(
        self,
        prompt: str,
        model: str = "llama3",
        system: str | None = None,
        stream: bool = False,
    ) -> str:
        """Send *prompt* to Ollama and return the assistant reply as a string.

        When *stream* is True the response is yielded token-by-token via
        :meth:`chat_stream` and then joined before being returned.
        """
        if stream:
            return "".join(self.chat_stream(prompt, model=model, system=system))
        return self._chat_blocking(prompt, model=model, system=system)

    def chat_stream(
        self,
        prompt: str,
        model: str = "llama3",
        system: str | None = None,
    ) -> Iterator[str]:
        """Yield response tokens as they arrive from Ollama."""
        messages = self._build_messages(prompt, system)
        payload = {"model": model, "messages": messages, "stream": True}
        with requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                chunk = json.loads(raw_line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break

    def is_available(self) -> bool:
        """Return True when Ollama is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _chat_blocking(self, prompt: str, model: str, system: str | None) -> str:
        messages = self._build_messages(prompt, system)
        payload = {"model": model, "messages": messages, "stream": False}
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")

    @staticmethod
    def _build_messages(prompt: str, system: str | None) -> list[dict]:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages
