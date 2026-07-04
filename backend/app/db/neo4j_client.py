"""
Neo4j client — treated strictly as a READ-MODEL / PROJECTION of Postgres.

Sync strategy (per architecture review):
  1. Write to Postgres first, inside a transaction.
  2. ONLY after that transaction commits, fire a background task that
     pushes the new nodes/edges into Neo4j (queue_neo4j_projection_update).
  3. If Neo4j is down or the push fails, Postgres data is untouched — the
     graph can be fully rebuilt from Postgres at any time via
     scripts/rebuild_neo4j_from_postgres.sh.

This avoids race conditions from trying to keep two databases in lockstep,
and means a Neo4j crash is a "rebuild the projection" event, not data loss.
"""
from neo4j import GraphDatabase
from app.config import settings
from app.models.graph_models import CYPHER_UPSERT_TRANSFER

_driver = None


def get_neo4j_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
    return _driver


def queue_neo4j_projection_update(source: str, payload: dict):
    """
    Background task fired AFTER a Postgres commit succeeds. Best-effort:
    if this fails, Postgres remains correct and the projection can be
    rebuilt later — it is never the only copy of the data.
    """
    if not settings.use_neo4j:
        return
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            for transfer in payload.get("transfers", []):
                session.run(CYPHER_UPSERT_TRANSFER, **transfer)
    except Exception as e:
        # Log and move on — Postgres already has the authoritative data.
        print(f"[neo4j_client] Projection update failed (source={source}): {e}. "
              f"Postgres is unaffected; rerun rebuild_neo4j_from_postgres.sh later.")
