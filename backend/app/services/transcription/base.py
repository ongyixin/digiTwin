"""Transcription provider abstraction.

Allows swapping between Gemini-native transcription (simple, single model)
and dedicated STT services like OpenAI gpt-4o-transcribe-diarize (better
diarization and timestamps for enterprise use cases).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranscriptionConfig:
    language: Optional[str] = None
    diarize: bool = True
    max_speakers: Optional[int] = None
    chunking_strategy: str = "auto"


@dataclass
class TranscriptionSegment:
    speaker: str
    text: str
    start_ts: float
    end_ts: float


@dataclass
class TranscriptionResult:
    text: str
    language: str = "en"
    segments: list[TranscriptionSegment] = field(default_factory=list)
    provider: str = "unknown"

    def to_segments_dicts(self) -> list[dict]:
        return [
            {
                "speaker": s.speaker,
                "text": s.text,
                "start_ts": s.start_ts,
                "end_ts": s.end_ts,
            }
            for s in self.segments
        ]


class TranscriptionProvider(ABC):
    """Abstract base for transcription/diarization providers."""

    @abstractmethod
    async def transcribe(
        self,
        raw_content: bytes | str | None,
        request,  # ArtifactIngestRequest
        config: Optional[TranscriptionConfig] = None,
    ) -> TranscriptionResult:
        ...
