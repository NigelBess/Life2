from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def send(self, messages: list[dict], system: str) -> str:
        """Send messages to the LLM and return the raw response text."""
        ...
