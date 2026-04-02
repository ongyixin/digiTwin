"""
Seed the Neo4j graph with full demo data for digiTwin showcase.

Loads:
  - data/sample_permissions.json  → Person, Role, Resource, Scope, Permission nodes
  - data/demo_graph.json          → Meeting, Decision, Assumption, Evidence, Task,
                                    Approval, AgentAction, ReviewTask, Artifact,
                                    ResolutionCase, ResolutionPlan, ProposedAction,
                                    RiskAssessment nodes + all relationships

Run after init_neo4j.py:
    python scripts/seed_demo.py
"""

import json
import os
import sys

from neo4j import GraphDatabase


def get_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "digitwin2026")
    return GraphDatabase.driver(uri, auth=(user, password))


# ---------------------------------------------------------------------------
# Permissions graph (from sample_permissions.json)
# ---------------------------------------------------------------------------

def seed_permissions(session, data: dict):
    print("\n── Permissions ──")

    for u in data["users"]:
        session.run(
            """
            MERGE (p:Person {id: $id})
            SET p.name = $name, p.email = $email, p.department = $department
            """,
            id=u["id"], name=u["name"],
            email=u.get("email", ""), department=u.get("department", ""),
        )
        print(f"  Person: {u['name']}")

    for r in data["roles"]:
        session.run(
            """
            MERGE (r:Role {id: $id})
            SET r.name = $name, r.description = $desc
            """,
            id=r["id"], name=r["name"], desc=r.get("description", ""),
        )
        print(f"  Role: {r['name']}")

    for res in data["resources"]:
        session.run(
            """
            MERGE (r:Resource {id: $id})
            SET r.resource_type = $rtype, r.description = $desc
            """,
            id=res["id"], rtype=res.get("type", "action"),
            desc=res.get("description", ""),
        )
        print(f"  Resource: {res['id']}")

    for s in data.get("scopes", []):
        session.run(
            """
            MERGE (s:Scope {id: $id})
            SET s.name = $name, s.boundary = $boundary
            """,
            id=s["id"], name=s["name"], boundary=s.get("boundary", ""),
        )
        print(f"  Scope: {s['name']}")

    perm_counter = 0
    for r in data["roles"]:
        for perm_str in r.get("permissions", []):
            action, resource_id = perm_str.split(":", 1)
            perm_id = f"P-{r['id']}-{action}-{resource_id}"
            session.run(
                """
                MERGE (p:Permission {id: $id})
                SET p.action = $action
                """,
                id=perm_id, action=action,
            )
            session.run(
                """
                MATCH (r:Role {id: $rid}), (p:Permission {id: $pid})
                MERGE (r)-[:GRANTS]->(p)
                """,
                rid=r["id"], pid=perm_id,
            )
            check = session.run(
                "MATCH (res:Resource {id: $id}) RETURN res",
                id=resource_id,
            )
            if list(check):
                session.run(
                    """
                    MATCH (p:Permission {id: $pid}), (res:Resource {id: $rid})
                    MERGE (p)-[:ON_RESOURCE]->(res)
                    """,
                    pid=perm_id, rid=resource_id,
                )
            perm_counter += 1

    print(f"  {perm_counter} Permission nodes created")

    for u in data["users"]:
        for role_id in u.get("roles", []):
            session.run(
                """
                MATCH (p:Person {id: $pid}), (r:Role {id: $rid})
                MERGE (p)-[:HAS_ROLE]->(r)
                """,
                pid=u["id"], rid=role_id,
            )
        print(f"  {u['name']} → roles: {u.get('roles', [])}")


# ---------------------------------------------------------------------------
# Graph entities (from demo_graph.json)
# ---------------------------------------------------------------------------

def seed_meetings(session, meetings):
    print("\n── Meetings ──")
    for m in meetings:
        session.run(
            """
            MERGE (m:Meeting {id: $id})
            SET m.title = $title, m.date = $date, m.participants = $participants
            """,
            id=m["id"], title=m["title"], date=m["date"],
            participants=m.get("participants", []),
        )
        print(f"  Meeting: {m['title']}")


def seed_decisions(session, decisions):
    print("\n── Decisions ──")
    for d in decisions:
        session.run(
            """
            MERGE (d:Decision {id: $id})
            SET d.title = $title,
                d.summary = $summary,
                d.status = $status,
                d.confidence = $confidence,
                d.source_excerpt = $source_excerpt,
                d.workspace = $workspace,
                d.tenant = $tenant,
                d.confidentiality = $confidentiality,
                d.provenance_speaker = $provenance_speaker,
                d.created_at = coalesce(d.created_at, $created_at)
            """,
            id=d["id"], title=d["title"], summary=d["summary"],
            status=d.get("status", "proposed"),
            confidence=d.get("confidence", 0.8),
            source_excerpt=d.get("source_excerpt", ""),
            workspace=d.get("workspace", "default"),
            tenant=d.get("tenant", "default"),
            confidentiality=d.get("confidentiality", "internal"),
            provenance_speaker=d.get("provenance_speaker", ""),
            created_at="2026-04-01T10:00:00Z",
        )
        if d.get("owner_id"):
            session.run(
                """
                MATCH (d:Decision {id: $did}), (p:Person {id: $pid})
                MERGE (p)-[:MADE_DECISION]->(d)
                """,
                did=d["id"], pid=d["owner_id"],
            )
        if d.get("meeting_id"):
            session.run(
                """
                MATCH (d:Decision {id: $did}), (m:Meeting {id: $mid})
                MERGE (m)-[:PRODUCED]->(d)
                """,
                did=d["id"], mid=d["meeting_id"],
            )
        print(f"  Decision [{d['status']}]: {d['title'][:60]}")


def seed_assumptions(session, assumptions):
    print("\n── Assumptions ──")
    for a in assumptions:
        session.run(
            """
            MERGE (a:Assumption {id: $id})
            SET a.text = $text,
                a.status = $status,
                a.risk_level = $risk_level,
                a.workspace = $workspace,
                a.provenance_speaker = $provenance_speaker,
                a.created_at = coalesce(a.created_at, $created_at)
            """,
            id=a["id"], text=a["text"],
            status=a.get("status", "active"),
            risk_level=a.get("risk_level", "medium"),
            workspace=a.get("workspace", "default"),
            provenance_speaker=a.get("provenance_speaker", ""),
            created_at="2026-04-01T10:00:00Z",
        )
        if a.get("decision_id"):
            session.run(
                """
                MATCH (d:Decision {id: $did}), (a:Assumption {id: $aid})
                MERGE (d)-[:DEPENDS_ON]->(a)
                """,
                did=a["decision_id"], aid=a["id"],
            )
        print(f"  Assumption [{a['risk_level']}]: {a['text'][:60]}")


def seed_evidence(session, evidence_list):
    print("\n── Evidence ──")
    for e in evidence_list:
        session.run(
            """
            MERGE (e:Evidence {id: $id})
            SET e.title = $title,
                e.content_summary = $content_summary,
                e.source_type = $source_type,
                e.source_url = $source_url,
                e.workspace = $workspace,
                e.confidentiality = $confidentiality,
                e.created_at = coalesce(e.created_at, $created_at)
            """,
            id=e["id"], title=e["title"],
            content_summary=e.get("content_summary", ""),
            source_type=e.get("source_type", "document"),
            source_url=e.get("source_url", ""),
            workspace=e.get("workspace", "default"),
            confidentiality=e.get("confidentiality", "internal"),
            created_at="2026-04-01T10:00:00Z",
        )
        if e.get("decision_id"):
            session.run(
                """
                MATCH (d:Decision {id: $did}), (e:Evidence {id: $eid})
                MERGE (d)-[:SUPPORTED_BY]->(e)
                """,
                did=e["decision_id"], eid=e["id"],
            )
        print(f"  Evidence: {e['title']}")


def seed_tasks(session, tasks):
    print("\n── Tasks ──")
    for t in tasks:
        session.run(
            """
            MERGE (t:Task {id: $id})
            SET t.title = $title,
                t.status = $status,
                t.assignee_id = $assignee_id,
                t.due_date = $due_date,
                t.created_at = coalesce(t.created_at, $created_at)
            """,
            id=t["id"], title=t["title"],
            status=t.get("status", "open"),
            assignee_id=t.get("assignee_id", ""),
            due_date=t.get("due_date"),
            created_at="2026-04-01T10:00:00Z",
        )
        if t.get("decision_id"):
            session.run(
                """
                MATCH (d:Decision {id: $did}), (t:Task {id: $tid})
                MERGE (t)-[:BLOCKS]->(d)
                """,
                did=t["decision_id"], tid=t["id"],
            )
        if t.get("assignee_id"):
            session.run(
                """
                MATCH (t:Task {id: $tid}), (p:Person {id: $pid})
                MERGE (t)-[:OWNED_BY]->(p)
                """,
                tid=t["id"], pid=t["assignee_id"],
            )
        print(f"  Task [{t['status']}]: {t['title']}")


def seed_approvals(session, approvals):
    print("\n── Approvals ──")
    for ap in approvals:
        session.run(
            """
            MERGE (ap:Approval {id: $id})
            SET ap.status = $status,
                ap.required_by = $required_by,
                ap.due_date = $due_date,
                ap.created_at = coalesce(ap.created_at, $created_at)
            """,
            id=ap["id"], status=ap.get("status", "pending"),
            required_by=ap.get("required_by", ""),
            due_date=ap.get("due_date"),
            created_at="2026-04-01T10:00:00Z",
        )
        session.run(
            """
            MATCH (ap:Approval {id: $apid}), (d:Decision {id: $did})
            MERGE (ap)-[:FOR_DECISION]->(d)
            """,
            apid=ap["id"], did=ap["decision_id"],
        )
        session.run(
            """
            MATCH (ap:Approval {id: $apid}), (p:Person {id: $pid})
            MERGE (ap)-[:ASSIGNED_TO]->(p)
            """,
            apid=ap["id"], pid=ap["assigned_to_id"],
        )
        print(f"  Approval [{ap['status']}]: {ap['id']} → {ap['assigned_to_id']}")


def seed_agent_actions(session, actions):
    print("\n── Agent Actions ──")
    for aa in actions:
        session.run(
            """
            MERGE (aa:AgentAction {id: $id})
            SET aa.action_type = $action_type,
                aa.initiated_by = $initiated_by,
                aa.executed_by_agent = $executed_by_agent,
                aa.policy_path = $policy_path,
                aa.status = $status,
                aa.timestamp = $timestamp
            """,
            id=aa["id"],
            action_type=aa["action_type"],
            initiated_by=aa["initiated_by"],
            executed_by_agent=aa.get("executed_by_agent", "digiTwin"),
            policy_path=aa.get("policy_path", []),
            status=aa.get("status", "executed"),
            timestamp=aa.get("timestamp", "2026-04-01T12:00:00Z"),
        )
        print(f"  AgentAction [{aa['status']}]: {aa['action_type']} by {aa['initiated_by']}")


def seed_review_tasks(session, review_tasks):
    print("\n── Review Tasks ──")
    for rt in review_tasks:
        session.run(
            """
            MERGE (rt:ReviewTask {id: $id})
            SET rt.original_action_id = $original_action_id,
                rt.action_type = $action_type,
                rt.initiated_by = $initiated_by,
                rt.reason = $reason,
                rt.status = $status,
                rt.created_at = $created_at
            """,
            id=rt["id"],
            original_action_id=rt["original_action_id"],
            action_type=rt["action_type"],
            initiated_by=rt["initiated_by"],
            reason=rt.get("reason", ""),
            status=rt.get("status", "pending"),
            created_at=rt.get("created_at", "2026-04-01T12:00:00Z"),
        )
        print(f"  ReviewTask [{rt['status']}]: {rt['action_type']} by {rt['initiated_by']}")


def seed_artifacts(session, artifacts):
    print("\n── Artifacts ──")
    for a in artifacts:
        import json as _json
        session.run(
            """
            MERGE (art:Artifact {id: $id})
            SET art.type = $type,
                art.source_type = $source_type,
                art.title = $title,
                art.workspace_id = $workspace_id,
                art.sensitivity = $sensitivity,
                art.mime_type = $mime_type,
                art.metadata = $metadata,
                art.status = $status,
                art.ingested_at = coalesce(art.ingested_at, $ingested_at)
            """,
            id=a["id"],
            type=a["type"],
            source_type=a.get("source_type", "document"),
            title=a["title"],
            workspace_id=a.get("workspace_id", "default"),
            sensitivity=a.get("sensitivity", "internal"),
            mime_type=a.get("mime_type", ""),
            metadata=_json.dumps(a.get("metadata", {})),
            status=a.get("status", "ingested"),
            ingested_at="2026-04-01T10:00:00Z",
        )
        print(f"  Artifact [{a['type']}]: {a['title']}")


def seed_resolution_cases(session, cases, risk_assessments, plans, proposed_actions):
    print("\n── Resolution Cases ──")
    for rc in cases:
        session.run(
            """
            MERGE (rc:ResolutionCase {id: $id})
            SET rc.title = $title,
                rc.description = $description,
                rc.case_type = $case_type,
                rc.status = $status,
                rc.severity = $severity,
                rc.autonomy_mode = $autonomy_mode,
                rc.created_at = $created_at,
                rc.created_by = $created_by,
                rc.trigger_source = $trigger_source,
                rc.workspace_id = $workspace_id
            """,
            id=rc["id"], title=rc["title"], description=rc.get("description", ""),
            case_type=rc["case_type"], status=rc["status"],
            severity=rc["severity"], autonomy_mode=rc["autonomy_mode"],
            created_at=rc.get("created_at", "2026-04-01T12:00:00Z"),
            created_by=rc.get("created_by", "system"),
            trigger_source=rc.get("trigger_source", "manual"),
            workspace_id=rc.get("workspace_id", "default"),
        )
        if rc.get("target_id"):
            session.run(
                """
                OPTIONAL MATCH (target {id: $target_id})
                WITH target
                MATCH (rc:ResolutionCase {id: $case_id})
                FOREACH (_ IN CASE WHEN target IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (rc)-[:ABOUT]->(target)
                )
                """,
                case_id=rc["id"], target_id=rc["target_id"],
            )
        print(f"  ResolutionCase [{rc['severity']}/{rc['status']}]: {rc['title'][:60]}")

    print("\n── Risk Assessments ──")
    for ra in risk_assessments:
        session.run(
            """
            MERGE (ra:RiskAssessment {id: $id})
            SET ra.risk_score = $risk_score,
                ra.blast_radius_score = $blast_radius_score,
                ra.staleness_score = $staleness_score,
                ra.contradiction_score = $contradiction_score,
                ra.dependency_score = $dependency_score,
                ra.notes = $notes,
                ra.created_at = $created_at
            """,
            id=ra["id"],
            risk_score=ra["risk_score"],
            blast_radius_score=ra["blast_radius_score"],
            staleness_score=ra["staleness_score"],
            contradiction_score=ra["contradiction_score"],
            dependency_score=ra["dependency_score"],
            notes=ra.get("notes", ""),
            created_at=ra.get("created_at", "2026-04-01T12:05:00Z"),
        )
        session.run(
            """
            MATCH (rc:ResolutionCase {id: $case_id}), (ra:RiskAssessment {id: $ra_id})
            MERGE (rc)-[:HAS_RISK]->(ra)
            """,
            case_id=ra["case_id"], ra_id=ra["id"],
        )
        print(f"  RiskAssessment: {ra['id']} (score={ra['risk_score']})")

    print("\n── Resolution Plans ──")
    for rp in plans:
        session.run(
            """
            MERGE (rp:ResolutionPlan {id: $id})
            SET rp.summary = $summary,
                rp.risk_score = $risk_score,
                rp.confidence_score = $confidence_score,
                rp.generated_at = $generated_at,
                rp.model_name = $model_name
            """,
            id=rp["id"], summary=rp["summary"],
            risk_score=rp["risk_score"],
            confidence_score=rp["confidence_score"],
            generated_at=rp.get("generated_at", "2026-04-01T12:10:00Z"),
            model_name=rp.get("model_name", "gemini-2.0-flash"),
        )
        session.run(
            """
            MATCH (rc:ResolutionCase {id: $case_id}), (rp:ResolutionPlan {id: $plan_id})
            MERGE (rc)-[:HAS_PLAN]->(rp)
            """,
            case_id=rp["case_id"], plan_id=rp["id"],
        )
        print(f"  ResolutionPlan: {rp['id']} (confidence={rp['confidence_score']})")

    print("\n── Proposed Actions ──")
    for pa in proposed_actions:
        session.run(
            """
            MERGE (pa:ProposedAction {id: $id})
            SET pa.action_type = $action_type,
                pa.status = $status,
                pa.risk_level = $risk_level,
                pa.requires_review = $requires_review,
                pa.target_type = $target_type,
                pa.target_id = $target_id,
                pa.reason = $reason,
                pa.policy_path = $policy_path,
                pa.evidence_refs = $evidence_refs,
                pa.executed_at = $executed_at
            """,
            id=pa["id"],
            action_type=pa["action_type"],
            status=pa["status"],
            risk_level=pa.get("risk_level", "low"),
            requires_review=pa.get("requires_review", False),
            target_type=pa.get("target_type", ""),
            target_id=pa.get("target_id", ""),
            reason=pa.get("reason", ""),
            policy_path=pa.get("policy_path", []),
            evidence_refs=pa.get("evidence_refs", []),
            executed_at=pa.get("executed_at", None),
        )
        session.run(
            """
            MATCH (rp:ResolutionPlan {id: $plan_id}), (pa:ProposedAction {id: $pa_id})
            MERGE (rp)-[:PROPOSES]->(pa)
            """,
            plan_id=pa["plan_id"], pa_id=pa["id"],
        )
        print(f"  ProposedAction [{pa['status']}]: {pa['action_type']} → {pa.get('target_id', '')}")


def seed_extra_relationships(session):
    """Additional cross-entity relationships for richer graph traversal."""
    print("\n── Extra Relationships ──")

    # D-launch-april15 depends on D-dpa-required (launch blocked by DPA)
    session.run(
        """
        MATCH (d1:Decision {id: 'D-launch-april15'}), (d2:Decision {id: 'D-dpa-required'})
        MERGE (d1)-[:LAUNCH_BLOCKED_BY]->(d2)
        """
    )
    # D-launch-april15 depends on D-qa-signoff
    session.run(
        """
        MATCH (d1:Decision {id: 'D-launch-april15'}), (d2:Decision {id: 'D-qa-signoff'})
        MERGE (d1)-[:LAUNCH_BLOCKED_BY]->(d2)
        """
    )
    # D-launch-april15 depends on D-runbook-update
    session.run(
        """
        MATCH (d1:Decision {id: 'D-launch-april15'}), (d2:Decision {id: 'D-runbook-update'})
        MERGE (d1)-[:DEPENDS_ON]->(d2)
        """
    )
    # Evidence E-q1-churn-report also supports the beta scope decision
    session.run(
        """
        MATCH (d:Decision {id: 'D-beta-scope'}), (e:Evidence {id: 'E-q1-churn-report'})
        MERGE (d)-[:SUPPORTED_BY]->(e)
        """
    )
    # Contradicted assumption CONTRADICTED_BY the active assumption
    session.run(
        """
        MATCH (a1:Assumption {id: 'A-churn-contradicted'}), (a2:Assumption {id: 'A-churn-low'})
        MERGE (a1)-[:CONTRADICTED_BY]->(a2)
        """
    )
    # Tasks T-legal-dpa-review blocks T-gonogo-meeting (can't hold go/no-go without legal)
    session.run(
        """
        MATCH (t1:Task {id: 'T-legal-dpa-review'}), (t2:Task {id: 'T-gonogo-meeting'})
        MERGE (t1)-[:BLOCKS]->(t2)
        """
    )
    # Resolution case RC-churn-contradiction is ABOUT the launch decision too
    session.run(
        """
        MATCH (rc:ResolutionCase {id: 'RC-churn-contradiction'}), (d:Decision {id: 'D-launch-april15'})
        MERGE (rc)-[:ABOUT]->(d)
        """
    )
    # Artifact → Decision provenance links
    session.run(
        """
        MATCH (art:Artifact {id: 'ART-beta-launch-transcript'}), (d:Decision {id: 'D-launch-april15'})
        MERGE (art)-[:PRODUCED]->(d)
        """
    )
    session.run(
        """
        MATCH (art:Artifact {id: 'ART-q1-churn-report'}), (e:Evidence {id: 'E-q1-churn-report'})
        MERGE (art)-[:PRODUCED]->(e)
        """
    )
    session.run(
        """
        MATCH (art:Artifact {id: 'ART-gdpr-policy'}), (e:Evidence {id: 'E-gdpr-policy'})
        MERGE (art)-[:PRODUCED]->(e)
        """
    )
    session.run(
        """
        MATCH (art:Artifact {id: 'ART-staging-results'}), (e:Evidence {id: 'E-staging-results'})
        MERGE (art)-[:PRODUCED]->(e)
        """
    )
    print("  Extra relationships created.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    base_dir = os.path.join(os.path.dirname(__file__), "..")

    perms_path = os.path.join(base_dir, "data", "sample_permissions.json")
    graph_path = os.path.join(base_dir, "data", "demo_graph.json")

    with open(perms_path) as f:
        perms_data = json.load(f)

    with open(graph_path) as f:
        graph_data = json.load(f)

    driver = get_driver()

    with driver.session() as session:
        print("=== Seeding permission graph ===")
        seed_permissions(session, perms_data)

        print("\n=== Seeding demo graph ===")
        seed_meetings(session, graph_data.get("meetings", []))
        seed_decisions(session, graph_data.get("decisions", []))
        seed_assumptions(session, graph_data.get("assumptions", []))
        seed_evidence(session, graph_data.get("evidence", []))
        seed_tasks(session, graph_data.get("tasks", []))
        seed_approvals(session, graph_data.get("approvals", []))
        seed_agent_actions(session, graph_data.get("agent_actions", []))
        seed_review_tasks(session, graph_data.get("review_tasks", []))
        seed_artifacts(session, graph_data.get("artifacts", []))
        seed_resolution_cases(
            session,
            graph_data.get("resolution_cases", []),
            graph_data.get("resolution_risk_assessments", []),
            graph_data.get("resolution_plans", []),
            graph_data.get("proposed_actions", []),
        )
        seed_extra_relationships(session)

    print("\n=== Seed complete ===")
    driver.close()


if __name__ == "__main__":
    main()
