"""
NetworkX fallback graph engine — used automatically if Neo4j is
unreachable (see USE_NEO4J flag in app/config.py and routes_fusion.py).
Same interface as graph_engine_neo4j.py so callers don't need to branch.
"""
import networkx as nx
from typing import Dict, List


def get_money_flow_graph(case_id: str) -> Dict:
    G = _load_graph_for_case(case_id)
    nodes = [{"id": n, "label": n} for n in G.nodes]
    edges = [
        {"source": u, "target": v, "amount": d.get("amount"), "timestamp": d.get("timestamp")}
        for u, v, d in G.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


def get_circular_loops(case_id: str) -> List[List[str]]:
    G = _load_graph_for_case(case_id)
    return [cycle for cycle in nx.simple_cycles(G, length_bound=5)]


def get_mastermind_candidates(case_id: str) -> List[Dict]:
    G = _load_graph_for_case(case_id)
    centrality = nx.in_degree_centrality(G)
    ranked = sorted(centrality.items(), key=lambda kv: kv[1], reverse=True)[:5]
    return [{"account_id": account_id, "in_degree_centrality": score} for account_id, score in ranked]


def _load_graph_for_case(case_id: str) -> nx.DiGraph:
    """
    TODO: load real transfer edges from Postgres for this case_id.
    This is the rebuildable source: Neo4j's projection can always be
    regenerated from the same underlying Postgres data this function reads.
    """
    G = nx.DiGraph()
    return G
