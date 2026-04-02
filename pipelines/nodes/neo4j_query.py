"""
RocketRide custom node: Execute parameterized Cypher queries against Neo4j.
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


def main():
    payload = json.loads(sys.stdin.read())
    query = payload.get("query", "")
    params = payload.get("params", {})

    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, **params)
        records = [dict(r) for r in result]

    print(json.dumps({"results": records}))
    driver.close()


if __name__ == "__main__":
    main()
