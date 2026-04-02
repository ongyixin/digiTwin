"""Hybrid retrieval using neo4j-graphrag: vector search + Cypher traversal.

Supports artifact-aware filtering: by type, workspace, sensitivity, and time.
"""

from typing import Any, Optional

from neo4j import AsyncDriver

from app.llm.base import GenerateConfig, LLMProvider
from app.models.api import Citation, QueryResponse


SYNTHESIS_PROMPT = """You are digiTwin, a decision intelligence assistant. Answer the user's question using ONLY the graph context provided below.

Rules:
- Cite specific nodes by their ID in square brackets (e.g., [D-abc123])
- If you cannot answer from the context, say so explicitly
- Explain the reasoning chain when relevant
- Note any permission restrictions if present
- Be concise and factual

Graph Context:
{context}

User Question: {question}

Answer:"""


class RetrievalService:
    def __init__(self, driver: AsyncDriver, llm: LLMProvider) -> None:
        self.driver = driver
        self.llm = llm

    async def embed(self, text: str) -> list[float]:
        result = await self.llm.embed(text)
        return result or []

    async def vector_search(
        self,
        embedding: list[float],
        index_name: str,
        top_k: int = 5,
        allowed_scopes: list[str] | None = None,
        tenant: str | None = None,
    ) -> list[dict[str, Any]]:
        """Vector search with optional post-filter for permission-scoped retrieval."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
                YIELD node, score
                WHERE ($tenant IS NULL OR node.tenant = $tenant OR node.tenant IS NULL)
                OPTIONAL MATCH (node)-[r]->(connected)
                WHERE connected:Assumption OR connected:Evidence OR connected:Person
                      OR connected:Approval OR connected:Task
                RETURN
                    node.id AS id,
                    labels(node)[0] AS label,
                    coalesce(node.title, node.text, '') AS title,
                    coalesce(node.summary, node.content_summary, node.text, node.description, '') AS content,
                    node.workspace AS workspace,
                    node.workspace_id AS workspace_id,
                    node.tenant AS tenant,
                    node.confidentiality AS confidentiality,
                    node.sensitivity AS sensitivity,
                    collect({
                        rel_type: type(r),
                        node_label: labels(connected)[0],
                        node_id: connected.id,
                        node_title: coalesce(connected.title, connected.text, connected.name, '')
                    }) AS connections,
                    score
                ORDER BY score DESC
                """,
                index_name=index_name,
                top_k=top_k,
                embedding=embedding,
                tenant=tenant,
            )
            rows = await result.data()

        # Post-filter by allowed scopes if provided
        if allowed_scopes is not None:
            rows = [
                r for r in rows
                if r.get("workspace") in allowed_scopes
                or r.get("workspace_id") in allowed_scopes
                or r.get("workspace") is None
            ]

        return rows

    async def chunk_search(
        self,
        embedding: list[float],
        top_k: int = 5,
        workspace_id: Optional[str] = None,
        artifact_types: Optional[list[str]] = None,
        sensitivity_ceiling: Optional[str] = None,
        ingested_after: Optional[str] = None,
        ingested_before: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Artifact-aware vector search over Chunk nodes with rich provenance filtering.

        Traverses Chunk -> ArtifactVersion -> Artifact to apply workspace, type,
        sensitivity, and time filters efficiently.
        """
        sensitivity_levels = ["public", "internal", "confidential", "restricted"]
        allowed_sensitivities = (
            sensitivity_levels[: sensitivity_levels.index(sensitivity_ceiling) + 1]
            if sensitivity_ceiling
            else sensitivity_levels
        )

        # Build dynamic WHERE clauses
        where_parts = ["score > 0"]
        if workspace_id:
            where_parts.append("a.workspace_id = $workspace_id")
        if artifact_types:
            where_parts.append("a.type IN $artifact_types")
        if allowed_sensitivities:
            where_parts.append("a.sensitivity IN $allowed_sensitivities")
        if ingested_after:
            where_parts.append("a.ingested_at >= $ingested_after")
        if ingested_before:
            where_parts.append("a.ingested_at <= $ingested_before")

        where_clause = " AND ".join(where_parts)

        try:
            async with self.driver.session() as session:
                result = await session.run(
                    f"""
                    CALL db.index.vector.queryNodes('chunk_embedding', $top_k, $embedding)
                    YIELD node AS c, score
                    MATCH (av:ArtifactVersion {{id: c.artifact_version_id}})<-[:HAS_VERSION]-(a:Artifact)
                    WHERE {where_clause}
                    RETURN c.id AS id,
                           'Chunk' AS label,
                           c.text AS title,
                           c.text AS content,
                           a.type AS artifact_type,
                           a.title AS artifact_title,
                           a.id AS artifact_id,
                           a.workspace_id AS workspace_id,
                           a.sensitivity AS sensitivity,
                           a.ingested_at AS ingested_at,
                           score
                    ORDER BY score DESC
                    LIMIT $top_k
                    """,
                    embedding=embedding,
                    top_k=top_k,
                    workspace_id=workspace_id,
                    artifact_types=artifact_types or [],
                    allowed_sensitivities=allowed_sensitivities,
                    ingested_after=ingested_after or "",
                    ingested_before=ingested_before or "",
                )
                return await result.data()
        except Exception:
            return []

    async def hybrid_search(
        self,
        question: str,
        top_k: int = 5,
        allowed_scopes: list[str] | None = None,
        tenant: str | None = None,
        # Artifact-aware filters
        artifact_types: Optional[list[str]] = None,
        sensitivity_ceiling: Optional[str] = None,
        ingested_after: Optional[str] = None,
        ingested_before: Optional[str] = None,
        include_chunks: bool = True,
    ) -> list[dict[str, Any]]:
        embedding = await self.embed(question)

        all_results: dict[str, dict] = {}

        # Classic entity index search (backward compat)
        entity_indexes = ["decision_embedding", "assumption_embedding", "evidence_embedding"]
        # Add new artifact-type indexes
        if artifact_types:
            if any(t in artifact_types for t in ("policy_doc", "contract")):
                entity_indexes.append("policy_embedding")
            if any(t in artifact_types for t in ("prd", "rfc")):
                entity_indexes.append("requirement_embedding")
            if "github_repo" in artifact_types:
                entity_indexes.append("symbol_embedding")

        for index_name in entity_indexes:
            try:
                results = await self.vector_search(
                    embedding,
                    index_name,
                    top_k=top_k,
                    allowed_scopes=allowed_scopes,
                    tenant=tenant,
                )
                for r in results:
                    if r["id"] and r["id"] not in all_results:
                        all_results[r["id"]] = r
            except Exception:
                pass

        # Artifact-aware chunk search
        if include_chunks:
            chunk_results = await self.chunk_search(
                embedding=embedding,
                top_k=top_k,
                workspace_id=(allowed_scopes[0] if allowed_scopes and len(allowed_scopes) == 1 else None),
                artifact_types=artifact_types,
                sensitivity_ceiling=sensitivity_ceiling,
                ingested_after=ingested_after,
                ingested_before=ingested_before,
            )
            for r in chunk_results:
                if r["id"] and r["id"] not in all_results:
                    all_results[r["id"]] = r

        sorted_results = sorted(all_results.values(), key=lambda x: x.get("score", 0), reverse=True)
        return sorted_results[:top_k]

    def _format_context(self, results: list[dict[str, Any]]) -> str:
        parts = []
        for r in results:
            label = r.get("label", "Node")
            connections = r.get("connections") or []
            conn_str = ", ".join(
                f"{c['rel_type']} -> [{c['node_label']}:{c['node_id']}] {c['node_title']}"
                for c in connections if c.get("node_id")
            )
            artifact_info = ""
            if r.get("artifact_title"):
                artifact_info = f"\n  Source artifact: {r['artifact_title']} ({r.get('artifact_type', '')})"
            parts.append(
                f"[{label}:{r['id']}] {r.get('title', '')}"
                f"{artifact_info}\n"
                f"  Content: {r.get('content', '')}\n"
                f"  Connected to: {conn_str or 'nothing'}"
            )
        return "\n\n".join(parts)

    async def query(
        self,
        question: str,
        user_id: str,
        top_k: int = 5,
        allowed_scopes: list[str] | None = None,
        tenant: str | None = None,
        artifact_types: Optional[list[str]] = None,
        sensitivity_ceiling: Optional[str] = None,
        ingested_after: Optional[str] = None,
        ingested_before: Optional[str] = None,
    ) -> QueryResponse:
        results = await self.hybrid_search(
            question,
            top_k=top_k,
            allowed_scopes=allowed_scopes,
            tenant=tenant,
            artifact_types=artifact_types,
            sensitivity_ceiling=sensitivity_ceiling,
            ingested_after=ingested_after,
            ingested_before=ingested_before,
        )

        if not results:
            return QueryResponse(
                answer="I couldn't find relevant information in the decision graph to answer your question.",
                citations=[],
            )

        context = self._format_context(results)
        prompt = SYNTHESIS_PROMPT.format(context=context, question=question)

        answer = await self.llm.generate(prompt, GenerateConfig(temperature=0.2))

        citations = [
            Citation(
                id=r["id"],
                label=r.get("label", "Node"),
                title=r.get("title", ""),
                excerpt=r.get("content", "")[:200] if r.get("content") else None,
            )
            for r in results
            if r.get("id") and (f"[{r['id']}]" in answer or f"[{r.get('label', '')}:{r['id']}]" in answer)
        ]

        return QueryResponse(
            answer=answer,
            citations=citations,
            graph_context=results,
        )
