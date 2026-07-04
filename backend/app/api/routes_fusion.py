"""
Fusion data endpoints for the frontend dashboard.

IMPORTANT ARCHITECTURE RULE:
The React frontend NEVER queries Neo4j directly. All graph queries happen
here, server-side. This route runs the Cypher query, enriches the result
with risk scores and node colors, and returns plain JSON for Cytoscape.js.

Flow: React -> FastAPI (this file) -> Neo4j (Cypher) -> FastAPI (JSON + risk/colors) -> React
"""
from fastapi import APIRouter
from app.fusion import graph_engine_neo4j, graph_engine_networkx, temporal_rules, spatial_engine
from app.config import settings

router = APIRouter()


@router.get("/timeline/{case_id}")
def get_timeline(case_id: str):
    """Returns unified Call + IP session + Transfer events for vis-timeline."""
    events = temporal_rules.get_unified_timeline(case_id)
    flagged = temporal_rules.apply_rules(events)
    return {"case_id": case_id, "events": events, "flags": flagged}


@router.get("/network/{case_id}")
def get_network_graph(case_id: str):
    """
    Returns a Cytoscape.js-ready graph: {nodes: [...], edges: [...]}.
    Uses Neo4j if enabled, otherwise falls back to NetworkX automatically.
    """
    if settings.use_neo4j:
        try:
            raw_graph = graph_engine_neo4j.get_money_flow_graph(case_id)
        except Exception:
            # Neo4j unreachable mid-demo -> fall back without breaking the request
            raw_graph = graph_engine_networkx.get_money_flow_graph(case_id)
    else:
        raw_graph = graph_engine_networkx.get_money_flow_graph(case_id)

    # Enrich with risk-based node coloring before sending to the frontend
    cytoscape_json = graph_engine_neo4j.attach_risk_colors(raw_graph)
    return cytoscape_json


@router.get("/map/{case_id}")
def get_map_clusters(case_id: str):
    """Returns ST-DBSCAN co-location clusters for the Leaflet map panel."""
    clusters = spatial_engine.get_colocation_clusters(case_id)
    return {"case_id": case_id, "clusters": clusters}
