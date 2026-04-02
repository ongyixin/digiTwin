"""OpenAI diarization-capable transcription provider.

Uses gpt-4o-transcribe-diarize for high-quality speaker diarization and
timestamp-accurate segments. Recommended for enterprise customers where
transcript quality and attribution are critical.

Requirements:
- OPENAI_API_KEY environment variable
- openai Python package installed

Limitations:
- 25 MB file size limit per request
- Requires chunking_strategy for audio > 30 seconds
- Does not support gpt-4o-transcribe prompts or logprobs
"""

import io
import json
from typing import Optional

from app.services.transcription.base import (
    TranscriptionConfig,
    TranscriptionProvider,
    TranscriptionResult,
    TranscriptionSegment,
)


class OpenAITranscriptionProvider(TranscriptionProvider):
    """Transcribes audio using OpenAI gpt-4o-transcribe-diarize."""

    def __init__(self, api_key: str, model: str = "gpt-4o-transcribe-diarize") -> None:
        self._api_key = api_key
        self._model = model

    async def transcribe(
        self,
        raw_content: bytes | str | None,
        request,
        config: Optional[TranscriptionConfig] = None,
    ) -> TranscriptionResult:
        try:
            import openai
        except ImportError:
            raise RuntimeError(
                "openai package is required for OpenAITranscriptionProvider. "
                "Install it with: pip install openai"
            )

        if not isinstance(raw_content, bytes):
            raise ValueError("OpenAI transcription requires bytes content")

        cfg = config or TranscriptionConfig()
        filename = request.metadata.get("filename", "recording.mp3")
        mime_type = request.mime_type or "audio/mpeg"

        client = openai.AsyncOpenAI(api_key=self._api_key)

        # Build response_format based on diarization mode
        response_format = "diarized_json" if cfg.diarize else "json"

        try:
            file_tuple = (filename, io.BytesIO(raw_content), mime_type)
            response = await client.audio.transcriptions.create(
                model=self._model,
                file=file_tuple,
                response_format=response_format,
                chunking_strategy=cfg.chunking_strategy,
                **({"language": cfg.language} if cfg.language else {}),
            )

            return _parse_openai_response(response, response_format)
        except Exception as e:
            raise RuntimeError(f"OpenAI transcription failed: {e}") from e


def _parse_openai_response(response, response_format: str) -> TranscriptionResult:
    """Parse OpenAI transcription response into a TranscriptionResult."""
    if response_format == "diarized_json":
        # diarized_json has top-level 'text' and 'utterances' or 'segments'
        if hasattr(response, "model_dump"):
            data = response.model_dump()
        elif isinstance(response, dict):
            data = response
        else:
            data = json.loads(str(response))

        full_text = data.get("text", "")
        raw_segments = data.get("utterances", data.get("segments", []))
        segments = [
            TranscriptionSegment(
                speaker=seg.get("speaker", "Unknown"),
                text=seg.get("text", ""),
                start_ts=float(seg.get("start", 0.0)),
                end_ts=float(seg.get("end", 0.0)),
            )
            for seg in raw_segments
        ]
        return TranscriptionResult(
            text=full_text,
            language=data.get("language", "en"),
            segments=segments,
            provider="openai-diarize",
        )
    else:
        # Standard json format
        text = response.text if hasattr(response, "text") else str(response)
        return TranscriptionResult(
            text=text,
            language="en",
            segments=[TranscriptionSegment(speaker="Unknown", text=text, start_ts=0.0, end_ts=0.0)],
            provider="openai",
        )
