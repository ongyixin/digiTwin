from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_driver
from app.models.api import ImpactScore
from app.models.graph import GraphSubgraph
from app.services.analytics_service import AnalyticsService
from app.services.graph_service import GraphService

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("/decisions")
async def list_decisions(driver=Depends(get_driver)):
    service = GraphService(driver)
    return await service.get_all_decisions()


@router.get("/overview", response_model=GraphSubgraph)
async def graph_overview(workspace: str = "default", driver=Depends(get_driver)):
    """Return all primary entity nodes and relationships for the dependency map."""
    service = GraphService(driver)
    return await service.get_graph_overview(workspace=workspace)


@router.get("/decisions/{decision_id}/lineage", response_model=GraphSubgraph)
async def decision_lineage(decision_id: str, driver=Depends(get_driver)):
    service = GraphService(driver)
    subgraph = await service.get_decision_lineage(decision_id)
    if not subgraph.nodes:
        raise HTTPException(status_code=404, detail="Decision not found")
    return subgraph


@router.get("/decisions/{decision_id}/impact", response_model=ImpactScore)
async def decision_impact(decision_id: str, driver=Depends(get_driver)):
    service = AnalyticsService(driver)
    return await service.compute_impact(decision_id)


@router.get("/timeline")
async def decision_timeline(driver=Depends(get_driver)):
    """Return decisions ordered by created_at with change events."""
    service = GraphService(driver)
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (d:Decision)
            OPTIONAL MATCH (p:Person)-[:MADE_DECISION]->(d)
            OPTIONAL MATCH (m:Meeting)-[:PRODUCED]->(d)
            OPTIONAL MATCH (d)-[:DEPENDS_ON]->(a:Assumption)-[:CONTRADICTED_BY]->(e:Evidence)
            RETURN d,
                   p.name AS owner_name,
                   m.title AS meeting_title,
                   count(DISTINCT e) AS contradictions
            ORDER BY coalesce(d.created_at, '') ASC
            LIMIT 200
            """
        )
        rows = await result.data()

    return [
        {
            **{k: v for k, v in dict(r["d"]).items() if k != "embedding"},
            "owner_name": r["owner_name"],
            "meeting_title": r["meeting_title"],
            "contradictions": r["contradictions"],
        }
        for r in rows
    ]
