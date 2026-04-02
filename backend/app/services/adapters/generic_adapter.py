"""Generic text adapter — handles freeform text dumps and unknown artifact types."""

import hashlib
import json
from typing import Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult
from app.services.adapters.base import BaseAdapter
from app.services.graph_service import GraphService, _new_id
from app.services.pii_service import get_pii_service


class GenericTextAdapter(BaseAdapter):
    """Ingestion adapter for unclassified text content."""

    @property
    def pipeline_stages(self) -> list[str]:
        return [
            "setup",
            "chunking",
            "entity_extraction",
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
        from app.services.ingestion_service import _speaker_turn_chunks, _clean_json

        graph = GraphService(driver)
        pii_svc = get_pii_service()

        if isinstance(raw_content, bytes):
            text = raw_content.decode("utf-8", errors="replace")
        else:
            text = raw_content or ""

        title = request.metadata.get("title", "Generic Text")
        artifact_id = _new_id("ART")
        artifact_version_id = _new_id("AV")

        await self._emit(job_emitter, "stage_started", stage="setup", detail="Registering artifact")
        content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        await graph.upsert_artifact(
            artifact_id=artifact_id,
            artifact_type=request.artifact_type,
            source_type=request.source_type,
            title=title,
            workspace_id=request.workspace_id,
            sensitivity=request.sensitivity,
            mime_type=request.mime_type or "text/plain",
            metadata=request.metadata,
        )
        await graph.upsert_artifact_version(
            version_id=artifact_version_id,
            artifact_id=artifact_id,
            content_hash=content_hash,
            model_version="gemini-2.5-flash",
        )
        await self._emit(job_emitter, "stage_completed", stage="setup", entities_found=1)

        await self._emit(job_emitter, "stage_started", stage="chunking")
        chunks = _speaker_turn_chunks(text, max_words=2000, overlap_words=200)
        await self._emit(job_emitter, "stage_completed", stage="chunking", entities_found=len(chunks))

        await self._emit(job_emitter, "stage_started", stage="entity_extraction")
        from app.services.ingestion_service import _load_prompt

        prompt_template = _load_prompt("extract_decisions.txt")
        all_entities: dict[str, list] = {"decisions": [], "assumptions": [], "evidence": [], "tasks": [], "approvals": []}

        for i, chunk in enumerate(chunks):
            safe_chunk = pii_svc.scan_and_redact(chunk).redacted_text
            prompt = (
                prompt_template
                .replace("{transcript}", safe_chunk)
                .replace("{meeting_title}", title)
                .replace("{meeting_date}", request.metadata.get("date", ""))
                .replace("{participants}", "")
            )
            raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
            try:
                extracted = json.loads(_clean_json(raw or "{}"))
                for key in all_entities:
                    all_entities[key].extend(extracted.get(key, []))
            except Exception:
                pass

        await self._emit(job_emitter, "stage_completed", stage="entity_extraction",
                         entities_found=sum(len(v) for v in all_entities.values()))

        await self._emit(job_emitter, "stage_started", stage="embedding")
        decision_map: dict[str, str] = {}
        chunk_count = 0

        for i, chunk in enumerate(chunks):
            safe_text = pii_svc.scan_and_redact(chunk).redacted_text
            embedding = await llm.embed(safe_text[:8000])
            chunk_id = _new_id("CHK")
            await graph.upsert_chunk(
                chunk_id=chunk_id,
                artifact_version_id=artifact_version_id,
                sequence=i,
                text=safe_text[:2000],
                embedding=embedding,
            )
            chunk_count += 1

        for d in all_entities.get("decisions", []):
            embedding = await llm.embed(f"{d.get('title', '')} {d.get('summary', '')}")
            did = await graph.upsert_decision(
                title=d.get("title", "Untitled"),
                summary=d.get("summary", ""),
                confidence=d.get("confidence", 0.8),
                embedding=embedding,
                workspace=request.workspace_id,
                tenant=request.workspace_id,
                confidentiality=request.sensitivity,
            )
            decision_map[d.get("title", "")] = did

        for a in all_entities.get("assumptions", []):
            embedding = await llm.embed(a.get("text", ""))
            related = a.get("related_decision_title")
            await graph.upsert_assumption(
                text=a.get("text", ""),
                risk_level=a.get("risk_level", "medium"),
                decision_id=decision_map.get(related) if related else None,
                embedding=embedding,
                workspace=request.workspace_id,
                tenant=request.workspace_id,
                confidentiality=request.sensitivity,
            )

        await self._emit(job_emitter, "stage_completed", stage="embedding", entities_found=chunk_count)

        await self._emit(job_emitter, "stage_started", stage="graph_upsert")
        await self._emit(job_emitter, "stage_completed", stage="graph_upsert",
                         entities_found=len(decision_map))

        await self._emit(job_emitter, "stage_started", stage="provenance")
        await self._emit(job_emitter, "stage_completed", stage="provenance", entities_found=chunk_count)

        return ArtifactIngestResult(
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            artifact_type=request.artifact_type,
            entities_created={
                "decisions": len(all_entities.get("decisions", [])),
                "assumptions": len(all_entities.get("assumptions", [])),
                "chunks": chunk_count,
            },
            chunk_count=chunk_count,
        )
