"""
Neo4j-backed money-flow graph engine — primary graph implementation.

Called ONLY from routes_fusion.py (server-side). The frontend never
imports or calls this directly — it only ever sees the JSON this module
(via routes_fusion.py) produces.
"""
from typing import Dict, List
from app.db.neo4j_client import get_neo4j_driver

CYPHER_MONEY_FLOW_GRAPH = """
MATCH (a:Account)-[t:TRANSFER]->(b:Account)
WHERE a.case_id = $case_id OR b.case_id = $case_id
RETURN a, t, b
LIMIT 500
"""

CYPHER_CIRCULAR_LOOPS = """
MATCH p=(a:Account)-[:TRANSFER*2..5]->(a)
WHERE a.case_id = $case_id
RETURN p
"""

CYPHER_MASTERMIND_CENTRALITY = """
MATCH (n:Account {case_id: $case_id})
RETURN n.id AS account_id,
       size((n)<-[:TRANSFER]-()) AS in_degree,
       size((n)-[:TRANSFER]->()) AS out_degree
ORDER BY in_degree DESC, out_degree ASC
LIMIT 5
"""


def get_money_flow_graph(case_id: str) -> Dict:
    driver = get_neo4j_driver()
    nodes, edges, seen_nodes = [], [], set()

    with driver.session() as session:
        result = session.run(CYPHER_MONEY_FLOW_GRAPH, case_id=case_id)
        for record in result:
            a, t, b = record["a"], record["t"], record["b"]
            for node in (a, b):
                if node["id"] not in seen_nodes:
                    nodes.append({"id": node["id"], "label": node.get("label", node["id"])})
                    seen_nodes.add(node["id"])
            edges.append({
                "source": a["id"],
                "target": b["id"],
                "amount": t.get("amount"),
                "timestamp": t.get("timestamp"),
            })

    return {"nodes": nodes, "edges": edges}


def get_circular_loops(case_id: str) -> List[List[str]]:
    driver = get_neo4j_driver()
    loops = []
    with driver.session() as session:
        result = session.run(CYPHER_CIRCULAR_LOOPS, case_id=case_id)
        for record in result:
            path = record["p"]
            loops.append([node["id"] for node in path.nodes])
    return loops


def get_mastermind_candidates(case_id: str) -> List[Dict]:
    driver = get_neo4j_driver()
    with driver.session() as session:
        result = session.run(CYPHER_MASTERMIND_CENTRALITY, case_id=case_id)
        return [dict(record) for record in result]


def attach_risk_colors(graph: Dict) -> Dict:
    """
    Enriches the raw graph with risk-based node colors before it's sent to
    the frontend. This is where FastAPI does the "coloring" work so
    Cytoscape.js just renders a ready-made JSON payload.
    """
    # TODO: pull real risk scores via app.ml.risk_aggregator.get_risk_breakdown
    for node in graph.get("nodes", []):
        node["color"] = "#dc2626" if node.get("risk_score", 0) > 0.8 else "#2563eb"
    return graph
