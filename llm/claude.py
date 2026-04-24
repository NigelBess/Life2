import anthropic
from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def send(self, messages: list[dict], system: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=8096,
            system=system,
            messages=messages,
        )
        return response.content[0].text
