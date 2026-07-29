from types import SimpleNamespace
from unittest.mock import Mock

import anthropic
import httpx
import pytest

from backend.errors import TailorError
from backend.llm import complete

CREDIT_MESSAGE = (
    "Your credit balance is too low to access the Anthropic API. "
    "Please go to Plans & Billing to upgrade or purchase credits."
)


def _client_raising(error):
    client = Mock()
    client.messages.create.side_effect = error
    return client


def _status_error(error_class, status_code, message):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return error_class(
        "boom",
        response=httpx.Response(status_code, request=request),
        body={"type": "error", "error": {"type": "invalid_request_error", "message": message}},
    )


def _complete(client):
    return complete(client, model="claude-sonnet-4-6", system="sys", user="usr", max_tokens=100)


def test_complete_concatenates_text_blocks_and_ignores_non_text():
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Hello "),
            SimpleNamespace(type="tool_use", text="ignored"),
            SimpleNamespace(type="text", text="world"),
        ]
    )

    result = _complete(client)

    assert result == "Hello world"
    _, kwargs = client.messages.create.call_args
    assert kwargs["system"] == "sys"
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]


def test_exhausted_credit_becomes_a_user_facing_error():
    client = _client_raising(_status_error(anthropic.BadRequestError, 400, CREDIT_MESSAGE))

    with pytest.raises(TailorError) as caught:
        _complete(client)

    assert "no credit left" in str(caught.value)
    assert "Plans & Billing" in str(caught.value)


def test_rejected_key_points_at_the_env_file():
    client = _client_raising(_status_error(anthropic.AuthenticationError, 401, "invalid x-api-key"))

    with pytest.raises(TailorError) as caught:
        _complete(client)

    assert "ANTHROPIC_API_KEY" in str(caught.value)


def test_unknown_model_names_the_model():
    client = _client_raising(_status_error(anthropic.NotFoundError, 404, "model not found"))

    with pytest.raises(TailorError) as caught:
        _complete(client)

    assert "claude-sonnet-4-6" in str(caught.value)
    assert "ANTHROPIC_MODEL" in str(caught.value)


def test_rate_limit_suggests_waiting():
    client = _client_raising(_status_error(anthropic.RateLimitError, 429, "rate limit exceeded"))

    with pytest.raises(TailorError) as caught:
        _complete(client)

    assert "rate limit" in str(caught.value).lower()


def test_server_error_is_reported_as_their_side():
    client = _client_raising(_status_error(anthropic.InternalServerError, 529, "overloaded"))

    with pytest.raises(TailorError) as caught:
        _complete(client)

    assert "unavailable" in str(caught.value)


def test_connection_failure_mentions_the_network():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    client = _client_raising(anthropic.APIConnectionError(request=request))

    with pytest.raises(TailorError) as caught:
        _complete(client)

    assert "internet connection" in str(caught.value)
