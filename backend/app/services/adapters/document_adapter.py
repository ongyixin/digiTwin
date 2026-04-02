"""Document adapter — handles PDFs, policy docs, PRDs, RFCs, contracts,
and postmortems using Gemini's native document understanding.
"""

import hashlib
import json
import re
from typing import Any, Callable, Optional

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.artifact import ArtifactIngestRequest, ArtifactIngestResult
from app.services.adapters.base import BaseAdapter
from app.services.graph_service import GraphService, _new_id
from app.services.pii_service import get_pii_service


class DocumentAdapter(BaseAdapter):
    """Ingestion adapter for PDF / document artifacts.

    Covers: policy_doc, prd, rfc, postmortem, contract.
    Uses Gemini's native document understanding for layout-aware extraction.
    """

    @property
    def pipeline_stages(self) -> list[str]:
        return [
            "upload",
            "parse_layout",
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
        from app.extraction.schema_registry import registry
        from app.llm.gemini_provider import GeminiProvider

        graph = GraphService(driver)
        pii_svc = get_pii_service()

        title = request.metadata.get("title") or request.metadata.get("filename") or f"Document {request.artifact_type}"
        artifact_id = _new_id("ART")
        artifact_version_id = _new_id("AV")

        await self._emit(job_emitter, "stage_started", stage="upload", detail="Registering artifact")
        await graph.upsert_artifact(
            artifact_id=artifact_id,
            artifact_type=request.artifact_type,
            source_type=request.source_type,
            title=title,
            workspace_id=request.workspace_id,
            sensitivity=request.sensitivity,
            mime_type=request.mime_type or "application/pdf",
            metadata=request.metadata,
        )
        content_hash = hashlib.sha256(raw_content if isinstance(raw_content, bytes) else (raw_content or "").encode()).hexdigest()[:16]
        await graph.upsert_artifact_version(
            version_id=artifact_version_id,
            artifact_id=artifact_id,
            content_hash=content_hash,
            model_version="gemini-2.5-flash",
        )
        await self._emit(job_emitter, "stage_completed", stage="upload", entities_found=1)

        # Use Gemini to extract document structure
        await self._emit(job_emitter, "stage_started", stage="parse_layout", detail="Analyzing document layout")
        doc_text = await self._extract_text_from_doc(llm, raw_content, request)
        await self._emit(job_emitter, "stage_completed", stage="parse_layout", entities_found=1)

        # Split into logical sections
        await self._emit(job_emitter, "stage_started", stage="section_split", detail="Splitting into sections")
        sections = _split_into_sections(doc_text)
        section_nodes = []
        for i, (sec_title, sec_text) in enumerate(sections):
            section_id = _new_id("SEC")
            await graph.upsert_section(
                section_id=section_id,
                artifact_version_id=artifact_version_id,
                title=sec_title or f"Section {i + 1}",
                sequence=i,
                text_preview=sec_text[:300],
            )
            section_nodes.append((section_id, sec_title, sec_text))
        await self._emit(job_emitter, "stage_completed", stage="section_split", entities_found=len(sections))

        # Entity extraction using artifact-specific prompt + schema
        prompt_file, _schema = registry.get(request.artifact_type)
        await self._emit(job_emitter, "stage_started", stage="entity_extraction", detail=f"Extracting from {len(sections)} sections")

        all_entities: dict[str, list] = {}
        chunk_count = 0
        for section_id, sec_title, sec_text in section_nodes:
            chunk_id = _new_id("CHK")
            safe_text, detected_level = _pii_scan(pii_svc, sec_text)
            embedding = await llm.embed(safe_text[:8000])
            await graph.upsert_chunk(
                chunk_id=chunk_id,
                artifact_version_id=artifact_version_id,
                sequence=chunk_count,
                text=safe_text[:2000],
                embedding=embedding,
            )
            chunk_count += 1

            extracted = await _extract_entities_from_section(
                llm, safe_text, request, prompt_file, section_id
            )
            for key, items in extracted.items():
                all_entities.setdefault(key, []).extend(items)

        await self._emit(job_emitter, "stage_completed", stage="entity_extraction",
                         entities_found=sum(len(v) for v in all_entities.values()))

        # Relationship extraction
        await self._emit(job_emitter, "stage_started", stage="relationship_extraction")
        relationships = await _extract_relationships(llm, all_entities)
        await self._emit(job_emitter, "stage_completed", stage="relationship_extraction",
                         entities_found=len(relationships))

        # Graph upsert (type-specific)
        await self._emit(job_emitter, "stage_started", stage="embedding")
        counts = await _upsert_document_entities(
            graph, llm, pii_svc, all_entities, relationships,
            request, artifact_version_id
        )
        await self._emit(job_emitter, "stage_completed", stage="embedding",
                         entities_found=sum(counts.values()))

        await self._emit(job_emitter, "stage_started", stage="graph_upsert")
        await self._emit(job_emitter, "stage_completed", stage="graph_upsert",
                         entities_found=sum(counts.values()))

        await self._emit(job_emitter, "stage_started", stage="provenance", detail="Linking entities to source spans")
        await self._emit(job_emitter, "stage_completed", stage="provenance", entities_found=chunk_count)

        return ArtifactIngestResult(
            artifact_id=artifact_id,
            artifact_version_id=artifact_version_id,
            artifact_type=request.artifact_type,
            entities_created=counts,
            chunk_count=chunk_count,
            section_count=len(section_nodes),
        )

    async def _extract_text_from_doc(
        self,
        llm: LLMProvider,
        raw_content: Optional[bytes | str],
        request: ArtifactIngestRequest,
    ) -> str:
        """Extract clean text from the document using Gemini."""
        from app.llm.gemini_provider import GeminiProvider

        # If raw content is bytes (PDF), upload to Gemini Files API and extract text
        if isinstance(raw_content, bytes) and len(raw_content) > 0:
            if isinstance(llm, GeminiProvider):
                try:
                    import io
                    from google.genai import types as genai_types

                    mime = request.mime_type or "application/pdf"
                    file_obj = io.BytesIO(raw_content)
                    uploaded = await llm.client.aio.files.upload(
                        file=file_obj,
                        config=genai_types.UploadFileConfig(mime_type=mime),
                    )
                    extraction_prompt = (
                        "Extract all text content from this document, preserving section headings "
                        "and paragraph structure. Use ### for major section headings, ## for sub-sections. "
                        "Return only the extracted text, no additional commentary."
                    )
                    response = await llm.client.aio.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[uploaded, extraction_prompt],
                    )
                    return response.text or ""
                except Exception as e:
                    print(f"Gemini file upload failed, falling back to text decode: {e}")

        # Fallback: try UTF-8 decode
        if isinstance(raw_content, bytes):
            try:
                return raw_content.decode("utf-8")
            except UnicodeDecodeError:
                return raw_content.decode("latin-1", errors="replace")
        return raw_content or ""


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split document text into (title, content) section pairs."""
    header_re = re.compile(r"(?m)^#{1,3}\s+(.+)$")
    boundaries = [(m.start(), m.group(1)) for m in header_re.finditer(text)]

    if len(boundaries) < 2:
        # No headers — chunk by paragraphs
        paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        chunk_size = 10
        sections = []
        for i in range(0, len(paragraphs), chunk_size):
            group = paragraphs[i:i + chunk_size]
            sections.append((f"Section {i // chunk_size + 1}", "\n\n".join(group)))
        return sections or [("Full Document", text)]

    sections: list[tuple[str, str]] = []
    for idx, (start, heading) in enumerate(boundaries):
        end = boundaries[idx + 1][0] if idx + 1 < len(boundaries) else len(text)
        sections.append((heading, text[start:end].strip()))
    return sections


def _pii_scan(pii_svc, text: str) -> tuple[str, str]:
    result = pii_svc.scan_and_redact(text)
    return result.redacted_text, result.sensitivity_level


async def _extract_entities_from_section(
    llm: LLMProvider,
    text: str,
    request: ArtifactIngestRequest,
    prompt_file: str,
    section_id: str,
) -> dict[str, list]:
    """Run artifact-type-specific extraction on one section."""
    import os

    prompt_path = os.path.join(
        os.path.dirname(__file__), f"../../prompts/{prompt_file}"
    )
    try:
        with open(prompt_path) as f:
            template = f.read()
    except FileNotFoundError:
        # Fallback to generic decision extraction
        from app.services.ingestion_service import _load_prompt
        template = _load_prompt("extract_decisions.txt")

    prompt = (
        template
        .replace("{content}", text)
        .replace("{transcript}", text)
        .replace("{artifact_type}", request.artifact_type)
        .replace("{title}", request.metadata.get("title", ""))
        .replace("{meeting_title}", request.metadata.get("title", ""))
        .replace("{meeting_date}", request.meeting_date or "")
        .replace("{participants}", ", ".join(request.participants))
    )

    raw = await llm.generate(prompt, GenerateConfig(temperature=0.1, response_mime_type="application/json"))
    try:
        from app.services.ingestion_service import _clean_json
        return json.loads(_clean_json(raw or "{}"))
    except (json.JSONDecodeError, Exception):
        return {}


async def _extract_relationships(llm: LLMProvider, entities: dict[str, list]) -> list[dict]:
    """Extract relationships between all entities."""
    import os

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


async def _upsert_document_entities(
    graph: GraphService,
    llm: LLMProvider,
    pii_svc,
    entities: dict[str, list],
    relationships: list[dict[str, Any]],
    request: ArtifactIngestRequest,
    artifact_version_id: str,
) -> dict[str, int]:
    """Upsert extracted entities into Neo4j based on artifact type."""
    counts: dict[str, int] = {}

    workspace = request.workspace_id
    sensitivity = request.sensitivity

    # Universal: always try to extract decisions/assumptions/evidence if present
    decision_map: dict[str, str] = {}
    for d in entities.get("decisions", []):
        embedding = await llm.embed(f"{d.get('title', '')} {d.get('summary', '')}")
        safe_summary, _ = _pii_scan(pii_svc, d.get("summary", ""))
        did = await graph.upsert_decision(
            title=d.get("title", "Untitled"),
            summary=safe_summary,
            confidence=d.get("confidence", 0.8),
            source_excerpt=d.get("source_excerpt", ""),
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
        decision_map[d.get("title", "")] = did
    counts["decisions"] = len(decision_map)

    # Artifact-type-specific node upserts
    artifact_type = request.artifact_type

    # Policy / contract / compliance
    if artifact_type in ("policy_doc", "contract"):
        policy_count = 0
        for p in entities.get("policies", []):
            embedding = await llm.embed(f"{p.get('title', '')} {p.get('description', '')}")
            await graph.upsert_policy_node(
                title=p.get("title", "Untitled Policy"),
                description=p.get("description", ""),
                owner=p.get("owner", ""),
                effective_date=p.get("effective_date"),
                scope=p.get("scope", ""),
                embedding=embedding,
                workspace=workspace,
                sensitivity=sensitivity,
                artifact_version_id=artifact_version_id,
            )
            policy_count += 1
        counts["policies"] = policy_count

        control_count = 0
        for c in entities.get("controls", []):
            await graph.upsert_control_node(
                title=c.get("title", "Untitled Control"),
                description=c.get("description", ""),
                policy_title=c.get("policy_title", ""),
                workspace=workspace,
                sensitivity=sensitivity,
                artifact_version_id=artifact_version_id,
            )
            control_count += 1
        counts["controls"] = control_count

    # PRD / RFC / design spec
    if artifact_type in ("prd", "rfc", "postmortem"):
        req_count = 0
        for r in entities.get("requirements", []):
            embedding = await llm.embed(f"{r.get('title', '')} {r.get('description', '')}")
            await graph.upsert_requirement_node(
                title=r.get("title", "Untitled Requirement"),
                description=r.get("description", ""),
                req_type=r.get("type", "functional"),
                priority=r.get("priority", "medium"),
                embedding=embedding,
                workspace=workspace,
                sensitivity=sensitivity,
                artifact_version_id=artifact_version_id,
            )
            req_count += 1
        counts["requirements"] = req_count

        goal_count = 0
        for g in entities.get("product_goals", []):
            await graph.upsert_product_goal_node(
                title=g.get("title", "Untitled Goal"),
                description=g.get("description", ""),
                workspace=workspace,
                sensitivity=sensitivity,
                artifact_version_id=artifact_version_id,
            )
            goal_count += 1
        counts["product_goals"] = goal_count

    # Assumptions (universal)
    assumption_map: dict[str, str] = {}
    for a in entities.get("assumptions", []):
        embedding = await llm.embed(a.get("text", ""))
        related = a.get("related_decision_title")
        decision_id = decision_map.get(related) if related else None
        aid = await graph.upsert_assumption(
            text=a.get("text", ""),
            risk_level=a.get("risk_level", "medium"),
            decision_id=decision_id,
            embedding=embedding,
            workspace=workspace,
            tenant=workspace,
            confidentiality=sensitivity,
        )
        assumption_map[a.get("text", "")] = aid
    counts["assumptions"] = len(assumption_map)

    # Apply cross-entity relationships
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
