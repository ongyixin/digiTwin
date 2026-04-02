"""Initialize Neo4j schema: constraints and indexes."""

import os
import sys
import time

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable


def wait_for_neo4j(driver, retries=30, delay=2):
    for i in range(retries):
        try:
            with driver.session() as session:
                session.run("RETURN 1")
            print("Neo4j is ready.")
            return
        except ServiceUnavailable:
            print(f"Waiting for Neo4j... ({i+1}/{retries})")
            time.sleep(delay)
    raise RuntimeError("Neo4j did not become ready in time.")


def run_cypher_file(session, path):
    with open(path) as f:
        content = f.read()
    statements = [s.strip() for s in content.split(";") if s.strip() and not s.strip().startswith("//")]
    for stmt in statements:
        try:
            session.run(stmt)
        except Exception as e:
            print(f"Warning running: {stmt[:80]}...\n  {e}")


def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "digitwin2026")

    driver = GraphDatabase.driver(uri, auth=(user, password))

    print("Waiting for Neo4j to be ready...")
    wait_for_neo4j(driver)

    schema_dir = os.path.join(os.path.dirname(__file__), "../backend/app/graph_schema")

    with driver.session() as session:
        print("Applying constraints...")
        run_cypher_file(session, os.path.join(schema_dir, "constraints.cypher"))
        print("Applying indexes...")
        run_cypher_file(session, os.path.join(schema_dir, "indexes.cypher"))

    print("Schema initialized successfully.")
    driver.close()


if __name__ == "__main__":
    main()
