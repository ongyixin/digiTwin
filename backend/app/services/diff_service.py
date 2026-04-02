"""Compute what changed in the knowledge twin after an ingestion run."""

from datetime import datetime, timezone

from neo4j import AsyncDriver

from app.models.api import TwinDiff, TwinDiffItem


class DiffService:
    def __init__(self, driver: AsyncDriver) -> None:
        self.driver = driver

    async def snapshot_before(self) -> dict:
        """Capture counts and IDs of existing nodes before ingestion."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (d:Decision) RETURN 'decisions' AS label, count(d) AS cnt, collect(d.id) AS ids
                UNION ALL
                MATCH (a:Assumption) RETURN 'assumptions' AS label, count(a) AS cnt, collect(a.id) AS ids
                UNION ALL
                MATCH (e:Evidence) RETURN 'evidence' AS label, count(e) AS cnt, collect(e.id) AS ids
                UNION ALL
                MATCH (t:Task) RETURN 'tasks' AS label, count(t) AS cnt, collect(t.id) AS ids
                UNION ALL
                MATCH (ap:Approval) RETURN 'approvals' AS label, count(ap) AS cnt, collect(ap.id) AS ids
            """)
            rows = await result.data()

        return {r["label"]: set(r["ids"]) for r in rows}

    async def compute_diff(self, before: dict, since_ts: str) -> TwinDiff:
        """Find nodes created since since_ts and compare against pre-run snapshot."""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (n)
                WHERE (n:Decision OR n:Assumption OR n:Evidence OR n:Task OR n:Approval)
                  AND n.created_at >= $since_ts
                RETURN labels(n)[0] AS label,
                       n.id AS id,
                       coalesce(n.title, n.text, n.required_by, n.id) AS title
                """,
                since_ts=since_ts,
            )
            new_nodes = await result.data()

            # Find contradicted/superseded assumptions
            result2 = await session.run(
                """
                MATCH (a:Assumption)-[:CONTRADICTED_BY]->(e:Evidence)
                WHERE e.created_at >= $since_ts
                RETURN a.id AS id, a.text AS title
                """,
                since_ts=since_ts,
            )
            contradicted = await result2.data()

        diff = TwinDiff()
        before_decisions = before.get("decisions", set())
        before_assumptions = before.get("assumptions", set())
        before_evidence = before.get("evidence", set())
        before_tasks = before.get("tasks", set())
        before_approvals = before.get("approvals", set())

        for node in new_nodes:
            label = node["label"]
            node_id = node["id"]
            title = str(node["title"] or node_id)
            item = TwinDiffItem(
                id=node_id,
                title=title,
                label=label,
                href=f"/decisions/{node_id}" if label == "Decision" else None,
            )
            if label == "Decision" and node_id not in before_decisions:
                diff.new_decisions.append(item)
            elif label == "Assumption" and node_id not in before_assumptions:
                diff.new_assumptions.append(item)
            elif label == "Evidence" and node_id not in before_evidence:
                diff.new_evidence.append(item)
            elif label == "Task" and node_id not in before_tasks:
                diff.new_tasks.append(item)
            elif label == "Approval" and node_id not in before_approvals:
                diff.new_approvals.append(item)

        for row in contradicted:
            diff.superseded_assumptions.append(
                TwinDiffItem(id=row["id"], title=str(row["title"] or row["id"]), label="Assumption")
            )

        return diff
