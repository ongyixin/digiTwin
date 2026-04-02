"""Transcription provider factory."""

import os
from typing import Optional

from app.llm.base import LLMProvider
from app.services.transcription.base import TranscriptionProvider


def get_transcription_provider(llm: Optional[LLMProvider] = None) -> TranscriptionProvider:
    """Return the appropriate transcription provider based on configuration.

    Priority:
    1. OpenAI diarization if OPENAI_API_KEY is set and TRANSCRIPTION_PROVIDER=openai
    2. Gemini (default) using the existing LLM provider
    """
    from app.services.transcription.gemini_provider import GeminiTranscriptionProvider

    provider_name = os.environ.get("TRANSCRIPTION_PROVIDER", "gemini").lower()

    if provider_name == "openai":
        openai_key = os.environ.get("OPENAI_API_KEY", "")
        if openai_key:
            from app.services.transcription.openai_provider import OpenAITranscriptionProvider
            model = os.environ.get("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe-diarize")
            return OpenAITranscriptionProvider(api_key=openai_key, model=model)

    # Default to Gemini
    if llm is None:
        from app.dependencies import get_llm_provider_cached
        llm = get_llm_provider_cached()

    return GeminiTranscriptionProvider(llm=llm)
