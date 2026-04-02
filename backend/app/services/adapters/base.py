"""Base adapter interface for artifact ingestion."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult


class BaseAdapter(ABC):
    """Abstract base for all artifact ingestion adapters.

    Each adapter handles one artifact type family, declares its own pipeline
    stages, and implements a full ingest() method.
    """

    @property
    @abstractmethod
    def pipeline_stages(self) -> list[str]:
        """Ordered list of pipeline stage names exposed to the job tracker."""
        ...

    @abstractmethod
    async def ingest(
        self,
        request: ArtifactIngestRequest,
        raw_content: Optional[bytes | str],
        driver: AsyncDriver,
        llm: LLMProvider,
        job_emitter: Optional[Callable] = None,
    ) -> ArtifactIngestResult:
        """Execute the full ingestion pipeline and return summary stats."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _emit(
        self,
        job_emitter: Optional[Callable],
        event: str,
        **kwargs: Any,
    ) -> None:
        if job_emitter:
            await job_emitter(event, **kwargs)
