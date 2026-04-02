"""Artifact type classifier.

Classifies an incoming artifact into one of the known ArtifactType values using
MIME type heuristics, file extension mapping, and an optional LLM call for
ambiguous document types.
"""

import os
from typing import Optional

from app.models.artifact import ArtifactType

# ---------------------------------------------------------------------------
# MIME-type -> primary type mapping
# ---------------------------------------------------------------------------

_MIME_TYPE_MAP: dict[str, ArtifactType] = {
    "text/plain": "transcript",
    "text/vtt": "transcript",
    "text/srt": "transcript",
    "application/pdf": "policy_doc",  # refined by LLM if needed
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "policy_doc",
    "application/msword": "policy_doc",
    "audio/mpeg": "audio",
    "audio/mp3": "audio",
    "audio/wav": "audio",
    "audio/x-wav": "audio",
    "audio/webm": "audio",
    "audio/ogg": "audio",
    "audio/mp4": "audio",
    "audio/aac": "audio",
    "video/mp4": "video",
    "video/mpeg": "video",
    "video/webm": "video",
    "video/quicktime": "video",
    "video/x-matroska": "video",
    "application/x-git": "github_repo",
}

# ---------------------------------------------------------------------------
# File extension -> type mapping
# ---------------------------------------------------------------------------

_EXT_MAP: dict[str, ArtifactType] = {
    ".txt": "transcript",
    ".vtt": "transcript",
    ".srt": "transcript",
    ".pdf": "policy_doc",
    ".docx": "policy_doc",
    ".doc": "policy_doc",
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".aac": "audio",
    ".ogg": "audio",
    ".mp4": "video",
    ".mkv": "video",
    ".mov": "video",
    ".webm": "video",
    ".mpeg": "video",
    ".mpg": "video",
    ".md": "generic_text",
    ".rst": "generic_text",
}

# Document types that need sub-classification
_DOCUMENT_TYPES: set[ArtifactType] = {"policy_doc", "prd", "rfc", "postmortem", "contract"}

# Keywords that imply document sub-type
_DOC_TYPE_KEYWORDS: dict[ArtifactType, list[str]] = {
    "prd": ["product requirements", "prd", "product spec", "feature spec", "user story", "acceptance criteria", "mvp"],
    "rfc": ["request for comments", "rfc", "design doc", "design proposal", "architecture decision"],
    "postmortem": ["postmortem", "post-mortem", "incident report", "root cause", "lessons learned"],
    "contract": ["agreement", "contract", "terms and conditions", "sla", "service level", "nda", "non-disclosure"],
    "policy_doc": ["policy", "compliance", "regulation", "control", "obligation", "gdpr", "hipaa", "sox"],
}


def classify_from_metadata(
    mime_type: Optional[str] = None,
    filename: Optional[str] = None,
    title: Optional[str] = None,
) -> ArtifactType:
    """Classify using MIME type, filename extension, and title keywords only."""
    # MIME type lookup
    if mime_type:
        normalized = mime_type.lower().split(";")[0].strip()
        if normalized in _MIME_TYPE_MAP:
            base = _MIME_TYPE_MAP[normalized]
            if base == "policy_doc" and title:
                return _refine_doc_type_from_text(title)
            return base

    # Extension lookup
    if filename:
        ext = os.path.splitext(filename.lower())[1]
        if ext in _EXT_MAP:
            base = _EXT_MAP[ext]
            if base == "policy_doc" and title:
                return _refine_doc_type_from_text(title)
            return base

    # Title keyword scan
    if title:
        return _refine_doc_type_from_text(title)

    return "generic_text"


def classify_from_content_preview(content_preview: str) -> ArtifactType:
    """Heuristic classification from first few hundred characters of content."""
    lower = content_preview.lower()

    # Audio/video markers shouldn't appear in text, but check for transcript cues
    if any(marker in lower for marker in ["[00:", "(00:", "speaker a:", "speaker b:", " --> "]):
        return "transcript"

    # Speaker-turn-style meeting transcript
    import re
    if re.search(r"(?m)^[A-Z][A-Za-z .'-]{1,40}:\s", content_preview):
        return "transcript"

    return _refine_doc_type_from_text(lower)


def _refine_doc_type_from_text(text: str) -> ArtifactType:
    lower = text.lower()
    for doc_type, keywords in _DOC_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return doc_type
    return "generic_text"


async def classify_with_llm(
    llm,
    content_preview: str,
    filename: Optional[str] = None,
) -> ArtifactType:
    """Use LLM for ambiguous cases where heuristics aren't confident.

    Only called when mime_type and extension are inconclusive (e.g., plain PDF).
    """
    from app.llm.base import GenerateConfig

    prompt = f"""Classify this document excerpt into exactly one of these types:
transcript, policy_doc, prd, rfc, postmortem, contract, generic_text

Filename (if known): {filename or "unknown"}
Content preview (first 500 chars):
{content_preview[:500]}

Respond with ONLY the type name, nothing else."""

    try:
        raw = await llm.generate(prompt, GenerateConfig(temperature=0.0))
        result = raw.strip().lower().split()[0] if raw else ""
        valid: set[ArtifactType] = {
            "transcript", "policy_doc", "prd", "rfc", "postmortem", "contract", "generic_text"
        }
        if result in valid:
            return result  # type: ignore[return-value]
    except Exception:
        pass
    return "generic_text"
