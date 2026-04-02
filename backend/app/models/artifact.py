"""Artifact domain models for the universal intake layer."""

from typing import Any, Literal, Optional

from pydantic import BaseModel

ArtifactType = Literal[
    "transcript",
    "policy_doc",
    "prd",
    "rfc",
    "postmortem",
    "contract",
    "audio",
    "video",
    "github_repo",
    "generic_text",
]

SourceType = Literal["upload", "url", "gcs", "github", "connector"]
SensitivityLevel = Literal["public", "internal", "confidential", "restricted"]
IngestMode = Literal["sync", "async"]

DOCUMENT_TYPES: set[ArtifactType] = {"policy_doc", "prd", "rfc", "postmortem", "contract"}
AUDIO_VIDEO_TYPES: set[ArtifactType] = {"audio", "video"}


class ArtifactIngestRequest(BaseModel):
    artifact_type: ArtifactType = "transcript"
    source_type: SourceType = "upload"
    mime_type: Optional[str] = None
    workspace_id: str = "default"
    sensitivity: SensitivityLevel = "internal"
    metadata: dict[str, Any] = {}
    ingest_mode: IngestMode = "async"
    principal_user_id: str = "anonymous"

    # For URL / GCS / GitHub references
    source_url: Optional[str] = None

    # Transcript-specific
    meeting_title: Optional[str] = None
    meeting_date: Optional[str] = None
    participants: list[str] = []

    # GitHub-specific
    github_repo_url: Optional[str] = None
    github_branch: str = "main"
    github_installation_id: Optional[str] = None


class ArtifactIngestResult(BaseModel):
    artifact_id: str
    artifact_version_id: str
    artifact_type: ArtifactType
    entities_created: dict[str, int] = {}
    chunk_count: int = 0
    section_count: int = 0


class ArtifactRecord(BaseModel):
    """Lightweight summary of an ingested artifact (for list views)."""

    id: str
    type: ArtifactType
    title: str
    source_type: SourceType
    workspace_id: str
    sensitivity: SensitivityLevel
    status: str
    ingested_at: str
    entity_count: int = 0
    version_count: int = 0
