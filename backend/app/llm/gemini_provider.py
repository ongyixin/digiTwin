"""Gemini-backed LLM provider."""

import asyncio
from typing import Optional

from google import genai
from google.genai import types

from app.llm.base import GenerateConfig, LLMProvider

# Hard cap per LLM call — prevents entity_extraction from hanging indefinitely
# when Gemini is slow or rate-limited.
_GENERATE_TIMEOUT_SECS = 120


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, chat_model: str, embedding_model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._chat_model = chat_model
        self._embedding_model = embedding_model

    @property
    def client(self) -> genai.Client:
        return self._client

    async def generate(self, prompt: str, config: Optional[GenerateConfig] = None) -> str:
        cfg = config or GenerateConfig()
        genai_config = types.GenerateContentConfig(
            temperature=cfg.temperature,
            **({"response_mime_type": cfg.response_mime_type} if cfg.response_mime_type else {}),
            **({"max_output_tokens": cfg.max_tokens} if cfg.max_tokens else {}),
        )
        response = await asyncio.wait_for(
            self._client.aio.models.generate_content(
                model=self._chat_model,
                contents=prompt,
                config=genai_config,
            ),
            timeout=_GENERATE_TIMEOUT_SECS,
        )
        return response.text or ""

    async def embed(self, text: str) -> Optional[list[float]]:
        if not text.strip():
            return None
        try:
            result = await self._client.aio.models.embed_content(
                model=self._embedding_model,
                contents=text[:8000],
            )
            return result.embeddings[0].values
        except Exception as e:
            print(f"Embedding error: {e}")
            return None
