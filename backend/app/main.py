import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import get_neo4j_driver
from app.routers import actions, artifacts, chatbot, graph, ingest, permissions, query, resolution, webhooks, ws

_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "graph_schema")


_VECTOR_INDEX_NAMES = [
    "decision_embedding",
    "assumption_embedding",
    "evidence_embedding",
    "document_embedding",
    "chunk_embedding",
    "symbol_embedding",
    "policy_embedding",
    "requirement_embedding",
]


async def _apply_schema(driver) -> None:
    """Apply constraints and vector indexes from the graph_schema cypher files.

    Vector indexes are always dropped and recreated to handle dimension mismatches
    when the embedding model changes.
    """
    async with driver.session() as session:
        for idx_name in _VECTOR_INDEX_NAMES:
            try:
                await session.run(f"DROP INDEX {idx_name} IF EXISTS")
            except Exception:
                pass

    for filename in ("constraints.cypher", "indexes.cypher"):
        path = os.path.join(_SCHEMA_DIR, filename)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            raw = f.read()
        def _strip_comments(stmt: str) -> str:
            lines = [l for l in stmt.splitlines() if not l.strip().startswith("//")]
            return "\n".join(lines).strip()

        statements = [
            _strip_comments(s) for s in raw.split(";")
            if _strip_comments(s)
        ]
        async with driver.session() as session:
            for stmt in statements:
                try:
                    await session.run(stmt)
                except Exception as e:
                    print(f"Schema warning ({filename}): {e}")
    print("Neo4j schema applied.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver = get_neo4j_driver()
    try:
        async with driver.session() as session:
            await session.run("RETURN 1")
        print("Connected to Neo4j.")
        await _apply_schema(driver)
    except Exception as e:
        print(f"Warning: Could not connect to Neo4j: {e}")
    yield
    await driver.close()


app = FastAPI(
    title="digiTwin API",
    description="Permission-aware decision intelligence for enterprise teams",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(artifacts.router)
app.include_router(query.router)
app.include_router(chatbot.router)
app.include_router(graph.router)
app.include_router(permissions.router)
app.include_router(actions.router)
app.include_router(webhooks.router)
app.include_router(ws.router)
app.include_router(resolution.router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "digiTwin"}
