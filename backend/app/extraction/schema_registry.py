"""Schema registry — maps artifact_type to (prompt_file, GraphSchema).

Used by adapters to select the correct extraction schema and prompt for each
artifact type family.
"""

from typing import NamedTuple

from neo4j_graphrag.experimental.components.schema import GraphSchema

from app.extraction.schema import (
    DIGITWIN_SCHEMA,
    POLICY_SCHEMA,
    PRD_SCHEMA,
    REPO_SCHEMA,
    AUDIO_SCHEMA,
)


class SchemaEntry(NamedTuple):
    prompt_file: str
    schema: GraphSchema


# Maps artifact_type -> (prompt_file, GraphSchema)
_REGISTRY: dict[str, SchemaEntry] = {
    "transcript": SchemaEntry("extract_decisions.txt", DIGITWIN_SCHEMA),
    "policy_doc": SchemaEntry("extract_policy.txt", POLICY_SCHEMA),
    "contract": SchemaEntry("extract_policy.txt", POLICY_SCHEMA),
    "prd": SchemaEntry("extract_prd.txt", PRD_SCHEMA),
    "rfc": SchemaEntry("extract_prd.txt", PRD_SCHEMA),
    "postmortem": SchemaEntry("extract_decisions.txt", DIGITWIN_SCHEMA),
    "audio": SchemaEntry("extract_audio_video.txt", AUDIO_SCHEMA),
    "video": SchemaEntry("extract_audio_video.txt", AUDIO_SCHEMA),
    "github_repo": SchemaEntry("extract_repo.txt", REPO_SCHEMA),
    "generic_text": SchemaEntry("extract_decisions.txt", DIGITWIN_SCHEMA),
}

_FALLBACK = SchemaEntry("extract_decisions.txt", DIGITWIN_SCHEMA)


class SchemaRegistry:
    def get(self, artifact_type: str) -> SchemaEntry:
        return _REGISTRY.get(artifact_type, _FALLBACK)

    def all_types(self) -> list[str]:
        return list(_REGISTRY.keys())


registry = SchemaRegistry()
