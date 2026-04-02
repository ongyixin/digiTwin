"""Core Neo4j read/write operations."""

import uuid
from datetime import datetime
from typing import Any, Optional

from neo4j import AsyncDriver

from app.models.graph import GraphEdge, GraphNode, GraphSubgraph


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class GraphService:
    def __init__(self, driver: AsyncDriver):
        self.driver = driver

    # ------------------------------------------------------------------
    # Upsert helpers
    # ------------------------------------------------------------------

    async def upsert_person(self, person_id: str, name: str, email: str = "", department: str = "") -> str:
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (p:Person {id: $id})
                SET p.name = $name, p.email = $email, p.department = $department
                """,
                id=person_id, name=name, email=email, department=department,
            )
        return person_id

    async def upsert_meeting(self, meeting_id: str, title: str, date: str, participants: list[str]) -> str:
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (m:Meeting {id: $id})
                SET m.title = $title, m.date = $date, m.participants = $participants
                """,
                id=meeting_id, title=title, date=date, participants=participants,
            )
        return meeting_id

    async def upsert_decision(
        self,
        title: str,
        summary: str,
        status: str = "proposed",
        confidence: float = 0.8,
        source_excerpt: str = "",
        owner_id: str = "",
        meeting_id: str = "",
        embedding: Optional[list[float]] = None,
        decision_id: Optional[str] = None,
        workspace: str = "default",
        tenant: str = "default",
        confidentiality: str = "internal",
        provenance_chunk: Optional[int] = None,
        provenance_speaker: str = "",
    ) -> str:
        did = decision_id or _new_id("D")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (d:Decision {id: $id})
                SET d.title = $title,
                    d.summary = $summary,
                    d.status = $status,
                    d.confidence = $confidence,
                    d.source_excerpt = $source_excerpt,
                    d.created_at = $created_at,
                    d.embedding = $embedding,
                    d.workspace = $workspace,
                    d.tenant = $tenant,
                    d.confidentiality = $confidentiality,
                    d.provenance_chunk = $provenance_chunk,
                    d.provenance_speaker = $provenance_speaker
                """,
                id=did, title=title, summary=summary, status=status,
                confidence=confidence, source_excerpt=source_excerpt,
                created_at=datetime.utcnow().isoformat(),
                embedding=embedding,
                workspace=workspace, tenant=tenant, confidentiality=confidentiality,
                provenance_chunk=provenance_chunk, provenance_speaker=provenance_speaker,
            )
            if owner_id:
                await session.run(
                    """
                    MATCH (d:Decision {id: $did}), (p:Person {id: $pid})
                    MERGE (p)-[:MADE_DECISION]->(d)
                    """,
                    did=did, pid=owner_id,
                )
            if meeting_id:
                await session.run(
                    """
                    MATCH (d:Decision {id: $did}), (m:Meeting {id: $mid})
                    MERGE (m)-[:PRODUCED]->(d)
                    """,
                    did=did, mid=meeting_id,
                )
        return did

    async def upsert_assumption(
        self,
        text: str,
        status: str = "active",
        risk_level: str = "medium",
        decision_id: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        assumption_id: Optional[str] = None,
        workspace: str = "default",
        tenant: str = "default",
        confidentiality: str = "internal",
        provenance_chunk: Optional[int] = None,
        provenance_speaker: str = "",
    ) -> str:
        aid = assumption_id or _new_id("A")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (a:Assumption {id: $id})
                SET a.text = $text, a.status = $status,
                    a.risk_level = $risk_level, a.embedding = $embedding,
                    a.workspace = $workspace, a.tenant = $tenant,
                    a.confidentiality = $confidentiality,
                    a.created_at = $created_at,
                    a.provenance_chunk = $provenance_chunk,
                    a.provenance_speaker = $provenance_speaker
                """,
                id=aid, text=text, status=status, risk_level=risk_level, embedding=embedding,
                workspace=workspace, tenant=tenant, confidentiality=confidentiality,
                created_at=datetime.utcnow().isoformat(),
                provenance_chunk=provenance_chunk, provenance_speaker=provenance_speaker,
            )
            if decision_id:
                await session.run(
                    """
                    MATCH (d:Decision {id: $did}), (a:Assumption {id: $aid})
                    MERGE (d)-[:DEPENDS_ON]->(a)
                    """,
                    did=decision_id, aid=aid,
                )
        return aid

    async def upsert_evidence(
        self,
        title: str,
        content_summary: str,
        source_type: str = "document",
        source_url: str = "",
        decision_id: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        evidence_id: Optional[str] = None,
        workspace: str = "default",
        tenant: str = "default",
        confidentiality: str = "internal",
    ) -> str:
        eid = evidence_id or _new_id("E")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (e:Evidence {id: $id})
                SET e.title = $title, e.content_summary = $content_summary,
                    e.source_type = $source_type, e.source_url = $source_url,
                    e.embedding = $embedding,
                    e.workspace = $workspace, e.tenant = $tenant,
                    e.confidentiality = $confidentiality,
                    e.created_at = $created_at
                """,
                id=eid, title=title, content_summary=content_summary,
                source_type=source_type, source_url=source_url, embedding=embedding,
                workspace=workspace, tenant=tenant, confidentiality=confidentiality,
                created_at=datetime.utcnow().isoformat(),
            )
            if decision_id:
                await session.run(
                    """
                    MATCH (d:Decision {id: $did}), (e:Evidence {id: $eid})
                    MERGE (d)-[:SUPPORTED_BY]->(e)
                    """,
                    did=decision_id, eid=eid,
                )
        return eid

    async def upsert_task(
        self,
        title: str,
        status: str = "open",
        assignee_id: str = "",
        due_date: Optional[str] = None,
        decision_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> str:
        tid = task_id or _new_id("T")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (t:Task {id: $id})
                SET t.title = $title, t.status = $status,
                    t.assignee_id = $assignee_id, t.due_date = $due_date,
                    t.created_at = coalesce(t.created_at, $created_at)
                """,
                id=tid, title=title, status=status,
                assignee_id=assignee_id, due_date=due_date,
                created_at=datetime.utcnow().isoformat(),
            )
            if decision_id:
                await session.run(
                    """
                    MATCH (d:Decision {id: $did}), (t:Task {id: $tid})
                    MERGE (t)-[:BLOCKS]->(d)
                    """,
                    did=decision_id, tid=tid,
                )
            if assignee_id:
                await session.run(
                    """
                    MATCH (t:Task {id: $tid}), (p:Person {id: $pid})
                    MERGE (t)-[:OWNED_BY]->(p)
                    """,
                    tid=tid, pid=assignee_id,
                )
        return tid

    async def upsert_approval(
        self,
        decision_id: str,
        assigned_to_id: str,
        required_by: str = "",
        due_date: Optional[str] = None,
        status: str = "pending",
        approval_id: Optional[str] = None,
    ) -> str:
        apid = approval_id or _new_id("AP")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (ap:Approval {id: $id})
                SET ap.status = $status, ap.required_by = $required_by, ap.due_date = $due_date,
                    ap.created_at = coalesce(ap.created_at, $created_at)
                """,
                id=apid, status=status, required_by=required_by, due_date=due_date,
                created_at=datetime.utcnow().isoformat(),
            )
            await session.run(
                """
                MATCH (ap:Approval {id: $apid}), (d:Decision {id: $did})
                MERGE (ap)-[:FOR_DECISION]->(d)
                """,
                apid=apid, did=decision_id,
            )
            await session.run(
                """
                MATCH (ap:Approval {id: $apid}), (p:Person {id: $pid})
                MERGE (ap)-[:ASSIGNED_TO]->(p)
                """,
                apid=apid, pid=assigned_to_id,
            )
        return apid

    async def create_agent_action(
        self,
        action_type: str,
        initiated_by: str,
        policy_path: list[str],
        resource_id: Optional[str] = None,
        status: str = "allowed",
    ) -> str:
        action_id = _new_id("AA")
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (aa:AgentAction {
                    id: $id,
                    action_type: $action_type,
                    initiated_by: $initiated_by,
                    executed_by_agent: 'digiTwin',
                    policy_path: $policy_path,
                    status: $status,
                    timestamp: $timestamp
                })
                """,
                id=action_id, action_type=action_type, initiated_by=initiated_by,
                policy_path=policy_path, status=status,
                timestamp=datetime.utcnow().isoformat(),
            )
        return action_id

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_all_decisions(self, limit: int = 50) -> list[dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (d:Decision)
                OPTIONAL MATCH (p:Person)-[:MADE_DECISION]->(d)
                OPTIONAL MATCH (m:Meeting)-[:PRODUCED]->(d)
                RETURN d, p.name AS owner_name, m.title AS meeting_title
                ORDER BY d.created_at DESC LIMIT $limit
                """,
                limit=limit,
            )
            records = await result.data()
        return [
            {
                **{k: v for k, v in dict(r["d"]).items() if k != "embedding"},
                "owner_name": r["owner_name"],
                "meeting_title": r["meeting_title"],
            }
            for r in records
        ]

    async def get_decision_lineage(self, decision_id: str) -> GraphSubgraph:
        _SKIP_LABELS = {"Chunk", "ArtifactVersion", "SourceSpan", "Symbol", "SpeakerTurn"}

        nodes: dict[str, GraphNode] = {}
        edges_set: set[tuple[str, str]] = set()
        edges: list[GraphEdge] = []

        def _add_node(raw: dict, label_list: list[str]) -> str | None:
            if not raw or not raw.get("id"):
                return None
            nid = raw["id"]
            label = next((l for l in label_list if l not in _SKIP_LABELS), "Node")
            if nid not in nodes:
                nodes[nid] = GraphNode(
                    id=nid,
                    label=label,
                    properties={k: v for k, v in raw.items() if k != "embedding"},
                )
            return nid

        def _add_edge(src: str, tgt: str, rel: str) -> None:
            key = (src, tgt)
            if key not in edges_set:
                edges_set.add(key)
                edges.append(GraphEdge(source=src, target=tgt, type=rel or "RELATED"))

        async with self.driver.session() as session:
            # ── 1. Outgoing from decision (2 hops) ──────────────────────────
            r1 = await session.run(
                """
                MATCH (d:Decision {id: $id})
                OPTIONAL MATCH (d)-[r1]->(n1)
                OPTIONAL MATCH (n1)-[r2]->(n2)
                RETURN d,
                       collect(DISTINCT {
                           rel: type(r1), node: n1, labels1: labels(n1),
                           rel2: type(r2), node2: n2, labels2: labels(n2)
                       }) AS context
                """,
                id=decision_id,
            )
            rows1 = await r1.data()

            if not rows1:
                return GraphSubgraph(nodes=[], edges=[])

            row = rows1[0]
            d = row["d"]
            _add_node(d, ["Decision"])

            for ctx in row.get("context", []) or []:
                n1 = ctx.get("node")
                labels1 = ctx.get("labels1") or []
                if set(labels1) & _SKIP_LABELS:
                    continue
                nid = _add_node(n1, labels1)
                if nid:
                    _add_edge(d["id"], nid, ctx.get("rel", "RELATED"))
                    n2 = ctx.get("node2")
                    labels2 = ctx.get("labels2") or []
                    if not (set(labels2) & _SKIP_LABELS):
                        n2id = _add_node(n2, labels2)
                        if n2id and ctx.get("rel2"):
                            _add_edge(nid, n2id, ctx["rel2"])

            # ── 2. Nodes pointing INTO the decision ──────────────────────────
            r2 = await session.run(
                """
                MATCH (n_in)-[r_in]->(d:Decision {id: $id})
                WHERE NONE(lbl IN labels(n_in) WHERE lbl IN ['Chunk','ArtifactVersion','SourceSpan','Symbol','SpeakerTurn'])
                RETURN type(r_in) AS rel, n_in, labels(n_in) AS lbls
                """,
                id=decision_id,
            )
            rows2 = await r2.data()
            incoming_ids: list[str] = []
            for row2 in rows2:
                nin = row2.get("n_in")
                nin_id = _add_node(nin, row2.get("lbls") or [])
                if nin_id:
                    _add_edge(nin_id, decision_id, row2.get("rel", "RELATED"))
                    incoming_ids.append(nin_id)

            # ── 3. Outgoing from incoming nodes (e.g. RC→Plan→Action) ────────
            if incoming_ids:
                r3 = await session.run(
                    """
                    UNWIND $ids AS nid
                    MATCH (n1 {id: nid})-[r1]->(n2)
                    WHERE NONE(lbl IN labels(n2) WHERE lbl IN ['Chunk','ArtifactVersion','SourceSpan','Symbol','SpeakerTurn'])
                      AND NOT n2:Decision
                    OPTIONAL MATCH (n2)-[r2]->(n3)
                    WHERE NONE(lbl IN labels(n3) WHERE lbl IN ['Chunk','ArtifactVersion','SourceSpan','Symbol','SpeakerTurn'])
                      AND NOT n3:Decision
                    RETURN n1.id AS src1, type(r1) AS rel1, n2, labels(n2) AS lbls2,
                           type(r2) AS rel2, n3, labels(n3) AS lbls3
                    """,
                    ids=incoming_ids,
                )
                rows3 = await r3.data()
                for row3 in rows3:
                    src1 = row3["src1"]
                    n2id = _add_node(row3.get("n2"), row3.get("lbls2") or [])
                    if n2id:
                        _add_edge(src1, n2id, row3.get("rel1", "RELATED"))
                        n3id = _add_node(row3.get("n3"), row3.get("lbls3") or [])
                        if n3id and row3.get("rel2"):
                            _add_edge(n2id, n3id, row3["rel2"])

        return GraphSubgraph(nodes=list(nodes.values()), edges=edges)

    async def get_graph_overview(self, workspace: str = "default") -> GraphSubgraph:
        """Return all primary entity nodes and their relationships for the full dependency map."""
        _MAIN_LABELS = {
            "Decision", "ResolutionCase", "Meeting", "Person",
            "Assumption", "Evidence", "Task", "Approval", "ProposedAction",
        }
        _SKIP_LABELS = {"Chunk", "ArtifactVersion", "SourceSpan", "Symbol", "SpeakerTurn", "Role", "Permission", "Resource", "Scope"}

        nodes: dict[str, GraphNode] = {}
        edges_set: set[tuple[str, str]] = set()
        edges: list[GraphEdge] = []

        def _add_node(raw: dict | None, label_list: list[str]) -> str | None:
            if not raw or not raw.get("id"):
                return None
            nid = raw["id"]
            label = next((l for l in label_list if l not in _SKIP_LABELS), "Node")
            if nid not in nodes:
                nodes[nid] = GraphNode(
                    id=nid, label=label,
                    properties={k: v for k, v in raw.items() if k != "embedding"},
                )
            return nid

        def _add_edge(src: str, tgt: str, rel: str) -> None:
            key = (src, tgt)
            if key not in edges_set:
                edges_set.add(key)
                edges.append(GraphEdge(source=src, target=tgt, type=rel or "RELATED"))

        async with self.driver.session() as session:
            # Main entity nodes + their direct relationships to other main entities
            r1 = await session.run(
                """
                MATCH (n)
                WHERE (n:Decision OR n:ResolutionCase OR n:Meeting OR n:Person
                    OR n:Assumption OR n:Evidence OR n:Task OR n:Approval)
                AND (n.workspace = $ws OR n.workspace_id = $ws
                     OR (n.workspace IS NULL AND n.workspace_id IS NULL))
                OPTIONAL MATCH (n)-[r]->(m)
                WHERE (m:Decision OR m:ResolutionCase OR m:Meeting OR m:Assumption
                    OR m:Evidence OR m:Task OR m:Approval OR m:Person)
                  AND NOT (n:Person AND type(r) IN ['HAS_ROLE','GRANTS','ON_RESOURCE'])
                RETURN n, labels(n) AS lbls,
                       collect(DISTINCT {
                           rel: type(r), target: m, tlbls: labels(m)
                       }) AS out_edges
                """,
                ws=workspace,
            )
            rows1 = await r1.data()

            for row in rows1:
                nid = _add_node(row.get("n"), row.get("lbls") or [])
                if not nid:
                    continue
                for ed in (row.get("out_edges") or []):
                    target = ed.get("target")
                    tlbls = ed.get("tlbls") or []
                    if set(tlbls) & _SKIP_LABELS:
                        continue
                    tid = _add_node(target, tlbls)
                    if tid:
                        _add_edge(nid, tid, ed.get("rel", "RELATED"))

            # ProposedActions via ResolutionCase → ResolutionPlan → ProposedAction
            r2 = await session.run(
                """
                MATCH (rc:ResolutionCase)-[:HAS_PLAN]->(rp:ResolutionPlan)-[:PROPOSES]->(pa:ProposedAction)
                WHERE rc.workspace_id = $ws OR rc.workspace_id IS NULL
                RETURN rc.id AS rc_id, pa, labels(pa) AS pa_lbls
                """,
                ws=workspace,
            )
            rows2 = await r2.data()
            for row in rows2:
                pa_id = _add_node(row.get("pa"), row.get("pa_lbls") or [])
                rc_id = row.get("rc_id")
                if pa_id and rc_id and rc_id in nodes:
                    _add_edge(rc_id, pa_id, "PROPOSES")

        return GraphSubgraph(nodes=list(nodes.values()), edges=edges)

    async def create_review_task(
        self,
        original_action_id: str,
        action_type: str,
        initiated_by: str,
        reason: str,
    ) -> str:
        tid = _new_id("RT")
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (rt:ReviewTask {
                    id: $id,
                    original_action_id: $original_action_id,
                    action_type: $action_type,
                    initiated_by: $initiated_by,
                    reason: $reason,
                    status: 'pending',
                    created_at: $created_at
                })
                """,
                id=tid,
                original_action_id=original_action_id,
                action_type=action_type,
                initiated_by=initiated_by,
                reason=reason,
                created_at=datetime.utcnow().isoformat(),
            )
        return tid

    async def get_review_inbox(self) -> list[dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (rt:ReviewTask {status: 'pending'})
                RETURN rt ORDER BY rt.created_at DESC LIMIT 50
                """
            )
            rows = await result.data()
        return [dict(r["rt"]) for r in rows]

    async def resolve_review_task(self, task_id: str, approved: bool, reviewer_id: str) -> None:
        status = "approved" if approved else "rejected"
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (rt:ReviewTask {id: $id})
                SET rt.status = $status, rt.reviewer_id = $reviewer_id,
                    rt.resolved_at = $resolved_at
                """,
                id=task_id,
                status=status,
                reviewer_id=reviewer_id,
                resolved_at=datetime.utcnow().isoformat(),
            )

    async def get_pending_approvals(self) -> list[dict[str, Any]]:
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (ap:Approval {status: 'pending'})-[:FOR_DECISION]->(d:Decision)
                MATCH (ap)-[:ASSIGNED_TO]->(p:Person)
                RETURN ap, d.title AS decision_title, d.id AS decision_id,
                       p.id AS person_id, p.name AS person_name, p.email AS person_email
                ORDER BY ap.due_date ASC
                """
            )
            return await result.data()

    # ------------------------------------------------------------------
    # Artifact provenance layer
    # ------------------------------------------------------------------

    async def upsert_artifact(
        self,
        artifact_id: str,
        artifact_type: str,
        source_type: str,
        title: str,
        workspace_id: str,
        sensitivity: str,
        mime_type: str = "",
        metadata: Optional[dict] = None,
        status: str = "ingested",
    ) -> str:
        import json as _json
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (a:Artifact {id: $id})
                SET a.type = $type,
                    a.source_type = $source_type,
                    a.title = $title,
                    a.workspace_id = $workspace_id,
                    a.sensitivity = $sensitivity,
                    a.mime_type = $mime_type,
                    a.metadata = $metadata,
                    a.status = $status,
                    a.ingested_at = coalesce(a.ingested_at, $ingested_at)
                """,
                id=artifact_id,
                type=artifact_type,
                source_type=source_type,
                title=title,
                workspace_id=workspace_id,
                sensitivity=sensitivity,
                mime_type=mime_type,
                metadata=_json.dumps(metadata or {}),
                status=status,
                ingested_at=datetime.utcnow().isoformat(),
            )
        return artifact_id

    async def upsert_artifact_version(
        self,
        version_id: str,
        artifact_id: str,
        content_hash: str,
        model_version: str = "",
    ) -> str:
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (av:ArtifactVersion {id: $id})
                SET av.artifact_id = $artifact_id,
                    av.content_hash = $content_hash,
                    av.model_version = $model_version,
                    av.ingested_at = coalesce(av.ingested_at, $ingested_at)
                WITH av
                MATCH (a:Artifact {id: $artifact_id})
                MERGE (a)-[:HAS_VERSION]->(av)
                """,
                id=version_id,
                artifact_id=artifact_id,
                content_hash=content_hash,
                model_version=model_version,
                ingested_at=datetime.utcnow().isoformat(),
            )
        return version_id

    async def upsert_chunk(
        self,
        chunk_id: str,
        artifact_version_id: str,
        sequence: int,
        text: str,
        embedding: Optional[list[float]] = None,
        byte_start: Optional[int] = None,
        byte_end: Optional[int] = None,
    ) -> str:
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (c:Chunk {id: $id})
                SET c.artifact_version_id = $artifact_version_id,
                    c.sequence = $sequence,
                    c.text = $text,
                    c.embedding = $embedding,
                    c.byte_start = $byte_start,
                    c.byte_end = $byte_end
                WITH c
                MATCH (av:ArtifactVersion {id: $artifact_version_id})
                MERGE (av)-[:CONTAINS_CHUNK]->(c)
                """,
                id=chunk_id,
                artifact_version_id=artifact_version_id,
                sequence=sequence,
                text=text,
                embedding=embedding,
                byte_start=byte_start,
                byte_end=byte_end,
            )
        return chunk_id

    async def upsert_section(
        self,
        section_id: str,
        artifact_version_id: str,
        title: str,
        sequence: int,
        text_preview: str = "",
        page_start: Optional[int] = None,
        page_end: Optional[int] = None,
        timestamp_start: Optional[float] = None,
        timestamp_end: Optional[float] = None,
        file_path: Optional[str] = None,
    ) -> str:
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (s:Section {id: $id})
                SET s.artifact_version_id = $artifact_version_id,
                    s.title = $title,
                    s.sequence = $sequence,
                    s.text_preview = $text_preview,
                    s.page_start = $page_start,
                    s.page_end = $page_end,
                    s.timestamp_start = $timestamp_start,
                    s.timestamp_end = $timestamp_end,
                    s.file_path = $file_path
                WITH s
                MATCH (av:ArtifactVersion {id: $artifact_version_id})
                MERGE (av)-[:CONTAINS_SECTION]->(s)
                """,
                id=section_id,
                artifact_version_id=artifact_version_id,
                title=title,
                sequence=sequence,
                text_preview=text_preview,
                page_start=page_start,
                page_end=page_end,
                timestamp_start=timestamp_start,
                timestamp_end=timestamp_end,
                file_path=file_path,
            )
        return section_id

    async def link_entity_to_source_span(
        self,
        entity_id: str,
        chunk_id: str,
        byte_start: Optional[int] = None,
        byte_end: Optional[int] = None,
    ) -> str:
        span_id = _new_id("SS")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (ss:SourceSpan {id: $span_id})
                SET ss.chunk_id = $chunk_id,
                    ss.byte_start = $byte_start,
                    ss.byte_end = $byte_end
                WITH ss
                MATCH (c:Chunk {id: $chunk_id})
                MERGE (ss)-[:WITHIN]->(c)
                """,
                span_id=span_id,
                chunk_id=chunk_id,
                byte_start=byte_start,
                byte_end=byte_end,
            )
            # Link the entity to its source span
            await session.run(
                """
                MATCH (n {id: $entity_id}), (ss:SourceSpan {id: $span_id})
                MERGE (n)-[:EXTRACTED_FROM]->(ss)
                """,
                entity_id=entity_id,
                span_id=span_id,
            )
        return span_id

    # ------------------------------------------------------------------
    # Artifact-type-specific entity upserts
    # ------------------------------------------------------------------

    async def upsert_policy_node(
        self,
        title: str,
        description: str = "",
        owner: str = "",
        effective_date: Optional[str] = None,
        scope: str = "",
        embedding: Optional[list[float]] = None,
        workspace: str = "default",
        sensitivity: str = "internal",
        artifact_version_id: Optional[str] = None,
    ) -> str:
        pid = _new_id("POL")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (p:Policy {title: $title, workspace: $workspace})
                ON CREATE SET p.id = $id
                SET p.description = $description,
                    p.owner = $owner,
                    p.effective_date = $effective_date,
                    p.scope = $scope,
                    p.embedding = $embedding,
                    p.sensitivity = $sensitivity,
                    p.created_at = coalesce(p.created_at, $created_at)
                """,
                id=pid,
                title=title,
                description=description,
                owner=owner,
                effective_date=effective_date,
                scope=scope,
                embedding=embedding,
                workspace=workspace,
                sensitivity=sensitivity,
                created_at=datetime.utcnow().isoformat(),
            )
        return pid

    async def upsert_control_node(
        self,
        title: str,
        description: str = "",
        policy_title: str = "",
        workspace: str = "default",
        sensitivity: str = "internal",
        artifact_version_id: Optional[str] = None,
    ) -> str:
        cid = _new_id("CTL")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (c:Control {title: $title, workspace: $workspace})
                ON CREATE SET c.id = $id
                SET c.description = $description,
                    c.created_at = coalesce(c.created_at, $created_at)
                """,
                id=cid,
                title=title,
                description=description,
                workspace=workspace,
                created_at=datetime.utcnow().isoformat(),
            )
            if policy_title:
                await session.run(
                    """
                    MATCH (p:Policy {title: $policy_title}), (c:Control {id: $cid})
                    MERGE (p)-[:REQUIRES_CONTROL]->(c)
                    """,
                    policy_title=policy_title,
                    cid=cid,
                )
        return cid

    async def upsert_requirement_node(
        self,
        title: str,
        description: str = "",
        req_type: str = "functional",
        priority: str = "medium",
        embedding: Optional[list[float]] = None,
        workspace: str = "default",
        sensitivity: str = "internal",
        artifact_version_id: Optional[str] = None,
    ) -> str:
        rid = _new_id("REQ")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (r:Requirement {title: $title, workspace: $workspace})
                ON CREATE SET r.id = $id
                SET r.description = $description,
                    r.req_type = $req_type,
                    r.priority = $priority,
                    r.embedding = $embedding,
                    r.created_at = coalesce(r.created_at, $created_at)
                """,
                id=rid,
                title=title,
                description=description,
                req_type=req_type,
                priority=priority,
                embedding=embedding,
                workspace=workspace,
                created_at=datetime.utcnow().isoformat(),
            )
        return rid

    async def upsert_product_goal_node(
        self,
        title: str,
        description: str = "",
        workspace: str = "default",
        sensitivity: str = "internal",
        artifact_version_id: Optional[str] = None,
    ) -> str:
        gid = _new_id("PG")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (pg:ProductGoal {title: $title, workspace: $workspace})
                ON CREATE SET pg.id = $id
                SET pg.description = $description,
                    pg.created_at = coalesce(pg.created_at, $created_at)
                """,
                id=gid,
                title=title,
                description=description,
                workspace=workspace,
                created_at=datetime.utcnow().isoformat(),
            )
        return gid

    async def upsert_repository(
        self,
        owner: str,
        repo_name: str,
        repo_url: str,
        branch: str,
        workspace_id: str,
        artifact_version_id: str,
    ) -> str:
        rid = _new_id("REPO")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (r:Repository {repo_url: $repo_url})
                ON CREATE SET r.id = $id
                SET r.owner = $owner,
                    r.repo_name = $repo_name,
                    r.branch = $branch,
                    r.workspace_id = $workspace_id,
                    r.ingested_at = $ingested_at
                WITH r
                MATCH (av:ArtifactVersion {id: $artifact_version_id})
                MERGE (av)-[:DESCRIBES]->(r)
                """,
                id=rid,
                owner=owner,
                repo_name=repo_name,
                repo_url=repo_url,
                branch=branch,
                workspace_id=workspace_id,
                ingested_at=datetime.utcnow().isoformat(),
                artifact_version_id=artifact_version_id,
            )
            # Return the id we set
            result = await session.run(
                "MATCH (r:Repository {repo_url: $repo_url}) RETURN r.id AS id",
                repo_url=repo_url,
            )
            row = await result.single()
        return row["id"] if row else rid

    async def upsert_symbol(
        self,
        name: str,
        kind: str,
        file_path: str,
        line_start: int,
        line_end: int,
        docstring: str = "",
        repo_node_id: Optional[str] = None,
        embedding: Optional[list[float]] = None,
        workspace_id: str = "default",
        artifact_version_id: Optional[str] = None,
    ) -> str:
        sid = _new_id("SYM")
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (s:Symbol {name: $name, file_path: $file_path, kind: $kind})
                ON CREATE SET s.id = $id
                SET s.line_start = $line_start,
                    s.line_end = $line_end,
                    s.docstring = $docstring,
                    s.embedding = $embedding,
                    s.workspace_id = $workspace_id,
                    s.updated_at = $updated_at
                """,
                id=sid,
                name=name,
                kind=kind,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                docstring=docstring,
                embedding=embedding,
                workspace_id=workspace_id,
                updated_at=datetime.utcnow().isoformat(),
            )
            if repo_node_id:
                await session.run(
                    """
                    MATCH (r:Repository {id: $repo_id}), (s:Symbol {name: $name, file_path: $file_path})
                    MERGE (r)-[:DEFINES_SYMBOL]->(s)
                    """,
                    repo_id=repo_node_id,
                    name=name,
                    file_path=file_path,
                )
        return sid

    async def upsert_speaker_turn(
        self,
        artifact_version_id: str,
        speaker: str,
        text: str,
        start_ts: float,
        end_ts: float,
    ) -> str:
        turn_id = _new_id("ST")
        async with self.driver.session() as session:
            await session.run(
                """
                CREATE (st:SpeakerTurn {
                    id: $id,
                    artifact_version_id: $artifact_version_id,
                    speaker: $speaker,
                    text: $text,
                    start_ts: $start_ts,
                    end_ts: $end_ts,
                    created_at: $created_at
                })
                WITH st
                MATCH (av:ArtifactVersion {id: $artifact_version_id})
                MERGE (av)-[:CONTAINS_TURN]->(st)
                """,
                id=turn_id,
                artifact_version_id=artifact_version_id,
                speaker=speaker,
                text=text,
                start_ts=start_ts,
                end_ts=end_ts,
                created_at=datetime.utcnow().isoformat(),
            )
        return turn_id

    async def upsert_relationship(
        self,
        from_label: str,
        from_title: str,
        rel_type: str,
        to_label: str,
        to_title: str,
    ) -> None:
        """Create a relationship between two nodes matched by their title/text property."""
        if not all([from_label, from_title, rel_type, to_label, to_title]):
            return

        # Sanitize rel_type to be a valid Cypher relationship type
        safe_rel = rel_type.upper().replace(" ", "_").replace("-", "_")
        # Allow only known relationship types to prevent injection
        allowed_rels = {
            "DEPENDS_ON", "SUPPORTED_BY", "CONTRADICTED_BY", "BLOCKS",
            "REQUIRES_APPROVAL_FROM", "AFFECTS", "MADE_DECISION", "RAISES_RISK",
            "ENFORCES", "REQUIRES_CONTROL", "GRANTS_EXCEPTION", "ESCALATES_TO",
            "ACHIEVES_GOAL", "CONSTRAINED_BY", "MEASURED_BY", "TRADES_OFF_WITH",
            "LAUNCH_BLOCKED_BY", "IMPLEMENTS", "REFERENCES_DECISION", "RESOLVES_ISSUE",
        }
        if safe_rel not in allowed_rels:
            return

        title_prop = "text" if from_label == "Assumption" else "title"
        to_title_prop = "text" if to_label == "Assumption" else "title"

        query = f"""
        MATCH (a:{from_label} {{{title_prop}: $from_title}})
        MATCH (b:{to_label} {{{to_title_prop}: $to_title}})
        MERGE (a)-[:{safe_rel}]->(b)
        """
        try:
            async with self.driver.session() as session:
                await session.run(query, from_title=from_title, to_title=to_title)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Artifact list / query
    # ------------------------------------------------------------------

    async def list_artifacts(
        self,
        workspace_id: str = "default",
        artifact_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return a list of non-archived artifact records for the workspace."""
        type_filter = "AND a.type = $artifact_type" if artifact_type else ""
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (a:Artifact)
                WHERE a.workspace_id = $workspace_id
                  AND (a.archived IS NULL OR a.archived = false)
                  {type_filter}
                OPTIONAL MATCH (a)-[:HAS_VERSION]->(av:ArtifactVersion)
                RETURN a, count(av) AS version_count
                ORDER BY a.ingested_at DESC LIMIT $limit
                """,
                workspace_id=workspace_id,
                artifact_type=artifact_type,
                limit=limit,
            )
            rows = await result.data()
        return [
            {**dict(r["a"]), "version_count": r["version_count"]}
            for r in rows
        ]

    async def list_archived_artifacts(
        self,
        workspace_id: str = "default",
        artifact_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return a list of archived artifact records for the workspace."""
        type_filter = "AND a.type = $artifact_type" if artifact_type else ""
        async with self.driver.session() as session:
            result = await session.run(
                f"""
                MATCH (a:Artifact)
                WHERE a.workspace_id = $workspace_id
                  AND a.archived = true
                  {type_filter}
                OPTIONAL MATCH (a)-[:HAS_VERSION]->(av:ArtifactVersion)
                RETURN a, count(av) AS version_count
                ORDER BY a.archived_at DESC LIMIT $limit
                """,
                workspace_id=workspace_id,
                artifact_type=artifact_type,
                limit=limit,
            )
            rows = await result.data()
        return [
            {**dict(r["a"]), "version_count": r["version_count"]}
            for r in rows
        ]

    async def archive_artifact(self, artifact_id: str) -> bool:
        """Mark an artifact as archived."""
        from datetime import datetime, timezone
        archived_at = datetime.now(timezone.utc).isoformat()
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Artifact {id: $id})
                SET a.archived = true, a.archived_at = $archived_at
                RETURN a.id AS id
                """,
                id=artifact_id,
                archived_at=archived_at,
            )
            row = await result.single()
        return row is not None

    async def unarchive_artifact(self, artifact_id: str) -> bool:
        """Remove the archived flag from an artifact."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Artifact {id: $id})
                SET a.archived = false
                REMOVE a.archived_at
                RETURN a.id AS id
                """,
                id=artifact_id,
            )
            row = await result.single()
        return row is not None

    async def delete_artifact(self, artifact_id: str) -> bool:
        """Permanently delete an artifact and all its versions and chunks."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (a:Artifact {id: $id})
                OPTIONAL MATCH (a)-[:HAS_VERSION]->(av:ArtifactVersion)
                OPTIONAL MATCH (av)-[:CONTAINS_CHUNK]->(c:Chunk)
                DETACH DELETE c, av, a
                RETURN count(a) AS deleted
                """,
                id=artifact_id,
            )
            row = await result.single()
        return row is not None and row["deleted"] >= 0
