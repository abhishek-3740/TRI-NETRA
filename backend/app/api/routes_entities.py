"""Entity profile endpoints — accounts, phone numbers, UPI IDs, and their linked events."""
from fastapi import APIRouter, HTTPException

router = APIRouter()

# TODO: replace with real Postgres-backed queries once db_models.py is wired up.
_MOCK_ENTITIES = {
    "acc_001": {
        "id": "acc_001",
        "type": "account",
        "linked_phone": "9876543210",
        "linked_upi": "9876543210@okhdfc",
        "risk_score": 0.92,
        "flags": ["rapid_layering", "circular_flow"],
    }
}


@router.get("/{entity_id}")
def get_entity(entity_id: str):
    entity = _MOCK_ENTITIES.get(entity_id)
    if not entity:
        raise HTTPException(404, f"Entity '{entity_id}' not found.")
    return entity


@router.get("/")
def list_entities(min_risk: float = 0.0):
    return [e for e in _MOCK_ENTITIES.values() if e["risk_score"] >= min_risk]
