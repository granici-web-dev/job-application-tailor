from __future__ import annotations

import anthropic
from anthropic import Anthropic

from backend.errors import LLMError


def complete(client: Anthropic, *, model: str, system: str, user: str, max_tokens: int) -> str:
    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIStatusError as error:
        raise LLMError(_status_error_message(error, model)) from error
    except anthropic.APIConnectionError as error:
        raise LLMError(
            f"Could not reach the Anthropic API ({error}). Check your internet connection "
            "and try again."
        ) from error
    return "".join(block.text for block in message.content if block.type == "text")


def _status_error_message(error: anthropic.APIStatusError, model: str) -> str:
    detail = _api_message(error)
    if isinstance(error, (anthropic.AuthenticationError, anthropic.PermissionDeniedError)):
        return (
            f"The Anthropic API rejected the API key ({detail}). Check ANTHROPIC_API_KEY "
            "in your .env file and try again."
        )
    if "credit balance" in detail.lower():
        return (
            "The Anthropic account has no credit left, so nothing could be generated. "
            "Top up the balance under Plans & Billing in the Anthropic Console, then try again."
        )
    if isinstance(error, anthropic.NotFoundError):
        return (
            f"The Anthropic API does not know the model '{model}' ({detail}). "
            "Set ANTHROPIC_MODEL in your .env file to a model your account can use."
        )
    if isinstance(error, anthropic.RateLimitError):
        return f"The Anthropic API rate limit was hit ({detail}). Wait a minute and try again."
    if error.status_code >= 500:
        return (
            f"The Anthropic API is currently unavailable ({detail}). "
            "This is a problem on their side — try again in a few minutes."
        )
    return f"The Anthropic API refused the request ({detail})."


def _api_message(error: anthropic.APIStatusError) -> str:
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        inner = body.get("error")
        if isinstance(inner, dict) and isinstance(inner.get("message"), str):
            return inner["message"]
    return str(error)
