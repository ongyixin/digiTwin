"""Abstract base for LLM and embedding providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GenerateConfig:
    temperature: float = 0.1
    response_mime_type: Optional[str] = None
    max_tokens: Optional[int] = None
    extra: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Provider-agnostic interface for text generation and embedding."""

    @abstractmethod
    async def generate(self, prompt: str, config: Optional[GenerateConfig] = None) -> str:
        """Generate text from a prompt. Returns the text response."""

    @abstractmethod
    async def embed(self, text: str) -> Optional[list[float]]:
        """Generate an embedding vector for text. Returns None on error."""
