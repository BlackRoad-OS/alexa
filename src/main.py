"""Alexa – BlackRoad OS assistant entry point.

All requests are routed to the local Ollama instance.
No external AI provider is contacted.

Usage::

    python -m src.main "@ollama what is the capital of France?"
    python -m src.main "@copilot. refactor this function"
    python -m src.main  # interactive REPL
"""

from __future__ import annotations

import sys

from src.router import Router


def _repl(router: Router) -> None:
    print("Alexa – BlackRoad OS  [powered by Ollama]")
    print("Type your message with an @ trigger, or 'exit' to quit.\n")
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not message:
            continue
        if message.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        if not router.is_ollama_request(message):
            print(
                "  ⚠  No recognised @ trigger. "
                f"Available triggers: {', '.join(router.triggers)}\n"
            )
            continue
        try:
            print("Alexa: ", end="", flush=True)
            for token in router.handle_stream(message):
                print(token, end="", flush=True)
            print("\n")
        except Exception as exc:  # noqa: BLE001
            print(f"\n  ✗  Error: {exc}\n")


def main() -> None:
    router = Router()
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        if not router.is_ollama_request(message):
            print(
                f"Error: no recognised @ trigger found.\n"
                f"Available triggers: {', '.join(router.triggers)}",
                file=sys.stderr,
            )
            sys.exit(1)
        try:
            for token in router.handle_stream(message):
                print(token, end="", flush=True)
            print()
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        _repl(router)


if __name__ == "__main__":
    main()
