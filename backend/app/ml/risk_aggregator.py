"""
Combines Layer 1 (rule-based), Layer 2 (Isolation Forest), and Layer 3
(GraphSAGE/Node2Vec + Logistic Regression) into a single weighted risk
score per entity. Accounts with risk > 0.8 are flagged as Mule Accounts.
"""
from typing import Dict
from app.ml import isolation_forest

WEIGHTS = {
    "rule_based": 0.4,
    "isolation_forest": 0.3,
    "graph_ml": 0.3,
}

MULE_THRESHOLD = 0.8


def get_risk_breakdown(entity_id: str) -> Dict:
    rule_score = _get_rule_based_score(entity_id)
    if_score = _get_isolation_forest_score(entity_id)
    graph_score = _get_graph_ml_score(entity_id)

    final_score = (
        WEIGHTS["rule_based"] * rule_score
        + WEIGHTS["isolation_forest"] * if_score
        + WEIGHTS["graph_ml"] * graph_score
    )

    return {
        "entity_id": entity_id,
        "rule_based_score": rule_score,
        "isolation_forest_score": if_score,
        "graph_ml_score": graph_score,
        "final_risk_score": round(final_score, 3),
        "is_mule_account": final_score > MULE_THRESHOLD,
    }


def _get_rule_based_score(entity_id: str) -> float:
    # TODO: pull actual flags from app.fusion.temporal_rules / graph_engine for this entity
    return 0.0


def _get_isolation_forest_score(entity_id: str) -> float:
    # TODO: pull real feature vector for entity_id from Postgres
    features = {}
    return isolation_forest.score(features)


def _get_graph_ml_score(entity_id: str) -> float:
    # TODO: look up precomputed embedding + trained classifier prediction for entity_id
    return 0.0
