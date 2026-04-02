"""
RocketRide custom node: Upsert entities and relationships to Neo4j.
Called by ingest_transcript.pipe and draft_followups.pipe.
"""

import json
import os
import sys
import uuid
from datetime import datetime

from neo4j import GraphDatabase


def get_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "digitwin2026")
    return GraphDatabase.driver(uri, auth=(user, password))


def upsert_entities(session, entities: dict, embeddings: dict, meeting_id: str):
    """Merge all extracted entities into Neo4j."""
    decision_map = {}
    person_map = {}

    # Upsert persons
    for p in entities.get("persons", []):
        pid = p.get("id") or p["name"].lower().replace(" ", "_")
        session.run(
            "MERGE (p:Person {id: $id}) SET p.name = $name",
            id=pid, name=p["name"],
        )
        person_map[p["name"]] = pid

    # Upsert decisions
    for d in entities.get("decisions", []):
        did = f"D-{uuid.uuid4().hex[:8]}"
        embedding = embeddings.get(d["title"])
        session.run(
            """
            MERGE (d:Decision {id: $id})
            SET d.title = $title, d.summary = $summary,
                d.status = $status, d.confidence = $confidence,
                d.embedding = $embedding,
                d.created_at = $created_at
            """,
            id=did, title=d["title"], summary=d.get("summary", ""),
            status="proposed", confidence=d.get("confidence", 0.8),
            embedding=embedding,
            created_at=datetime.utcnow().isoformat(),
        )
        decision_map[d["title"]] = did

        owner_name = d.get("owner")
        if owner_name and owner_name in person_map:
            session.run(
                "MATCH (p:Person {id: $pid}), (d:Decision {id: $did}) MERGE (p)-[:MADE_DECISION]->(d)",
                pid=person_map[owner_name], did=did,
            )
        if meeting_id:
            session.run(
                "MATCH (m:Meeting {id: $mid}), (d:Decision {id: $did}) MERGE (m)-[:PRODUCED]->(d)",
                mid=meeting_id, did=did,
            )

    # Upsert assumptions
    for a in entities.get("assumptions", []):
        aid = f"A-{uuid.uuid4().hex[:8]}"
        embedding = embeddings.get(a["text"])
        session.run(
            """
            MERGE (a:Assumption {id: $id})
            SET a.text = $text, a.status = 'active',
                a.risk_level = $risk_level, a.embedding = $embedding
            """,
            id=aid, text=a["text"],
            risk_level=a.get("risk_level", "medium"), embedding=embedding,
        )
        related = a.get("related_decision_title")
        if related and related in decision_map:
            session.run(
                "MATCH (d:Decision {id: $did}), (a:Assumption {id: $aid}) MERGE (d)-[:DEPENDS_ON]->(a)",
                did=decision_map[related], aid=aid,
            )

    # Upsert evidence
    for e in entities.get("evidence", []):
        eid = f"E-{uuid.uuid4().hex[:8]}"
        embedding = embeddings.get(e["title"])
        session.run(
            """
            MERGE (e:Evidence {id: $id})
            SET e.title = $title, e.content_summary = $summary,
                e.source_type = $source_type, e.embedding = $embedding
            """,
            id=eid, title=e["title"],
            summary=e.get("content_summary", ""),
            source_type=e.get("source_type", "document"), embedding=embedding,
        )
        related = e.get("related_decision_title")
        if related and related in decision_map:
            session.run(
                "MATCH (d:Decision {id: $did}), (e:Evidence {id: $eid}) MERGE (d)-[:SUPPORTED_BY]->(e)",
                did=decision_map[related], eid=eid,
            )

    return decision_map


def create_agent_action(session, action_type: str, initiated_by: str, policy_path: list):
    action_id = f"AA-{uuid.uuid4().hex[:8]}"
    session.run(
        """
        CREATE (aa:AgentAction {
            id: $id, action_type: $action_type,
            initiated_by: $initiated_by, executed_by_agent: 'digiTwin',
            policy_path: $policy_path, status: 'completed',
            timestamp: $timestamp
        })
        """,
        id=action_id, action_type=action_type, initiated_by=initiated_by,
        policy_path=policy_path, timestamp=datetime.utcnow().isoformat(),
    )
    return action_id


def main():
    payload = json.loads(sys.stdin.read())
    action = payload.get("action", "upsert_entities")
    driver = get_driver()

    with driver.session() as session:
        if action == "create_agent_action":
            action_id = create_agent_action(
                session,
                action_type=payload.get("action_type", "unknown"),
                initiated_by=payload.get("user_id", "system"),
                policy_path=payload.get("policy_path", []),
            )
            print(json.dumps({"agent_action_id": action_id}))
        else:
            decision_map = upsert_entities(
                session,
                entities=payload.get("entities", {}),
                embeddings=payload.get("embeddings", {}),
                meeting_id=payload.get("meeting_id", ""),
            )
            print(json.dumps({"decision_map": decision_map, "status": "ok"}))

    driver.close()


if __name__ == "__main__":
    main()
