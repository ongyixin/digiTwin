from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.dependencies import get_neo4j_driver
from app.routers import actions, artifacts, chatbot, graph, ingest, permissions, query, resolution, webhooks, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify Neo4j connection on startup
    driver = get_neo4j_driver()
    try:
        async with driver.session() as session:
            await session.run("RETURN 1")
        print("Connected to Neo4j.")
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
