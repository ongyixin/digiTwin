"""Ingest meeting transcripts: extract entities, build graph, generate embeddings."""

import json
import os
import re
from typing import Any, Optional

from neo4j import AsyncDriver

from app.config import settings
from app.llm.base import GenerateConfig, LLMProvider
from app.models.api import IngestResponse
from app.services.graph_service import GraphService
from app.services.pii_service import get_pii_service


def _load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), f"../prompts/{name}")
    with open(path) as f:
        return f.read()


def _speaker_turn_chunks(text: str, max_words: int = 2000, overlap_words: int = 200) -> list[str]:
    """Split on speaker-turn boundaries (e.g. 'Alice:') or section headers.
    Falls back to word-count chunking when no speaker labels are detected.
    """
    speaker_pattern = re.compile(r"(?m)^([A-Z][A-Za-z .'-]{1,40}):\s")
    section_pattern = re.compile(r"(?m)^#{1,3}\s+.+$")

    boundaries = [m.start() for m in speaker_pattern.finditer(text)]
    boundaries += [m.start() for m in section_pattern.finditer(text)]
    boundaries = sorted(set(boundaries))

    if len(boundaries) < 2:
        # Fallback: word-count chunking
        words = text.split()
        chunks: list[str] = []
        i = 0
        while i < len(words):
            chunks.append(" ".join(words[i : i + max_words]))
            i += max_words - overlap_words
        return chunks or [text]

    segments: list[str] = []
    for idx, start in enumerate(boundaries):
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(text)
        segments.append(text[start:end].strip())

    # Merge small segments up to max_words
    chunks = []
    current_words: list[str] = []
    for seg in segments:
        seg_words = seg.split()
        if current_words and len(current_words) + len(seg_words) > max_words:
            chunks.append(" ".join(current_words))
            # Keep last overlap_words for context continuity
            current_words = current_words[-overlap_words:] + seg_words
        else:
            current_words.extend(seg_words)
    if current_words:
        chunks.append(" ".join(current_words))

    return chunks or [text]


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


class IngestionService:
    def __init__(self, driver: AsyncDriver, llm: LLMProvider) -> None:
        self.driver = driver
        self.llm = llm
        self.graph = GraphService(driver)

    async def embed(self, text: str) -> Optional[list[float]]:
        return await self.llm.embed(text)

    def _extract_speaker(self, chunk: str) -> str:
        """Extract the first speaker label from a chunk, if any."""
        import re
        m = re.match(r"^([A-Z][A-Za-z .'-]{1,40}):\s", chunk)
        return m.group(1) if m else ""

    async def extract_entities_from_chunk(
        self,
        chunk: str,
        meeting_title: str,
        meeting_date: str,
        participants: str,
        chunk_index: int = 0,
    ) -> dict[str, Any]:
        prompt_template = _load_prompt("extract_decisions.txt")
        prompt = (
            prompt_template
            .replace("{transcript}", chunk)
            .replace("{meeting_title}", meeting_title)
            .replace("{meeting_date}", meeting_date)
            .replace("{participants}", participants)
        )

        raw = await self.llm.generate(
            prompt,
            GenerateConfig(temperature=0.1, response_mime_type="application/json"),
        )
        try:
            result = json.loads(_clean_json(raw or "{}"))
            # Attach provenance metadata to every extracted entity
            speaker = self._extract_speaker(chunk)
            for key in ("decisions", "assumptions", "evidence", "tasks", "approvals"):
                for item in result.get(key, []):
                    item.setdefault("_provenance", {
                        "chunk_index": chunk_index,
                        "speaker": speaker,
                        "excerpt_start": chunk[:120],
                    })
            return result
        except json.JSONDecodeError:
            return {"decisions": [], "assumptions": [], "evidence": [], "tasks": [], "approvals": []}

    async def extract_relationships(self, entities: dict[str, Any]) -> list[dict[str, Any]]:
        prompt_template = _load_prompt("extract_relationships.txt")
        entities_str = json.dumps(entities, indent=2)
        prompt = prompt_template.replace("{entities}", entities_str)

        raw = await self.llm.generate(
            prompt,
            GenerateConfig(temperature=0.1, response_mime_type="application/json"),
        )
        try:
            return json.loads(_clean_json(raw or '{"relationships": []}')).get("relationships", [])
        except json.JSONDecodeError:
            return []

    def _name_to_id(self, name: str) -> str:
        return name.lower().replace(" ", "_").replace("-", "_") if name else ""

    async def ingest_transcript(
        self,
        transcript: str,
        meeting_title: str,
        meeting_date: str,
        participants: list[str],
        workspace: str = "default",
        tenant: str = "default",
        confidentiality: str = "internal",
        job_emitter: Any = None,
        artifact_version_id: Optional[str] = None,
    ) -> IngestResponse:
        from app.services.graph_service import _new_id
        meeting_id = _new_id("M")

        async def _emit(event: str, **kwargs: Any) -> None:
            if job_emitter:
                await job_emitter(event, **kwargs)

        await _emit("stage_started", stage="setup", detail="Resolving participants")

        participant_ids: dict[str, str] = {}
        for name in participants:
            pid = self._name_to_id(name)
            await self.graph.upsert_person(pid, name)
            participant_ids[name] = pid

        await self.graph.upsert_meeting(
            meeting_id, meeting_title, meeting_date, list(participant_ids.values())
        )

        await _emit("stage_completed", stage="setup", entities_found=len(participants))

        # Chunking
        await _emit("stage_started", stage="chunking")
        chunks = _speaker_turn_chunks(transcript, max_words=2000, overlap_words=200)
        await _emit("stage_completed", stage="chunking", entities_found=len(chunks))

        # Entity extraction across chunks
        all_entities: dict[str, list] = {
            "decisions": [], "assumptions": [], "evidence": [], "tasks": [], "approvals": []
        }

        for i, chunk in enumerate(chunks):
            await _emit("stage_started", stage="entity_extraction", detail=f"Chunk {i+1}/{len(chunks)}")
            extracted = await self.extract_entities_from_chunk(
                chunk, meeting_title, meeting_date, ", ".join(participants),
                chunk_index=i,
            )
            for key in all_entities:
                all_entities[key].extend(extracted.get(key, []))
            await _emit(
                "stage_completed",
                stage="entity_extraction",
                entities_found=sum(len(v) for v in extracted.values()),
            )

        # Relationship extraction
        await _emit("stage_started", stage="relationship_extraction")
        relationships = await self.extract_relationships(all_entities)
        await _emit("stage_completed", stage="relationship_extraction", entities_found=len(relationships))

        # Deduplicate by title/text
        seen_titles: set[str] = set()
        unique_entities: dict[str, list] = {k: [] for k in all_entities}
        for key in all_entities:
            for item in all_entities[key]:
                title = item.get("title") or item.get("text", "")
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    unique_entities[key].append(item)

        # Embedding generation
        await _emit("stage_started", stage="embedding")
        decision_map: dict[str, str] = {}
        assumption_map: dict[str, str] = {}
        evidence_map: dict[str, str] = {}
        decision_ids = []
        assumption_ids = []

        # PII pre-scan: classify sensitivity and optionally redact before indexing
        pii_svc = get_pii_service()

        def _pii_scan(text: str) -> tuple[str, str]:
            """Returns (safe_text, sensitivity_level)."""
            result = pii_svc.scan_and_redact(text)
            return result.redacted_text, result.sensitivity_level

        def _effective_confidentiality(base: str, detected_level: str) -> str:
            order = ["public", "internal", "confidential", "restricted"]
            return detected_level if order.index(detected_level) > order.index(base) else base

        for d in unique_entities["decisions"]:
            owner_name = d.get("owner") or ""
            owner_id = participant_ids.get(owner_name, "")
            safe_summary, detected_level = _pii_scan(d.get("summary", ""))
            effective_conf = _effective_confidentiality(confidentiality, detected_level)
            embedding_text = f"{d['title']} {safe_summary}"
            embedding = await self.embed(embedding_text)
            prov = d.get("_provenance", {})
            did = await self.graph.upsert_decision(
                title=d["title"],
                summary=safe_summary,
                confidence=d.get("confidence", 0.8),
                source_excerpt=d.get("source_excerpt", ""),
                owner_id=owner_id,
                meeting_id=meeting_id,
                embedding=embedding,
                provenance_chunk=prov.get("chunk_index"),
                provenance_speaker=prov.get("speaker", ""),
                workspace=workspace, tenant=tenant, confidentiality=effective_conf,
            )
            decision_map[d["title"]] = did
            decision_ids.append(did)

        for a in unique_entities["assumptions"]:
            related = a.get("related_decision_title")
            decision_id = decision_map.get(related) if related else None
            safe_text, detected_level = _pii_scan(a["text"])
            effective_conf = _effective_confidentiality(confidentiality, detected_level)
            embedding = await self.embed(safe_text)
            prov = a.get("_provenance", {})
            aid = await self.graph.upsert_assumption(
                text=safe_text,
                risk_level=a.get("risk_level", "medium"),
                decision_id=decision_id,
                embedding=embedding,
                provenance_chunk=prov.get("chunk_index"),
                provenance_speaker=prov.get("speaker", ""),
                workspace=workspace, tenant=tenant, confidentiality=effective_conf,
            )
            assumption_map[a["text"]] = aid
            assumption_ids.append(aid)

        for e in unique_entities["evidence"]:
            related = e.get("related_decision_title")
            decision_id = decision_map.get(related) if related else None
            safe_summary, detected_level = _pii_scan(e.get("content_summary", ""))
            effective_conf = _effective_confidentiality(confidentiality, detected_level)
            embedding = await self.embed(f"{e['title']} {safe_summary}")
            eid = await self.graph.upsert_evidence(
                title=e["title"],
                content_summary=safe_summary,
                source_type=e.get("source_type", "document"),
                decision_id=decision_id,
                embedding=embedding,
                workspace=workspace, tenant=tenant, confidentiality=effective_conf,
            )
            evidence_map[e["title"]] = eid

        await _emit(
            "stage_completed",
            stage="embedding",
            entities_found=len(decision_ids) + len(assumption_ids) + len(evidence_map),
        )

        # Graph upsert of tasks and approvals
        await _emit("stage_started", stage="graph_upsert")
        for t in unique_entities["tasks"]:
            assignee_name = t.get("assignee") or ""
            assignee_id = participant_ids.get(assignee_name, "")
            related = t.get("related_decision_title")
            decision_id = decision_map.get(related) if related else None
            await self.graph.upsert_task(
                title=t["title"],
                assignee_id=assignee_id,
                due_date=t.get("due_date"),
                decision_id=decision_id,
            )

        for ap in unique_entities["approvals"]:
            assigned_name = ap.get("assigned_to") or ""
            assigned_id = participant_ids.get(assigned_name, "")
            related = ap.get("related_decision_title")
            decision_id = decision_map.get(related)
            if decision_id and assigned_id:
                await self.graph.upsert_approval(
                    decision_id=decision_id,
                    assigned_to_id=assigned_id,
                    required_by=ap.get("required_by", ""),
                )

        # Persist extracted relationships (previously extracted but not applied)
        for rel in relationships:
            try:
                await self.graph.upsert_relationship(
                    from_label=rel.get("from_type", ""),
                    from_title=rel.get("from_title", ""),
                    rel_type=rel.get("relationship", ""),
                    to_label=rel.get("to_type", ""),
                    to_title=rel.get("to_title", ""),
                )
            except Exception:
                pass

        await _emit(
            "stage_completed",
            stage="graph_upsert",
            entities_found=len(unique_entities["tasks"]) + len(unique_entities["approvals"]),
        )

        return IngestResponse(
            meeting_id=meeting_id,
            entities_created={
                "decisions": len(decision_ids),
                "assumptions": len(assumption_ids),
                "evidence": len(evidence_map),
                "tasks": len(unique_entities["tasks"]),
                "approvals": len(unique_entities["approvals"]),
            },
            decision_ids=decision_ids,
            assumption_ids=assumption_ids,
        )
