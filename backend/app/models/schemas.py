"""Pydantic request/response schemas shared across API routes."""
from pydantic import BaseModel
from typing import Optional, List, Dict


class EntityOut(BaseModel):
    id: str
    type: str
    linked_phone: Optional[str] = None
    linked_upi: Optional[str] = None
    risk_score: float
    flags: List[str] = []


class RiskBreakdownOut(BaseModel):
    entity_id: str
    rule_based_score: float
    isolation_forest_score: float
    graph_ml_score: float
    final_risk_score: float
    is_mule_account: bool


class GraphOut(BaseModel):
    nodes: List[Dict]
    edges: List[Dict]


class TimelineOut(BaseModel):
    case_id: str
    events: List[Dict]
    flags: List[Dict]
