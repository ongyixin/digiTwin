"""Audio / video adapter — transcribes recordings and extracts structured
graph entities including speaker turns, decisions, and action items.
"""

import hashlib
import json
from typing import Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult
from app.services.adapters.base import BaseAdapter
from app.services.graph_service import GraphService, _new_id
from app.services.pii_service import get_pii_service


class AudioVideoAdapter(BaseAdapter):
    """Ingestion adapter for audio and video recordings.

    Pipeline:
    1. Upload file
    2. Transcribe (via Gemini audio/video understanding, or pluggable STT provider)
    3. Speaker diarization (embedded in transcription)
    4. Section split by speaker turns
    5. Entity extraction (decisions, action items, key moments)
    6. Embedding + graph upsert
    7. Provenance linking
    """

    @property
    def pipeline_stages(self) -> list[str]:
        return [
            "upload",
            "transcribe",
            "speaker_diarize",
            "section_split",
            "entity_extraction",
            "relationship_extraction",
            "embedding",
            "graph_upsert",
            "provenance",
        ]

    async def ingest(
        self,
        request: ArtifactIngestRequest,
        raw_content: Optional[bytes | str],
        driver: AsyncDriver,
        llm: LLMProvider,
        job_emitter: Optional[Callable] = None,
    ) -> ArtifactIngestResult:
        from app.services.transcription import get_transcription_provider

        graph = GraphService(driver)
        pii_svc = get_pii_service()

        title = request.metadata.get("title") or request.metadata.get("filename") or "Recording"
        artifact_id = _new_id("ART")
        artifact_version_id = _new_id("AV")

        await self._emit(job_emitter, "stage_started", stage="upload", detail="Registering recording artifact")
        content_hash = hashlib.sha256(
            raw_content if isinstance(raw_content, bytes) else (raw_content or "").encode()
        ).hexdigest()[:16]
        await graph.upsert_artifact(
            artifact_id=artifact_id,
            artifact_type=request.artifact_type,
            source_type=request.source_type,
            title=title,
            workspace_id=request.workspace_id,
            sensitivity=request.sensitivity,
            mime_type=request.mime_type or "audio/mpeg",
            metadata=request.metadata,
        )
        await graph.upsert_artifact_version(
            version_id=artifact_version_id,
            artifact_id=artifact_id,
            content_hash=content_hash,
            model_version="gemini-2.5-flash",
        )
        await self._emit(job_emitter, "stage_completed", stage="upload", entities_found=1)

        # Transcription
        await self._emit(job_emitter, "stage_started", stage="transcribe", detail="Transcribing audio/video")
        provider = get_transcription_provider(llm)
        transcript_result = await provider.transcribe(raw_content, request)
        transcript_text = transcript_result.text
        segments = transcript_result.segments  # list of {speaker, text, start_ts, end_ts}
        await self._emit(job_emitter, "stage_completed", stage="transcribe", entities_found=len(segments))

        # Speaker diarization (already embedded in transcript_result)
        await self._emit(job_emitter, "stage_started", stage="speaker_diarize",
                         detail=f"Identified {len(set(s.get('speaker','') for s in segments))} speakers")
        await self._emit(job_emitter, "stage_completed", stage="speaker_diarize",
                         entities_found=len(segments))

        # Section split: group segments into logical chunks
        await self._emit(job_emitter, "stage_started", stage="section_split")
        sections = _group_segments(segments)
        section_nodes = []
        for i, (sec_speaker, sec_text, start_ts, end_ts) in enumerate(sections):
            section_id = _new_id("SEC")
            await graph.upsert_section(
                section_id=section_id,
                artifact_version_id=artifact_version_id,
                title=f"{sec_speaker} ({_fmt_ts(start_ts)} – {_fmt_ts(end_ts)})",
                sequence=i,
                text_preview=sec_text[:200],
                timestamp_start=start_ts,
                timestamp_end=end_ts,
            )
            section_nodes.append((section_id, sec_speaker, sec_text, start_ts, end_ts))
        await self._emit(job_emitter, "stage_completed", stage="section_split", entities_found=len(sections))

        # Entity extraction from full transcript (use transcript schema)
        await self._emit(job_emitter, "stage_started", stage="entity_extraction",
                         detail="Extracting decisions and action items")
        all_entities = await _extract_audio_entities(llm, transcript_text, request, segments)
        await self._emit(job_emitter, "stage_completed", stage="entity_extraction",
                         entities_found=sum(len(v) for v in all_entities.values()))

        # Relationship extraction
        await self._emit(job_emitter, "stage_started", stage="relationship_extraction")
        relationships = await _extract_relationships(llm, all_entities)
        await self._emit(job_emitter, "stage_completed", stage="relationship_extraction",
                         entities_found=len(relationships))

        # Embed and upsert chunks
        await self._emit(job_emitter, "stage_started", stage="embedding")
        chunk_count = 0
        for section_id, speaker, sec_text, start_ts, end_ts in section_nodes:
            safe_text = pii_svc.scan_and_redact(sec_text).redacted_text
            embedding = await llm.embed(safe_text[:8000])
            chunk_id = _new_id("CHK")
            await graph.upsert_chunk(
                chunk_id=chunk_id,
                artifact_version_id=artifact_version_id,
                sequence=chunk_count,
                text=safe_text[:2000],
                embedding=embedding,
            )
            chunk_count += 1
        await self._emit(job_emitter, "stage_completed", stage="embedding", entities_found=chunk_count)

        # Graph upsert using the existing IngestionService path for decisions/tasks/approvals
        await self._emit(job_emitter, "stage_started", stage="graph_upsert")
        counts = await _upsert_audio_entities(
            graph, llm, pii_svc, all_entities, relationships,
            request, artifact_version_id, segments
        )
        counts["chunks"] = chunk_count
        await self._emit(job_emitter, "stage_completed", stage="graph_upsert",
                         entities_found=sum(counts.values()))

        await self._emit(job_emitter, "stage_started", stage="provenance")
        await self._emit(job_emitter, "stage_completed", stage="provenance", entities_found=chunk_count)

        return ArtifactIngestResult(
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            artifact_type=request.artifact_type,
            entities_created=counts,
            chunk_count=chunk_count,
            section_count=len(section_nodes),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _group_segments(segments: list[dict]) -> list[tuple[str, str, float, float]]:
    """Group speaker segments into logical sections (max ~500 words per section)."""
    if not segments:
        return []
    sections = []
    current_speaker = segments[0].get("speaker", "Unknown")
    current_texts = []
    current_start = segments[0].get("start_ts", 0.0)
    current_end = segments[0].get("end_ts", 0.0)
    word_count = 0

    for seg in segments:
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "")
        seg_words = len(text.split())
        end = seg.get("end_ts", current_end)

        if speaker != current_speaker or word_count + seg_words > 500:
            if current_texts:
                sections.append((current_speaker, " ".join(current_texts), current_start, current_end))
            current_speaker = speaker
            current_texts = [text]
            current_start = seg.get("start_ts", current_end)
            current_end = end
            word_count = seg_words
        else:
            current_texts.append(text)
            current_end = end
            word_count += seg_words

    if current_texts:
        sections.append((current_speaker, " ".join(current_texts), current_start, current_end))
    return sections


def _fmt_ts(ts: float) -> str:
    """Format seconds as mm:ss."""
    m, s = divmod(int(ts), 60)
    return f"{m}:{s:02d}"


async def _extract_audio_entities(
    llm: LLMProvider,
    transcript_text: str,
    request: ArtifactIngestRequest,
    segments: list[dict],
) -> dict:
    """Extract decisions, tasks, and action items from the transcript."""
    import os

    prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/extract_audio_video.txt")
    try:
        with open(prompt_path) as f:
            template = f.read()
    except FileNotFoundError:
        from app.services.ingestion_service import _load_prompt
        template = _load_prompt("extract_decisions.txt")

    # Build speaker summary for context
    speakers = list(set(s.get("speaker", "Unknown") for s in segments if s.get("speaker")))
    speaker_list = ", ".join(speakers) if speakers else "Unknown participants"

    prompt = (
        template
        .replace("{transcript}", transcript_text[:10000])
        .replace("{content}", transcript_text[:10000])
        .replace("{participants}", speaker_list)
        .replace("{meeting_title}", request.metadata.get("title", "Recording"))
        .replace("{meeting_date}", request.metadata.get("date", ""))
        .replace("{artifact_type}", request.artifact_type)
    )
    raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
    try:
        from app.services.ingestion_service import _clean_json
        return json.loads(_clean_json(raw or "{}"))
    except Exception:
        return {}


async def _extract_relationships(llm: LLMProvider, entities: dict) -> list[dict]:
    import json, os
    prompt_path = os.path.join(os.path.dirname(__file__), "../../prompts/extract_relationships.txt")
    try:
        with open(prompt_path) as f:
            template = f.read()
        prompt = template.replace("{entities}", json.dumps(entities, indent=2))
        raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
        from app.services.ingestion_service import _clean_json
        return json.loads(_clean_json(raw or '{"relationships": []}')).get("relationships", [])
    except Exception:
        return []


async def _upsert_audio_entities(
    graph: GraphService,
    llm: LLMProvider,
    pii_svc,
    entities: dict,
    relationships: list[dict],
    request: ArtifactIngestRequest,
    artifact_version_id: str,
    segments: list[dict],
) -> dict[str, int]:
    """Upsert extracted audio/video entities into Neo4j."""
    workspace = request.workspace_id
    sensitivity = request.sensitivity
    counts: dict[str, int] = {}

    # Speaker turns
    speaker_turn_count = 0
    for seg in segments:
        await graph.upsert_speaker_turn(
            artifact_version_id=artifact_version_id,
            speaker=seg.get("speaker", "Unknown"),
            text=seg.get("text", ""),
            start_ts=seg.get("start_ts", 0.0),
            end_ts=seg.get("end_ts", 0.0),
        )
        speaker_turn_count += 1
    counts["speaker_turns"] = speaker_turn_count

    # Decisions
    decision_map: dict[str, str] = {}
    for d in entities.get("decisions", []):
        embedding = await llm.embed(f"{d.get('title', '')} {d.get('summary', '')}")
        did = await graph.upsert_decision(
            title=d.get("title", "Untitled"),
            summary=d.get("summary", ""),
            confidence=d.get("confidence", 0.8),
            source_excerpt=d.get("source_excerpt", ""),
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
        decision_map[d.get("title", "")] = did
    counts["decisions"] = len(decision_map)

    # Tasks / action items
    task_count = 0
    for t in entities.get("tasks", []):
        await graph.upsert_task(
            title=t.get("title", ""),
            decision_id=decision_map.get(t.get("related_decision_title", ""), ""),
        )
        task_count += 1
    counts["tasks"] = task_count

    # Relationships
    for rel in relationships:
        try:
            await graph.upsert_relationship(
                from_label=rel.get("from_type", ""),
                from_title=rel.get("from_title", ""),
                rel_type=rel.get("relationship", ""),
                to_label=rel.get("to_type", ""),
                to_title=rel.get("to_title", ""),
            )
        except Exception:
            pass

    return counts
