#!/usr/bin/env bash
# Rebuilds the entire Neo4j graph projection from Postgres (the source of
# truth). Safe to run any time — e.g. after a Neo4j crash, or if the
# background sync task in app/db/neo4j_client.py silently failed.
set -e

echo "Rebuilding Neo4j projection from Postgres..."
docker-compose exec -T backend python -c "
from app.db.postgres import SessionLocal
from app.db.neo4j_client import get_neo4j_driver
from app.models.graph_models import CYPHER_UPSERT_TRANSFER, SCHEMA_CONSTRAINTS
from app.models.db_models import Transfer

driver = get_neo4j_driver()
with driver.session() as session:
    for constraint in SCHEMA_CONSTRAINTS:
        session.run(constraint)

db = SessionLocal()
transfers = db.query(Transfer).all()
with driver.session() as session:
    for t in transfers:
        session.run(
            CYPHER_UPSERT_TRANSFER,
            from_account_id=t.from_account_id,
            to_account_id=t.to_account_id,
            case_id=t.case_id,
            transfer_id=t.id,
            amount=t.amount,
            timestamp=t.timestamp,
        )
db.close()
print(f'Rebuilt Neo4j projection from {len(transfers)} Postgres transfer records.')
"
echo "Neo4j projection rebuild complete."
