"""
Embed Decision, Assumption, and Evidence nodes in Neo4j using the Gemini API.

Nodes seeded by seed_demo.py are created without `embedding` properties, so
vector search always returns empty results. This script back-fills embeddings
for every un-embedded node so the twin can find relevant context.

Run after seed_demo.py:
    python scripts/embed_graph_nodes.py
"""

import os
import sys
import time

from google import genai
from neo4j import GraphDatabase


EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_DELAY_SECS = 0.5  # avoid rate-limit burst

NODE_QUERIES = [
    (
        "Decision",
        """
        MATCH (n:Decision) WHERE n.embedding IS NULL
        RETURN n.id AS id,
               coalesce(n.title, '') + ' ' + coalesce(n.summary, '') AS text
        """,
    ),
    (
        "Assumption",
        """
        MATCH (n:Assumption) WHERE n.embedding IS NULL
        RETURN n.id AS id,
               coalesce(n.title, '') + ' ' + coalesce(n.text, '') AS text
        """,
    ),
    (
        "Evidence",
        """
        MATCH (n:Evidence) WHERE n.embedding IS NULL
        RETURN n.id AS id,
               coalesce(n.title, '') + ' ' + coalesce(n.text, '') + ' ' + coalesce(n.summary, '') AS text
        """,
    ),
]

UPDATE_QUERY = """
MATCH (n {id: $id})
SET n.embedding = $embedding
"""


def get_neo4j_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "digitwin2026")
    return GraphDatabase.driver(uri, auth=(user, password))


def embed_text(client: genai.Client, text: str) -> list[float] | None:
    text = text.strip()
    if not text:
        return None
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text[:8000],
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"  [embedding error] {e}", file=sys.stderr)
        return None


def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    gemini = genai.Client(api_key=api_key)
    driver = get_neo4j_driver()

    total_embedded = 0
    total_skipped = 0

    with driver.session() as session:
        for label, fetch_query in NODE_QUERIES:
            print(f"\n── Embedding {label} nodes ──")
            records = list(session.run(fetch_query))
            if not records:
                print(f"  No un-embedded {label} nodes found.")
                continue

            for record in records:
                node_id = record["id"]
                text = (record["text"] or "").strip()
                if not text:
                    print(f"  SKIP {node_id} (empty text)")
                    total_skipped += 1
                    continue

                embedding = embed_text(gemini, text)
                if embedding is None:
                    print(f"  FAIL {node_id} (embedding returned None)")
                    total_skipped += 1
                    continue

                session.run(UPDATE_QUERY, id=node_id, embedding=embedding)
                print(f"  OK   {node_id} ({len(embedding)}-dim)")
                total_embedded += 1
                time.sleep(BATCH_DELAY_SECS)

    driver.close()
    print(f"\n=== Done: {total_embedded} embedded, {total_skipped} skipped ===")


if __name__ == "__main__":
    main()
