"""Request router for the Alexa – BlackRoad OS assistant.

Any message that begins with (or contains) one of the configured @ triggers
is routed **exclusively** to the local Ollama instance.  No external AI
provider (ChatGPT, Copilot, Claude, etc.) is contacted.

Usage::

    from src.router import Router

    router = Router()
    response = router.handle("@ollama explain black holes")
    print(response)
"""

from __future__ import annotations

import re
from typing import Iterator

import yaml

from src.ollama_client import OllamaClient

_DEFAULT_CONFIG_PATH = "config.yaml"


def _load_config(path: str = _DEFAULT_CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class Router:
    """Route @ mention messages to the appropriate backend.

    All triggers listed in *config.yaml* under ``ollama_triggers`` are
    forwarded to the local Ollama instance.  Every other backend provider
    (Copilot, Claude, ChatGPT …) is intentionally **not** wired up — the
    owner of this system has explicitly requested that only Ollama is used.
    """

    def __init__(self, config_path: str = _DEFAULT_CONFIG_PATH) -> None:
        cfg = _load_config(config_path)
        ollama_cfg = cfg.get("ollama", {})
        self._client = OllamaClient(
            base_url=ollama_cfg.get("base_url", "http://localhost:11434"),
            timeout=ollama_cfg.get("timeout", 120),
        )
        self._default_model: str = ollama_cfg.get("default_model", "llama3")
        # Build a compiled pattern from the configured triggers (case-insensitive).
        raw_triggers: list[str] = cfg.get("ollama_triggers", [])
        self._triggers: list[str] = [t.lower() for t in raw_triggers]
        escaped = [re.escape(t) for t in self._triggers]
        self._trigger_pattern = re.compile(
            r"(?i)(" + "|".join(escaped) + r")",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def triggers(self) -> list[str]:
        """Return the list of configured @ triggers (lower-case)."""
        return list(self._triggers)

    def is_ollama_request(self, message: str) -> bool:
        """Return True when *message* contains an Ollama trigger."""
        return bool(self._trigger_pattern.search(message))

    def handle(self, message: str, stream: bool = False) -> str:
        """Route *message* and return the assistant reply.

        Raises :class:`ValueError` if the message does not contain a
        recognised trigger.  Raises :class:`RuntimeError` if Ollama is
        not reachable.
        """
        if not self.is_ollama_request(message):
            raise ValueError(
                f"No recognised @ trigger found in message. "
                f"Known triggers: {', '.join(self._triggers)}"
            )
        prompt = self._strip_trigger(message)
        return self._client.chat(prompt, model=self._default_model, stream=stream)

    def handle_stream(self, message: str) -> Iterator[str]:
        """Like :meth:`handle` but yields tokens as they arrive from Ollama."""
        if not self.is_ollama_request(message):
            raise ValueError(
                f"No recognised @ trigger found in message. "
                f"Known triggers: {', '.join(self._triggers)}"
            )
        prompt = self._strip_trigger(message)
        yield from self._client.chat_stream(prompt, model=self._default_model)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _strip_trigger(self, message: str) -> str:
        """Remove the trigger prefix (and leading whitespace) from *message*."""
        cleaned = self._trigger_pattern.sub("", message).strip()
        return cleaned if cleaned else message.strip()
