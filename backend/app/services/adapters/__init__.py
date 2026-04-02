"""Artifact ingestion adapters."""
from app.services.adapters.base import BaseAdapter
from app.services.adapters.transcript_adapter import TranscriptAdapter
from app.services.adapters.document_adapter import DocumentAdapter
from app.services.adapters.audio_video_adapter import AudioVideoAdapter
from app.services.adapters.github_adapter import GitHubRepoAdapter
from app.services.adapters.generic_adapter import GenericTextAdapter

__all__ = [
    "BaseAdapter",
    "TranscriptAdapter",
    "DocumentAdapter",
    "AudioVideoAdapter",
    "GitHubRepoAdapter",
    "GenericTextAdapter",
]
