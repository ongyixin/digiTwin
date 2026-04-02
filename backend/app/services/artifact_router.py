"""Artifact router — maps artifact_type to the appropriate adapter and
dispatches the ingestion call.
"""

from typing import Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult, DOCUMENT_TYPES, AUDIO_VIDEO_TYPES
from app.services.adapters.audio_video_adapter import AudioVideoAdapter
from app.services.adapters.document_adapter import DocumentAdapter
from app.services.adapters.generic_adapter import GenericTextAdapter
from app.services.adapters.github_adapter import GitHubRepoAdapter
from app.services.adapters.transcript_adapter import TranscriptAdapter


class ArtifactRouter:
    """Routes an ArtifactIngestRequest to the correct adapter."""

    def __init__(self) -> None:
        self._transcript = TranscriptAdapter()
        self._document = DocumentAdapter()
        self._audio_video = AudioVideoAdapter()
        self._github = GitHubRepoAdapter()
        self._generic = GenericTextAdapter()

    def pipeline_stages_for(self, artifact_type: str) -> list[str]:
        """Return the pipeline stages that will be used for a given artifact type."""
        adapter = self._resolve(artifact_type)
        return adapter.pipeline_stages

    async def route(
        self,
        request: ArtifactIngestRequest,
        raw_content: Optional[bytes | str],
        driver: AsyncDriver,
        llm: LLMProvider,
        job_emitter: Optional[Callable] = None,
    ) -> ArtifactIngestResult:
        """Dispatch to the appropriate adapter."""
        adapter = self._resolve(request.artifact_type)
        return await adapter.ingest(request, raw_content, driver, llm, job_emitter)

    def _resolve(self, artifact_type: str):
        if artifact_type == "transcript":
            return self._transcript
        if artifact_type in DOCUMENT_TYPES:
            return self._document
        if artifact_type in AUDIO_VIDEO_TYPES:
            return self._audio_video
        if artifact_type == "github_repo":
            return self._github
        return self._generic


# Singleton
_router: Optional[ArtifactRouter] = None


def get_artifact_router() -> ArtifactRouter:
    global _router
    if _router is None:
        _router = ArtifactRouter()
    return _router
