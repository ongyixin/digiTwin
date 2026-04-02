"""
RocketRide custom node: Check permissions against the Neo4j permission subgraph.
"""

import json
import os
import sys

from neo4j import GraphDatabase


def get_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "digitwin2026")
    return GraphDatabase.driver(uri, auth=(user, password))


def check_permission(session, user_id: str, action: str, resource_id: str) -> dict:
    # Direct permission
    result = session.run(
        """
        MATCH (p:Person {id: $user_id})-[:HAS_ROLE]->(r:Role)-[:GRANTS]->(perm:Permission {action: $action})
        MATCH (perm)-[:ON_RESOURCE]->(res:Resource {id: $resource_id})
        RETURN r.name AS role, perm.action AS action
        LIMIT 1
        """,
        user_id=user_id, action=action, resource_id=resource_id,
    )
    records = list(result)
    if records:
        row = records[0]
        return {
            "allowed": True,
            "policy_path": [f"User:{user_id}", f"Role:{row['role']}", f"Permission:{action}", f"Resource:{resource_id}"],
            "requires_approval": False,
            "approver": None,
            "reason": f"Allowed via role '{row['role']}'",
        }

    # Delegation check
    result = session.run(
        """
        MATCH (p:Person {id: $user_id})<-[:DELEGATED_TO]-(delegator:Person)
        MATCH (delegator)-[:HAS_ROLE]->(r:Role)-[:GRANTS]->(perm:Permission {action: $action})
        MATCH (perm)-[:ON_RESOURCE]->(res:Resource {id: $resource_id})
        RETURN delegator.name AS delegator_name, r.name AS role
        LIMIT 1
        """,
        user_id=user_id, action=action, resource_id=resource_id,
    )
    records = list(result)
    if records:
        row = records[0]
        return {
            "allowed": True,
            "policy_path": [f"User:{user_id}", f"DelegatedBy:{row['delegator_name']}", f"Role:{row['role']}", f"Permission:{action}", f"Resource:{resource_id}"],
            "requires_approval": False,
            "approver": None,
            "reason": f"Allowed via delegation from '{row['delegator_name']}'",
        }

    return {
        "allowed": False,
        "policy_path": [f"User:{user_id}", f"Action:{action}", f"Resource:{resource_id}", "Denied"],
        "requires_approval": False,
        "approver": None,
        "reason": f"No permission for action '{action}' on resource '{resource_id}'",
    }


def main():
    payload = json.loads(sys.stdin.read())
    user_id = payload.get("user_id", "")
    action = payload.get("action", "")
    resource_id = payload.get("resource_id", "")

    driver = get_driver()
    with driver.session() as session:
        result = check_permission(session, user_id, action, resource_id)

    print(json.dumps(result))
    driver.close()


if __name__ == "__main__":
    main()
