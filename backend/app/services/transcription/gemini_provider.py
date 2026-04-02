"""Gemini-based transcription provider.

Uses Gemini's native audio/video understanding to produce a full transcript
with speaker segments and timestamps in a single model call.

Advantages:
- Single provider, no additional API keys
- Works for all formats Gemini supports (mp3, mp4, wav, webm, m4a, mpeg)
- Can simultaneously extract semantic content (decisions, action items)
- 1-hour audio limit via the Files API

Limitations:
- Speaker diarization accuracy is lower than dedicated STT services
- No word-level timestamps (segment-level only)
"""

import io
import json
import re
from typing import Optional

from app.llm.base import GenerateConfig, LLMProvider
from app.services.transcription.base import (
    TranscriptionConfig,
    TranscriptionProvider,
    TranscriptionResult,
    TranscriptionSegment,
)


class GeminiTranscriptionProvider(TranscriptionProvider):
    """Transcribes audio/video using Gemini's multimodal understanding."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def transcribe(
        self,
        raw_content: bytes | str | None,
        request,
        config: Optional[TranscriptionConfig] = None,
    ) -> TranscriptionResult:
        from app.llm.gemini_provider import GeminiProvider

        if not isinstance(self._llm, GeminiProvider):
            return self._fallback_text(raw_content)

        if not raw_content or not isinstance(raw_content, bytes):
            return self._fallback_text(raw_content)

        mime_type = request.mime_type or _guess_mime(request.metadata.get("filename", ""))

        try:
            from google.genai import types as genai_types

            file_obj = io.BytesIO(raw_content)
            uploaded = await self._llm.client.aio.files.upload(
                file=file_obj,
                config=genai_types.UploadFileConfig(mime_type=mime_type),
            )

            prompt = _TRANSCRIPTION_PROMPT
            response = await self._llm.client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded, prompt],
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.0,
                ),
            )
            return _parse_gemini_response(response.text or "")
        except Exception as e:
            print(f"Gemini transcription failed: {e}")
            return self._fallback_text(raw_content)

    def _fallback_text(self, raw_content: bytes | str | None) -> TranscriptionResult:
        """Return a minimal result if Gemini transcription isn't possible."""
        if isinstance(raw_content, bytes):
            try:
                text = raw_content.decode("utf-8")
            except Exception:
                text = ""
        else:
            text = raw_content or ""
        return TranscriptionResult(
            text=text,
            language="en",
            segments=[TranscriptionSegment(speaker="Unknown", text=text, start_ts=0.0, end_ts=0.0)],
            provider="gemini-fallback",
        )


_TRANSCRIPTION_PROMPT = """Transcribe this audio/video recording.

Return ONLY valid JSON in this exact format:
{
  "full_transcript": "The complete verbatim transcript",
  "language": "en",
  "segments": [
    {
      "speaker": "Speaker A",
      "text": "What they said",
      "start_ts": 0.0,
      "end_ts": 12.5
    }
  ]
}

Rules:
- Label speakers as "Speaker A", "Speaker B", etc. unless names are audible
- Include all spoken content verbatim
- Timestamps should be in seconds
- For video, focus on the spoken audio track
- If you cannot detect speaker changes, use a single "Speaker A" for everything
"""


def _parse_gemini_response(raw: str) -> TranscriptionResult:
    """Parse the structured JSON response from Gemini transcription."""
    try:
        # Strip markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```[a-z]*\n?", "", clean)
            clean = re.sub(r"\n?```$", "", clean)

        data = json.loads(clean)
        segments = [
            TranscriptionSegment(
                speaker=seg.get("speaker", "Unknown"),
                text=seg.get("text", ""),
                start_ts=float(seg.get("start_ts", 0.0)),
                end_ts=float(seg.get("end_ts", 0.0)),
            )
            for seg in data.get("segments", [])
        ]
        full_text = data.get("full_transcript", " ".join(s.text for s in segments))
        return TranscriptionResult(
            text=full_text,
            language=data.get("language", "en"),
            segments=segments,
            provider="gemini",
        )
    except Exception as e:
        print(f"Failed to parse Gemini transcription response: {e}")
        return TranscriptionResult(
            text=raw,
            language="en",
            segments=[TranscriptionSegment(speaker="Unknown", text=raw, start_ts=0.0, end_ts=0.0)],
            provider="gemini-parse-error",
        )


def _guess_mime(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
        "ogg": "audio/ogg",
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
    }.get(ext, "audio/mpeg")
