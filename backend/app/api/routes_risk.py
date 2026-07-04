"""Risk score breakdown endpoint — rule-based + Isolation Forest + GraphSAGE/Node2Vec."""
from fastapi import APIRouter
from app.ml.risk_aggregator import get_risk_breakdown

router = APIRouter()


@router.get("/{entity_id}")
def get_risk(entity_id: str):
    return get_risk_breakdown(entity_id)
