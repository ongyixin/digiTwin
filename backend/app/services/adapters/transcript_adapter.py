"""Transcript adapter — wraps the existing IngestionService for meetings,
interviews, and support-call transcripts.
"""

from typing import Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult
from app.services.adapters.base import BaseAdapter
from app.services.graph_service import GraphService, _new_id
from app.services.ingestion_service import IngestionService


class TranscriptAdapter(BaseAdapter):
    """Ingestion adapter for meeting / interview / support-call transcripts."""

    @property
    def pipeline_stages(self) -> list[str]:
        return [
            "setup",
            "chunking",
            "entity_extraction",
            "relationship_extraction",
            "embedding",
            "graph_upsert",
            "provenance",
            "twin_diff",
        ]

    async def ingest(
        self,
        request: ArtifactIngestRequest,
        raw_content: Optional[bytes | str],
        driver: AsyncDriver,
        llm: LLMProvider,
        job_emitter: Optional[Callable] = None,
    ) -> ArtifactIngestResult:
        # Decode bytes — handle PDF or plain text
        if isinstance(raw_content, bytes):
            if raw_content[:4] == b"%PDF":
                transcript_text = _extract_pdf_text(raw_content)
            else:
                transcript_text = raw_content.decode("utf-8")
        else:
            transcript_text = raw_content or ""

        meeting_title = request.meeting_title or request.metadata.get("meeting_title", "Untitled Meeting")
        meeting_date = request.meeting_date or request.metadata.get("meeting_date", "2026-01-01")
        participants = request.participants or request.metadata.get("participants", [])
        workspace = request.workspace_id
        sensitivity = request.sensitivity

        # Register artifact + version in provenance layer
        graph = GraphService(driver)
        artifact_id = _new_id("ART")
        artifact_version_id = _new_id("AV")
        await graph.upsert_artifact(
            artifact_id=artifact_id,
            artifact_type="transcript",
            source_type=request.source_type,
            title=meeting_title,
            workspace_id=workspace,
            sensitivity=sensitivity,
            mime_type=request.mime_type or "text/plain",
            metadata=request.metadata,
        )
        await graph.upsert_artifact_version(
            version_id=artifact_version_id,
            artifact_id=artifact_id,
            content_hash=_content_hash(transcript_text),
            model_version="gemini-2.5-flash",
        )

        # Delegate to the existing IngestionService which handles all extraction
        svc = IngestionService(driver, llm)
        result = await svc.ingest_transcript(
            transcript=transcript_text,
            meeting_title=meeting_title,
            meeting_date=meeting_date,
            participants=participants,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
            job_emitter=job_emitter,
            artifact_version_id=artifact_version_id,
        )

        return ArtifactIngestResult(
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            artifact_type="transcript",
            entities_created=result.entities_created,
        )


def _content_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _extract_pdf_text(data: bytes) -> str:
    """Extract plain text from a PDF byte stream using pypdf."""
    import io
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)
