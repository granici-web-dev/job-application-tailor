from types import SimpleNamespace
from unittest.mock import Mock

from backend.llm import complete


def test_complete_concatenates_text_blocks_and_ignores_non_text():
    client = Mock()
    client.messages.create.return_value = SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="Hello "),
            SimpleNamespace(type="tool_use", text="ignored"),
            SimpleNamespace(type="text", text="world"),
        ]
    )

    result = complete(client, model="claude-sonnet-4-6", system="sys", user="usr", max_tokens=100)

    assert result == "Hello world"
    _, kwargs = client.messages.create.call_args
    assert kwargs["system"] == "sys"
    assert kwargs["messages"] == [{"role": "user", "content": "usr"}]
