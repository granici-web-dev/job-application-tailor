from __future__ import annotations

from anthropic import Anthropic


def complete(client: Anthropic, *, model: str, system: str, user: str, max_tokens: int) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
